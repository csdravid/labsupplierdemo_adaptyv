from __future__ import annotations

import csv
import re
from datetime import date

from supplier_agent.models import Item
from supplier_agent.paths import INVENTORY, POLICY


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "1", "y")


def _parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    return date.fromisoformat(value)


def read_policy() -> dict[str, str]:
    """Flat key-value map from `- Key: value` lines in policy.md."""
    text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*([^:]+):\s*(.+)$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def read_sku_overrides() -> dict[str, int]:
    """Per-SKU reorder_qty overrides from `## Per-SKU overrides` section."""
    text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    overrides: dict[str, int] = {}
    in_section = False
    for line in text.splitlines():
        if line.strip().lower().startswith("## per-sku"):
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            break
        if not in_section:
            continue
        m = re.match(r"^\s*-\s*([^:]+):\s*reorder_qty\s*(\d+)", line, re.I)
        if m:
            overrides[m.group(1).strip()] = int(m.group(2))
    return overrides


def read_lead_times() -> dict[str, int]:
    """Supplier name → lead time days from `## Supplier lead times` section."""
    text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    lead_times: dict[str, int] = {}
    in_section = False
    for line in text.splitlines():
        if "supplier lead times" in line.lower():
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            break
        if not in_section:
            continue
        m = re.match(r"^\s*-\s*([^:]+):\s*(\d+)", line)
        if m:
            lead_times[m.group(1).strip()] = int(m.group(2))
    return lead_times


def load_inventory() -> list[Item]:
    if not INVENTORY.exists():
        raise SystemExit(f"Missing inventory: {INVENTORY}")
    overrides = read_sku_overrides()
    items: list[Item] = []
    with INVENTORY.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sku = row["sku"].strip()
            qty = int(row["reorder_qty"])
            if sku in overrides:
                qty = overrides[sku]
            items.append(
                Item(
                    sku=sku,
                    item=row["item"].strip(),
                    supplier=row["supplier"].strip(),
                    supplier_email=row["supplier_email"].strip(),
                    catalog_no=row.get("catalog_no", "").strip(),
                    category=row.get("category", "").strip(),
                    on_hand=int(row["on_hand"]),
                    reorder_point=int(row["reorder_point"]),
                    reorder_qty=qty,
                    unit=row["unit"].strip(),
                    unit_cost_chf=float(row["unit_cost_chf"]),
                    usage_per_week=float(row["usage_per_week"]),
                    location=row["location"].strip(),
                    storage=row.get("storage", "").strip(),
                    critical=_parse_bool(row.get("critical", "no")),
                    next_run_date=_parse_date(row.get("next_run_date", "")),
                    last_ordered=row.get("last_ordered", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
    return items


def find_item_by_sku(sku: str) -> Item:
    for item in load_inventory():
        if item.sku == sku:
            return item
    raise KeyError(f"SKU not in inventory: {sku}")


def check_items(items: list[Item] | None = None) -> list[Item]:
    items = items or load_inventory()
    return [i for i in items if i.needs_reorder]


def lead_time_days(supplier: str, policy: dict[str, int] | None = None) -> int:
    policy = policy or read_lead_times()
    return policy.get(supplier, 5)
