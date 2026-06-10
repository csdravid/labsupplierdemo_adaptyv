from __future__ import annotations

from supplier_agent.draft_common import draft_header, requester, ship_to
from supplier_agent.finance import SkuFinance, analyze_item
from supplier_agent.models import Item
from supplier_agent.rules import read_policy


def draft_email(item: Item, draft_id: str, fin: SkuFinance | None = None) -> str:
    policy = read_policy()
    fin = fin or analyze_item(item)
    ship = ship_to(policy)
    req = requester(policy)
    header = draft_header(item.sku, draft_id, "template", fin)

    delivery_note = ""
    if fin.expedite_risk or fin.run_blocked:
        delivery_note = (
            "\nPlease use **standard delivery** if possible — we would like to avoid expedite surcharges.\n"
        )

    body = f"""## Email

**To:** {item.supplier_email}  
**Subject:** Reorder request — {item.item} ({item.sku})

---

Hi {item.supplier} team,

We would like to place a reorder:

| Field | Value |
| --- | --- |
| SKU | {item.sku} |
| Catalog | {item.catalog_no or "—"} |
| Item | {item.item} |
| Quantity | {item.reorder_qty} {item.unit}(s) |
| Current on-hand | {item.on_hand} (reorder point: {item.reorder_point}) |
| Storage location | {item.location} |
| Ship to | {ship} |
| Requester | {req} |
{delivery_note}
Please confirm availability, lead time, and quote in CHF.

Best regards,  
{req}  
Adaptyv Biosystems

---

*Draft only — approve via CLI or web UI before sending manually.*
"""
    return header + body
