# Data model

All operational data is **files ops can edit** — no database, no migrations.

## `data/inventory.csv`

One row per SKU. Loaded by `rules.load_inventory()`.

| Column | Type | Description |
| --- | --- | --- |
| `sku` | string | Primary key; used in draft IDs |
| `item` | string | Display name |
| `supplier` | string | Must match lead-time key in `policy.md` |
| `supplier_email` | string | To: address in draft email |
| `catalog_no` | string | Supplier catalog reference |
| `category` | string | kit / reagent / consumable (informational) |
| `on_hand` | int | Current quantity |
| `reorder_point` | int | Trigger when `on_hand <=` this |
| `reorder_qty` | int | Order quantity (may be overridden in policy) |
| `unit` | string | pack, box, bottle, etc. |
| `unit_cost_chf` | float | Per-unit cost in CHF |
| `usage_per_week` | float | Consumption rate for stockout projection |
| `location` | string | Freezer / shelf ID |
| `storage` | string | -20C, RT, etc. |
| `critical` | yes/no | Flag for UI emphasis |
| `next_run_date` | ISO date or empty | Next lab run using this SKU → run-blocked logic |
| `last_ordered` | string | Last PO date (informational) |
| `notes` | string | Free text |

### Derived behaviour

```python
needs_reorder = on_hand <= reorder_point
days_until_stockout = on_hand / usage_per_week * 7
run_blocked = next_run_date set and days_until_stockout < days_to_run
```

### Policy override

`policy.md` section `## Per-SKU overrides` can replace `reorder_qty` for specific SKUs after CSV load.

---

## `data/policy.md`

Markdown with structured sections parsed by `rules.py` and `finance.py`.

### Flat keys (`read_policy()`)

Lines like `- Ship-to: …` become dict keys:

| Key | Used by |
| --- | --- |
| Ship-to | Draft emails |
| Requester | Draft emails |
| Standard shipping CHF | `finance.planned_cost` |
| Expedite flat surcharge CHF | `expedite_surcharge()` |
| Expedite percent surcharge | `expedite_surcharge()` |

### Section: `## Per-SKU overrides`

```
- A1435101: reorder_qty 2
```

Parsed by `read_sku_overrides()`.

### Section: `## Supplier lead times (days)`

```
- Thermo Fisher: 3
```

Parsed by `read_lead_times()` → `lead_time_days(supplier)`.

---

## `data/spend_log.csv`

Append-only on approve. Read for MTD spend dashboards.

| Column | Description |
| --- | --- |
| `date` | ISO date of approval |
| `sku` | SKU ordered |
| `supplier` | Supplier name |
| `quantity` | `reorder_qty` at approve time |
| `unit_cost_chf` | From inventory |
| `shipping_chf` | Standard shipping from policy |
| `expedite_chf` | 0 unless `--expedite` on approve |
| `total_chf` | planned + expedite |
| `status` | `approved` |
| `po_ref` | e.g. `PO-A1435101_20260610` |

Written by `finance.record_approval()`.

---

## Draft markdown (`drafts/pending/*.md`)

Human-readable PO email with metadata blockquote:

```markdown
# Draft PO — {sku} — pending approval

> **Status:** PENDING · Human must approve before send
> **Draft ID:** `{sku}_{YYYYMMDD}`
> **Draft source:** template | claude
> **Expedite risk:** yes | no
> **Run blocked:** yes | no
> **Planned cost:** CHF …
> **Expedite exposure:** CHF …
> **Reorder by:** YYYY-MM-DD

## Email
**To:** …
**Subject:** …
…
```

On approve, status lines and title update; file moves to `drafts/approved/`.

Parsed by `drafts.parse_draft_meta()` for web UI badges.

---

## `activity.md`

Append-only audit log (markdown table).

| Column | Example |
| --- | --- |
| timestamp | `2026-06-10 09:46` |
| domain | `Supplier` |
| action | `draft PO`, `approve PO`, `daily run`, `demo reset` |
| detail | SKU + path |
| follow-up | source, exposure CHF, po_ref |

---

## Environment (`.env`)

| Variable | Default | Description |
| --- | --- | --- |
| `DRAFT_MODE` | `template` | `template` or `claude` |
| `ANTHROPIC_API_KEY` | empty | Required only for Claude mode |

Loaded by `config.py` on import (does not override existing env vars).

---

## Hero demo record

**A1435101** — Expi293 Expression Medium:

- `on_hand: 0`, `reorder_point: 2`, `reorder_qty: 2` (override)
- `unit_cost_chf: 6220` → planned ~CHF 12,465 with shipping
- Expedite exposure ~CHF 4,986 (40% of planned > flat 150)
- `next_run_date` → **run blocked**

Use this SKU for finance tab and approve demo.

---

## Related docs

- [../DATA_GUIDE.md](../DATA_GUIDE.md) — how to fill inventory
- [OPERATIONS.md](OPERATIONS.md) — draft modes
