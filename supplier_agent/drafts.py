from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from supplier_agent.activity import log_activity
from supplier_agent.draft_claude import generate_draft
from supplier_agent.finance import analyze_item, record_approval
from supplier_agent.models import Item
from supplier_agent.paths import APPROVED, PENDING
from supplier_agent.rules import check_items, find_item_by_sku, load_inventory


def draft_id(item: Item, on_day: date | None = None) -> str:
    on_day = on_day or date.today()
    return f"{item.sku}_{on_day.strftime('%Y%m%d')}"


def draft_path(did: str, *, approved: bool = False) -> Path:
    folder = APPROVED if approved else PENDING
    return folder / f"{did}.md"


def existing_pending_ids() -> set[str]:
    if not PENDING.exists():
        return set()
    return {p.stem for p in PENDING.glob("*.md")}


def create_drafts(
    items: list[Item] | None = None,
    *,
    force_template: bool | None = None,
) -> list[Path]:
    PENDING.mkdir(parents=True, exist_ok=True)
    APPROVED.mkdir(parents=True, exist_ok=True)
    low = items if items is not None else check_items()
    pending = existing_pending_ids()
    created: list[Path] = []

    for item in low:
        did = draft_id(item)
        if did in pending:
            continue
        fin = analyze_item(item)
        content, source = generate_draft(item, did, fin, force_template=force_template)
        path = draft_path(did)
        path.write_text(content, encoding="utf-8")
        created.append(path)
        log_activity(
            "draft PO",
            f"{item.sku} {item.item[:40]} → {path.name}",
            f"source={source}, exposure=CHF {fin.expedite_surcharge_chf:g}",
        )

    return created


def list_drafts() -> tuple[list[Path], list[Path]]:
    PENDING.mkdir(parents=True, exist_ok=True)
    APPROVED.mkdir(parents=True, exist_ok=True)
    return sorted(PENDING.glob("*.md")), sorted(APPROVED.glob("*.md"))


def parse_draft_meta(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for key in (
        "Draft ID",
        "Draft source",
        "Status",
        "Expedite risk",
        "Run blocked",
        "Planned cost",
        "Expedite exposure",
    ):
        m = re.search(rf"\*\*{re.escape(key)}:\*\*\s*(.+)", text)
        if m:
            meta[key] = m.group(1).strip().strip("`")
    subj = re.search(r"^\*\*Subject:\*\*\s*(.+)$", text, re.MULTILINE)
    if subj:
        meta["Subject"] = subj.group(1).strip()
    return meta


def read_draft_summary(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    meta = parse_draft_meta(text)
    meta["id"] = path.stem
    meta["path"] = str(path)
    meta["body"] = text
    return meta


def sku_from_draft_id(draft_id: str) -> str:
    if "_" not in draft_id:
        raise ValueError(f"Invalid draft ID (expected SKU_YYYYMMDD): {draft_id}")
    sku, _, date_part = draft_id.rpartition("_")
    if not re.fullmatch(r"\d{8}", date_part):
        raise ValueError(f"Invalid draft ID (expected SKU_YYYYMMDD): {draft_id}")
    return sku


def _mark_approved(text: str, sku: str) -> str:
    text = text.replace(
        "**Status:** PENDING · Human must approve before send",
        "**Status:** APPROVED · Ready to send manually",
    )
    text = text.replace("pending approval", "approved — ready to send manually")
    text = text.replace(
        f"# Draft PO — {sku} — pending approval",
        f"# Draft PO — {sku} — approved — ready to send manually",
    )
    text = text.replace(
        "*Draft only — approve via CLI or web UI before sending manually.*",
        "*Approved — copy email body to your mail client. No auto-send.*",
    )
    return text


def approve_draft(draft_id: str, *, expedite: bool = False) -> Path:
    """Human gate: pending → approved, append spend_log row."""
    src = draft_path(draft_id, approved=False)
    if not src.exists():
        raise FileNotFoundError(f"No pending draft: {draft_id}")

    sku = sku_from_draft_id(draft_id)
    item = find_item_by_sku(sku)
    text = _mark_approved(src.read_text(encoding="utf-8"), sku)
    dest = draft_path(draft_id, approved=True)
    dest.write_text(text, encoding="utf-8")
    src.unlink()

    po_ref = f"PO-{draft_id}"
    record_approval(item, po_ref, expedite=expedite)
    fin = analyze_item(item)
    log_activity(
        "approve PO",
        f"{draft_id} → {dest.name}",
        f"po_ref={po_ref}, CHF {fin.planned_cost_chf:g} planned"
        + (f", expedite CHF {fin.expedite_surcharge_chf:g}" if expedite else ""),
    )
    return dest


def status_summary() -> dict[str, int | list[Item] | list[Path]]:
    items = load_inventory()
    low = check_items()
    pending, approved = list_drafts()
    return {
        "total_skus": len(items),
        "low_stock": len(low),
        "pending": len(pending),
        "approved": len(approved),
        "low_items": low,
        "pending_paths": pending,
        "approved_paths": approved,
    }
