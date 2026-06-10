# Project structure

Complete map of `lab-supplier-agent-v2/`. Paths are relative to repo root.

## Top-level layout

```
lab-supplier-agent-v2/
├── supplier_agent/       # Python package — all business logic
├── web/                  # Localhost HTTP UI (thin shell)
├── data/                 # Editable ops data (no code changes needed)
├── drafts/               # Generated PO emails (pending → approved)
├── prompts/              # Claude system prompt
├── tests/                # pytest per layer
├── docs/                 # This documentation library
├── activity.md           # Append-only audit log (generated)
├── DRAFT_MODES.md        # Template vs Claude quick reference
├── DATA_GUIDE.md         # How to fill inventory + policy
├── GEMINI_RESEARCH_PROMPT.md  # Prompt used to research real SKUs
├── requirements.txt
├── .env.example          # DRAFT_MODE + ANTHROPIC_API_KEY
├── .gitignore
└── README.md             # Quick start
```

---

## `supplier_agent/` — package

| File | Role |
| --- | --- |
| `paths.py` | **L0** — single source of truth for all filesystem paths (`ROOT`, `DATA`, `PENDING`, etc.) |
| `models.py` | **L2** — frozen `Item` dataclass; `needs_reorder` property |
| `rules.py` | **L2** — load CSV, parse `policy.md` sections, `check_items()`, `find_item_by_sku()` |
| `finance.py` | **L3** — `SkuFinance`, expedite model, `finance_summary()`, `record_approval()` |
| `config.py` | **L4** — `.env` loader, `DRAFT_MODE`, `resolve_force_template()` |
| `draft_common.py` | **L4** — shared draft header (finance frontmatter), ship-to / requester from policy |
| `draft_template.py` | **L4** — default PO email body (no API) |
| `draft_claude.py` | **L4** — Anthropic integration; `generate_draft()` entry point |
| `drafts.py` | **L4–L5** — `create_drafts()`, `approve_draft()`, `list_drafts()`, `status_summary()` |
| `activity.py` | **L4** — `log_activity()`, `read_activity_rows()` → `activity.md` |
| `cli.py` | **L6** — argparse subcommands |
| `__main__.py` | Quick smoke: low stock + finance table |
| `__init__.py` | Package marker |

### Import rule

Only `cli.py` and `web/app.py` are entry points. Everything else is imported by tests or other modules.

---

## `web/`

| File | Role |
| --- | --- |
| `app.py` | **L7** — `HTTPServer` on `127.0.0.1:8787`; tabs Control / Finance / Drafts / Activity / Docs; POST handlers for run, approve, demo-reset |

No separate static assets — CSS is inline. Keeps deploy trivial (one file + package).

---

## `data/`

| File | Role |
| --- | --- |
| `inventory.csv` | **L1** — 14 real lab SKUs: on-hand, reorder points, costs, usage, `next_run_date` |
| `policy.md` | **L1** — ship-to, finance defaults, per-SKU overrides, supplier lead times |
| `spend_log.csv` | **L3** — historical + approved PO rows (append on approve) |
| `inventory.demo.csv` | Reserved — smaller demo set (path defined in `paths.py`) |
| `benchling_export_sample.csv` | **L8 planned** — stub for Benchling positioning demo |

---

## `drafts/`

| Folder | Role |
| --- | --- |
| `pending/` | Draft PO markdown awaiting human approve. Filename = draft ID. |
| `approved/` | Approved drafts — ops copies email body to mail client manually. |

Draft files are **markdown** with YAML-like frontmatter in blockquotes (human-readable, git-diffable).

---

## `prompts/`

| File | Role |
| --- | --- |
| `draft_po.txt` | System prompt for Claude when `DRAFT_MODE=claude` |

---

## `tests/`

| File | Covers |
| --- | --- |
| `test_rules.py` | Inventory load, policy overrides, 6 low-stock SKUs |
| `test_finance.py` | Expi293 hero SKU, expedite max(), spend log |
| `test_drafts.py` | Create, dedup, approve, template default |
| `test_config.py` | Draft mode env resolution |
| `test_activity.py` | Activity log round-trip |

---

## `docs/`

| File | Role |
| --- | --- |
| `README.md` | Documentation index (this library's table of contents) |
| `ARCHITECTURE.md` | System design and module graph |
| `PROJECT_STRUCTURE.md` | This file |
| `LAYERS.md` | L0–L9 build log |
| `DATA_MODEL.md` | CSV / markdown schemas |
| `OPERATIONS.md` | How to run day-to-day |
| `BENCHLING.md` | Positioning vs ELN |
| `DEMO_SCRIPT.md` | Interview demo script (L8) |
| `INTERVIEW_QA.md` | Q&A prep (L8) |
| `SUMMARY.md` | Final one-pager (L9) |

---

## Generated / runtime files (gitignored or local)

| Path | Created by |
| --- | --- |
| `activity.md` | `log_activity()` on draft, approve, run, reset |
| `drafts/pending/*.md` | `create_drafts()` |
| `drafts/approved/*.md` | `approve_draft()` |
| `.env` | You — copy from `.env.example` |
| `.pytest_cache/` | pytest |

---

## Path constants (`paths.py`)

All code references files via `supplier_agent.paths` — never hardcode paths in business logic:

```python
ROOT, DATA, INVENTORY, POLICY, SPEND_LOG
DRAFTS, PENDING, APPROVED
ACTIVITY, PROMPTS, DRAFT_PO_PROMPT
BENCHLING_SAMPLE
```

---

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — how modules connect
- [LAYERS.md](LAYERS.md) — when each file was introduced
