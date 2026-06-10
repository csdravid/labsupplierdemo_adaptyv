# Layers (L0 → L9)

Greenfield rebuild strategy: **bottom-up**, one auditable layer at a time. Each layer ships with tests before the next starts.

## Layer map

| Layer | Name | Status | Deliverables | Tests |
| --- | --- | --- | --- | --- |
| **L0** | Scaffold | ✅ Done | `paths.py`, folders, `.gitignore`, `requirements.txt`, README skeleton | — |
| **L1** | Data | ✅ Done | `inventory.csv` (14 SKUs), `policy.md`, `DATA_GUIDE.md` | Manual review |
| **L2** | Models + rules | ✅ Done | `models.py`, `rules.py` | `test_rules.py` |
| **L3** | Finance | ✅ Done | `finance.py`, `spend_log.csv` seed | `test_finance.py` |
| **L4** | Drafts | ✅ Done | template + Claude paths, `drafts.py`, `activity.py` | `test_drafts.py`, `test_config.py` |
| **L5** | Approve | ✅ Done | `approve_draft()`, spend log on approve | `test_drafts.py` |
| **L6** | CLI | ✅ Done | `cli.py` — status, finance, run, approve, demo-reset | Manual + pytest |
| **L7** | Web UI | ✅ Done | `web/app.py` — 5 tabs, light theme, public Docs | Render smoke |

## Audit gate (per layer)

Before moving to L{n+1}:

1. **Run tests** — `python -m pytest tests/ -v`
2. **Smoke the interface** — CLI or web for that layer's feature
3. **User says "L{n} approved"** — explicit sign-off in Cursor session
4. **Update this file** — mark layer done, note any deviations

## L0 — Scaffold

**Goal:** Empty repo that knows where everything lives.

- `supplier_agent/paths.py` — all paths from `ROOT`
- Folder skeleton: `data/`, `drafts/pending`, `drafts/approved`, `prompts/`, `tests/`, `web/`
- `requirements.txt` — `anthropic`, `pytest`
- `.gitignore` — `.env`, `__pycache__`, drafts optional

## L1 — Data

**Goal:** Real lab inventory ops can edit data without touching code.

- 14 SKUs researched (BioConcept, Thermo, Starlab CH, Sigma, etc.)
- Policy: shipping CHF 25, expedite flat 150 / 40%, lead times per supplier
- Per-SKU overrides: `A1435101` reorder_qty 2; `E2621S` reorder_qty 3
- Hero demo SKU: **A1435101** Expi293 — 0 on hand, run-blocked

## L2 — Models + rules

**Goal:** Deterministic low-stock detection.

- `Item` dataclass with `needs_reorder`
- `load_inventory()` + policy override merge
- `check_items()` → 6 SKUs below reorder in current data

## L3 — Finance

**Goal:** CHF story for interview — expedite exposure, run-blocked, ROI headline.

- `SkuFinance` per item: days until stockout, lead time, planned cost, surcharge
- `expedite_surcharge = max(flat, percent × planned)`
- `finance_summary()` — exposure excludes SKUs with draft already pending
- Seed `spend_log.csv` with 3 historical rows

## L4 — Drafts

**Goal:** PO email markdown with finance frontmatter.

- Template default; Claude parallel track via `config.py`
- Dedup by `{sku}_{date}`
- `prompts/draft_po.txt` for Claude system prompt
- Activity log on every draft

## L5 — Approve

**Goal:** Human gate + financial record.

- `approve_draft()` — pending → approved, status text update
- `record_approval()` → `spend_log.csv`
- `po_ref = PO-{draft_id}`

## L6 — CLI

**Goal:** Terminal demo without web.

```
status | check | finance | list | run | draft | approve | demo-reset
```

Draft flags: `--template` / `--claude` (mutually exclusive).

## L7 — Web UI

**Goal:** Screen-share friendly localhost UI.

- `127.0.0.1:8787` — Control, Finance, Drafts, Activity, **Docs**
- Light theme, Helvetica
- Demo reset in collapsed "Demo prep" section

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
