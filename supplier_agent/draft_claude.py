from __future__ import annotations

from supplier_agent.config import anthropic_api_key, resolve_force_template
from supplier_agent.draft_common import draft_header, requester, ship_to
from supplier_agent.draft_template import draft_email
from supplier_agent.finance import SkuFinance, analyze_item
from supplier_agent.models import Item
from supplier_agent.paths import DRAFT_PO_PROMPT
from supplier_agent.rules import read_policy

DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _load_system_prompt() -> str:
    if DRAFT_PO_PROMPT.exists():
        return DRAFT_PO_PROMPT.read_text(encoding="utf-8")
    return "Draft a professional lab reorder email using only provided fields."


def _user_payload(item: Item, fin: SkuFinance) -> str:
    policy = read_policy()
    lines = [
        f"SKU: {item.sku}",
        f"Item: {item.item}",
        f"Supplier: {item.supplier}",
        f"Supplier email: {item.supplier_email}",
        f"Catalog: {item.catalog_no}",
        f"On hand: {item.on_hand}",
        f"Reorder point: {item.reorder_point}",
        f"Reorder quantity: {item.reorder_qty} {item.unit}(s)",
        f"Storage location: {item.location}",
        f"Last ordered: {item.last_ordered}",
        f"Ship to: {ship_to(policy)}",
        f"Requester: {requester(policy)}",
        f"Company: Adaptyv Biosystems",
        "",
        "Finance context:",
        f"Days until stockout: {fin.days_until_stockout}",
        f"Supplier lead time (days): {fin.lead_time_days}",
        f"Expedite risk: {fin.expedite_risk}",
        f"Run blocked before next lab run: {fin.run_blocked}",
        f"Planned order cost CHF: {fin.planned_cost_chf}",
        f"Expedite surcharge if delayed CHF: {fin.expedite_surcharge_chf}",
    ]
    if item.next_run_date:
        lines.append(f"Next lab run date: {item.next_run_date.isoformat()}")
    return "\n".join(lines)


def _call_claude(item: Item, fin: SkuFinance) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed") from exc

    key = anthropic_api_key()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1024,
        system=_load_system_prompt(),
        messages=[{"role": "user", "content": _user_payload(item, fin)}],
    )
    parts = [b.text for b in message.content if hasattr(b, "text")]
    body = "\n".join(parts).strip()
    if not body:
        raise RuntimeError("empty Claude response")
    return body


def generate_draft(
    item: Item,
    draft_id: str,
    fin: SkuFinance | None = None,
    *,
    force_template: bool | None = None,
) -> tuple[str, str]:
    """Return (markdown_content, source) where source is 'claude' or 'template'.

    Default is template (no API). Set DRAFT_MODE=claude + ANTHROPIC_API_KEY in .env,
    or pass force_template=False to opt into Claude when configured.
    """
    fin = fin or analyze_item(item)
    if resolve_force_template(force_template):
        return draft_email(item, draft_id, fin), "template"
    try:
        body = _call_claude(item, fin)
        if not body.lstrip().startswith("## Email"):
            body = f"## Email\n\n{body}"
        header = draft_header(item.sku, draft_id, "claude", fin, model=DEFAULT_MODEL)
        footer = "\n---\n\n*Draft only — approve via CLI or web UI before sending manually.*\n"
        return header + body + footer, "claude"
    except Exception:
        return draft_email(item, draft_id, fin), "template"
