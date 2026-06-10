"""Quick check — python -m supplier_agent"""
from supplier_agent.config import draft_mode_status
from supplier_agent.finance import format_finance_table
from supplier_agent.rules import check_items, load_inventory

print(f"Draft mode: {draft_mode_status()}\n")
items = load_inventory()
low = check_items(items)
print(f"Loaded {len(items)} SKUs · {len(low)} below reorder point:\n")
for i in low:
    crit = " CRITICAL" if i.critical else ""
    run = f" run={i.next_run_date}" if i.next_run_date else ""
    print(f"  {i.sku}: {i.on_hand}/{i.reorder_point} {i.unit} — {i.item[:50]}{crit}{run}")

print("\n" + "=" * 60 + "\n")
print(format_finance_table())
