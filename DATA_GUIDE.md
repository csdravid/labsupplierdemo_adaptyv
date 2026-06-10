# Data guide (L1) — fill before L2

> **Your job:** Replace example rows in `data/inventory.csv` with **8–15 SKUs you recognise** from real lab work. Tune `data/policy.md` to match your suppliers and expedite experience (e.g. Novimmune).

Agent builds **L2** only after you reply **"L1 approved"**.

---

## `data/inventory.csv`

One row per SKU. Save as UTF-8 CSV (Excel / Numbers / Obsidian / Google Sheets → export CSV).

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| `sku` | yes | text | Internal ID, e.g. `SK-001` |
| `item` | yes | text | Full product name |
| `supplier` | yes | text | Must **exactly match** a name under `## Supplier lead times` in policy.md |
| `supplier_email` | yes | email | Orders desk (demo OK if fictional) |
| `catalog_no` | no | text | Supplier catalog / ref |
| `category` | no | text | `consumable` / `reagent` / `kit` |
| `on_hand` | yes | int | Current quantity in `unit` |
| `reorder_point` | yes | int | Reorder when on_hand ≤ this |
| `reorder_qty` | yes | int | Typical order batch |
| `unit` | yes | text | `pack`, `rack`, `vial`, `bottle`, `kit`, `box` |
| `unit_cost_chf` | yes | float | Price per `unit` (estimate OK) |
| `usage_per_week` | yes | float | How many `unit` consumed per week (estimate) |
| `location` | yes | text | Where stored, e.g. `Bench 3`, `4C`, `-20C` |
| `storage` | no | text | `RT`, `4C`, `-20C`, `-80C` |
| `critical` | yes | yes/no | Blocks experiments if out |
| `next_run_date` | no | YYYY-MM-DD | Upcoming run needing this SKU — powers **run_blocked** alert |
| `last_ordered` | yes | YYYY-MM-DD | Last PO date |
| `notes` | no | text | Sourced vs estimate — for humans only (ignored by agent until L2+) |

### Demo story (aim for this mix)

| Pattern | Count | Purpose |
|---------|-------|---------|
| Below reorder point | 2–4 | Triggers agent |
| Expedite risk (stockout before lead time) | 2–3 | Finance tab |
| `next_run_date` before stockout | 1–2 | Run-blocked row |
| Healthy stock | 2–3 | Contrast (e.g. SK-007) |

### `usage_per_week` cheat sheet

Estimate: *"We open X packs per month"* → `usage_per_week = X * 12 / 52`.

Example: 8 racks of tips/month → `8 * 12 / 52 ≈ 1.8` racks/week.

---

## `data/policy.md`

### Defaults
- **Ship-to** — delivery address (Adaptyv demo: EPFL Innovation Park, Lausanne)
- **Requester** — name on PO
- **Currency** — CHF

### Finance defaults
- **Standard shipping CHF** — typical order (~CHF 20–40 in CH)
- **Expedite flat surcharge CHF** — your Novimmune courier memory (e.g. 150)
- **Expedite percent surcharge** — e.g. 40 (= 40% of order)
- **Expedite model** — `max(flat, percent)` — we use whichever is higher

### Per-SKU overrides
Optional: `- SK-003: reorder_qty 2` for expensive items.

### Supplier lead times (days)
**Names must match `supplier` column in CSV.**

| Supplier | Typical days (CH/EU) |
|----------|----------------------|
| Thermo Fisher | 2–5 |
| Starlab | 1–3 |
| Merck/Sigma | 3–7 |
| New England Biolabs | 5–10 |
| Local pharmacy / COVID-era expedite | 1 |

---

## Validation checklist (before "L1 approved")

- [ ] 8–15 rows, no empty required fields
- [ ] Supplier names match policy lead-time keys
- [ ] At least 2 SKUs below reorder point
- [ ] `unit_cost_chf` and `usage_per_week` filled for all rows
- [ ] 1–2 rows have `next_run_date` within next 7–14 days
- [ ] You can explain each line in one sentence (interview-ready)

---

## Gemini research

Use the prompt in `GEMINI_RESEARCH_PROMPT.md` (or copy from chat) to gather CH prices, lead times, and usage hints — then **you** paste into this CSV and sanity-check numbers.
