from __future__ import annotations

from datetime import datetime

from supplier_agent.finance import SkuFinance
from supplier_agent.rules import read_policy


def ship_to(policy: dict[str, str] | None = None) -> str:
    policy = policy or read_policy()
    return policy.get("Ship-to", "Lab, Lausanne")


def requester(policy: dict[str, str] | None = None) -> str:
    policy = policy or read_policy()
    return policy.get("Requester", "Lab Operations")


def draft_header(item_sku: str, draft_id: str, source: str, fin: SkuFinance, *, model: str = "") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    reorder_by = fin.reorder_by.isoformat() if fin.reorder_by else "—"
    model_line = f"> **Model:** {model}  \n" if model else ""
    return f"""# Draft PO — {item_sku} — pending approval

> **Status:** PENDING · Human must approve before send  
> **Draft ID:** `{draft_id}`  
> **Draft source:** {source}  
{model_line}> **Generated:** {now}  
> **Expedite risk:** {"yes" if fin.expedite_risk else "no"}  
> **Run blocked:** {"yes" if fin.run_blocked else "no"}  
> **Planned cost:** CHF {fin.planned_cost_chf:g}  
> **Expedite exposure:** CHF {fin.expedite_surcharge_chf:g}  
> **Reorder by:** {reorder_by}

"""
