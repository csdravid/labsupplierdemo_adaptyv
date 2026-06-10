from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from supplier_agent.models import Item
from supplier_agent.paths import PENDING, SPEND_LOG
from supplier_agent.rules import lead_time_days, load_inventory, read_policy


@dataclass(frozen=True)
class SkuFinance:
    item: Item
    days_until_stockout: float
    lead_time_days: int
    expedite_risk: bool
    run_blocked: bool
    planned_cost_chf: float
    expedite_surcharge_chf: float
    expedite_cost_chf: float
    savings_if_now_chf: float
    reorder_by: date | None
    draft_pending: bool


def _float_policy(key: str, default: float) -> float:
    raw = read_policy().get(key, "")
    m = re.search(r"[\d.]+", raw)
    return float(m.group()) if m else default


def finance_config() -> dict[str, float]:
    return {
        "standard_shipping": _float_policy("Standard shipping CHF", 25.0),
        "expedite_flat": _float_policy("Expedite flat surcharge CHF", 150.0),
        "expedite_percent": _float_policy("Expedite percent surcharge", 40.0),
    }


def days_until_stockout(item: Item) -> float:
    if item.usage_per_week <= 0:
        return 999.0
    return item.on_hand / item.usage_per_week * 7.0


def expedite_surcharge(planned_cost: float, cfg: dict[str, float] | None = None) -> float:
    cfg = cfg or finance_config()
    flat = cfg["expedite_flat"]
    percent_cost = planned_cost * (cfg["expedite_percent"] / 100.0)
    return max(flat, percent_cost)


def _draft_pending_for_sku(sku: str) -> bool:
    if not PENDING.exists():
        return False
    today = date.today().strftime("%Y%m%d")
    return any(p.stem.startswith(f"{sku}_{today}") for p in PENDING.glob("*.md"))


def analyze_item(item: Item, today: date | None = None) -> SkuFinance:
    today = today or date.today()
    cfg = finance_config()
    lead = lead_time_days(item.supplier)
    days_left = days_until_stockout(item)

    stockout_before_lead = days_left <= lead
    expedite_risk = stockout_before_lead or item.needs_reorder

    run_blocked = False
    if item.next_run_date and item.next_run_date >= today:
        days_to_run = (item.next_run_date - today).days
        run_blocked = days_left < days_to_run

    planned = item.reorder_qty * item.unit_cost_chf + cfg["standard_shipping"]
    surcharge = expedite_surcharge(planned, cfg)
    expedite_total = planned + surcharge
    savings = surcharge if expedite_risk else 0.0

    reorder_by: date | None = None
    if expedite_risk or run_blocked:
        reorder_by = today

    return SkuFinance(
        item=item,
        days_until_stockout=round(days_left, 1),
        lead_time_days=lead,
        expedite_risk=expedite_risk,
        run_blocked=run_blocked,
        planned_cost_chf=round(planned, 2),
        expedite_surcharge_chf=round(surcharge, 2),
        expedite_cost_chf=round(expedite_total, 2),
        savings_if_now_chf=round(savings, 2),
        reorder_by=reorder_by,
        draft_pending=_draft_pending_for_sku(item.sku),
    )


def analyze_all(today: date | None = None) -> list[SkuFinance]:
    return [analyze_item(i, today=today) for i in load_inventory()]


def _read_spend_rows() -> list[dict[str, str]]:
    if not SPEND_LOG.exists():
        return []
    with SPEND_LOG.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def monthly_spend(year: int, month: int) -> float:
    total = 0.0
    for row in _read_spend_rows():
        d = date.fromisoformat(row["date"])
        if d.year == year and d.month == month:
            total += float(row["total_chf"])
    return round(total, 2)


def expedite_spend_mtd(today: date | None = None) -> float:
    today = today or date.today()
    total = 0.0
    for row in _read_spend_rows():
        d = date.fromisoformat(row["date"])
        if d.year == today.year and d.month == today.month:
            total += float(row.get("expedite_chf") or 0)
    return round(total, 2)


def finance_summary(today: date | None = None) -> dict:
    today = today or date.today()
    rows = analyze_all(today=today)
    at_risk = [r for r in rows if r.expedite_risk]
    run_blocked = [r for r in rows if r.run_blocked]
    exposure = sum(
        r.savings_if_now_chf for r in at_risk if not r.draft_pending
    )
    exposure = round(exposure, 2)

    mtd = monthly_spend(today.year, today.month)
    exp_mtd = expedite_spend_mtd(today)

    headline = (
        f"CHF {exposure:g} expedite exposure"
        f" · CHF {exposure:g} saveable if you reorder on schedule today"
    )
    if run_blocked:
        headline += f" · {len(run_blocked)} run(s) at risk"

    return {
        "monthly_spend_chf": mtd,
        "expedite_spend_mtd": exp_mtd,
        "expedite_exposure_chf": exposure,
        "potential_savings_chf": exposure,
        "run_blocked_count": len(run_blocked),
        "at_risk_count": len(at_risk),
        "roi_headline": headline,
        "at_risk_skus": sorted(
            at_risk,
            key=lambda r: (not r.run_blocked, -r.savings_if_now_chf),
        ),
        "run_blocked_skus": run_blocked,
    }


def record_approval(item: Item, po_ref: str, *, expedite: bool = False) -> None:
    """Append an approved PO line to spend_log.csv (L5 approve flow uses this)."""
    cfg = finance_config()
    planned = item.reorder_qty * item.unit_cost_chf + cfg["standard_shipping"]
    exp_fee = expedite_surcharge(planned) if expedite else 0.0
    total = planned + exp_fee
    row = {
        "date": date.today().isoformat(),
        "sku": item.sku,
        "supplier": item.supplier,
        "quantity": str(item.reorder_qty),
        "unit_cost_chf": str(item.unit_cost_chf),
        "shipping_chf": str(int(cfg["standard_shipping"])),
        "expedite_chf": str(int(exp_fee)),
        "total_chf": str(round(total, 2)),
        "status": "approved",
        "po_ref": po_ref,
    }
    write_header = not SPEND_LOG.exists() or SPEND_LOG.stat().st_size == 0
    fieldnames = list(row.keys())
    with SPEND_LOG.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def format_finance_table(summary: dict | None = None) -> str:
    summary = summary or finance_summary()
    lines = [
        summary["roi_headline"],
        "",
        f"Monthly spend (MTD): CHF {summary['monthly_spend_chf']:g}",
        f"Expedite spend (MTD): CHF {summary['expedite_spend_mtd']:g}",
        f"At-risk SKUs: {summary['at_risk_count']} · Run-blocked: {summary['run_blocked_count']}",
        "",
        "| SKU | Days left | Lead | Planned | Surcharge | Risk | Run blocked |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in summary["at_risk_skus"]:
        lines.append(
            f"| {r.item.sku} | {r.days_until_stockout} | {r.lead_time_days}d "
            f"| {r.planned_cost_chf:g} | {r.expedite_surcharge_chf:g} "
            f"| {'yes' if r.expedite_risk else 'no'} | {'yes' if r.run_blocked else 'no'} |"
        )
    return "\n".join(lines)
