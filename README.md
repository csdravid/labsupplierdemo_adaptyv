# Lab Supplier Agent

Internal lab **supplier / inventory ops** agent for consumables reordering.

**Rules → finance-aware draft PO email → human approve → audit log.** No auto-send.

Built for Adaptyv Biosystems (Lausanne)

## Quick start

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
python -m supplier_agent.cli status
python -m supplier_agent.cli run
python web/app.py    # http://127.0.0.1:8787
```

## What it does

| Step | Description |
| --- | --- |
| **Check** | Read `data/inventory.csv` + `data/policy.md`, flag SKUs below reorder |
| **Finance** | Days to stockout, expedite risk, run-blocked, CHF exposure |
| **Draft** | PO email markdown in `drafts/pending/` (template default, Claude optional) |
| **Approve** | Human gate → `drafts/approved/` + row in `data/spend_log.csv` |
| **Audit** | All actions in `activity.md` |

## Demo highlights

- **14 SKUs**, 6 below reorder in sample data
- Hero SKU **A1435101** (Expi293) — 0 on hand, run-blocked, ~CHF 12,465 planned / ~CHF 4,986 expedite exposure
- **23 pytest tests** — rules, finance, drafts, config

## Documentation

See **[docs/README.md](docs/README.md)** or the **Docs** tab in the web UI.

## Configuration

Copy `.env.example` to `.env` only if using Claude drafts:

```
DRAFT_MODE=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Default is **template** (no API). See [DRAFT_MODES.md](DRAFT_MODES.md).

## Project layout

```
supplier_agent/   # Core package (rules, finance, drafts, CLI)
web/app.py        # Localhost UI :8787
data/             # inventory.csv, policy.md, spend_log.csv
drafts/           # pending → approved
docs/             # Architecture and operations guides
tests/
```

## License

Demonstration project — contact author for use.
