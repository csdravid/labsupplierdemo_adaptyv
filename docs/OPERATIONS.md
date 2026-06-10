# Operations

Day-to-day use: CLI, web UI, and draft configuration.

## Prerequisites

```bash
cd ~/Desktop/lab-supplier-agent-v2
pip install -r requirements.txt
python -m pytest tests/ -v   # sanity check
```

Optional Claude path:

```bash
cp .env.example .env
# DRAFT_MODE=claude
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## CLI reference

| Command | What it does |
| --- | --- |
| `python -m supplier_agent.cli status` | Screen-share summary: SKUs, low stock, draft counts |
| `python -m supplier_agent.cli check` | Table of items below reorder point |
| `python -m supplier_agent.cli finance` | ROI headline + at-risk SKU table |
| `python -m supplier_agent.cli list` | Pending and approved draft IDs |
| `python -m supplier_agent.cli run` | Check low stock + create drafts (default template) |
| `python -m supplier_agent.cli draft` | Draft only (no status preamble) |
| `python -m supplier_agent.cli approve <draft_id>` | Human gate + spend log row |
| `python -m supplier_agent.cli demo-reset` | Clear drafts + activity; keep inventory + spend log |

### Draft flags (on `run` and `draft`)

```bash
python -m supplier_agent.cli run              # template (default)
python -m supplier_agent.cli run --template   # explicit template
python -m supplier_agent.cli run --claude     # Claude if configured
```

### Approve with expedite surcharge recorded

```bash
python -m supplier_agent.cli approve A1435101_20260610 --expedite
```

---

## Web UI

```bash
python web/app.py           # opens browser
python web/app.py --no-open   # terminal only
```

URL: **http://127.0.0.1:8787**

| Tab | Content |
| --- | --- |
| **Control** | Stats, Check+draft, Draft with Claude, low-stock table |
| **Finance** | ROI headline, MTD spend, at-risk table |
| **Drafts** | Pending (with Approve) + approved list |
| **Activity** | Recent audit log |
| **Docs** | Architecture and operations documentation |

### Web vs CLI

Tabs replace redundant buttons — no separate "status" or "list" buttons. Only actions that **mutate state**: run, approve, demo reset (under Demo prep).

---

## Typical daily workflow

```
1. Ops runs agent (morning)
   → cli run  OR  web "Check + draft"

2. Finance reviews Finance tab
   → expedite exposure headline

3. Lab lead approves urgent SKUs
   → web Approve  OR  cli approve

4. Ops copies approved email body to Outlook
   → manual send (NO auto-send)

5. Activity log records full trail
```

---

## Demo rehearsal workflow

Before screen-share:

```bash
python -m supplier_agent.cli demo-reset   # or web Demo prep → Reset
python -m supplier_agent.cli run
python web/app.py
```

Walk through: Control → Finance (hero SKU) → Drafts (approve Expi293) → Activity.

---

## Draft modes

| Scenario | Config |
| --- | --- |
| Interview / offline | No `.env` needed — template |
| Try Claude emails | `DRAFT_MODE=claude` + API key |
| Force template in code | `create_drafts(..., force_template=True)` |

Details: repo-root `DRAFT_MODES.md`.

---

## Troubleshooting

| Issue | Fix |
| --- | --- |
| No new drafts on run | Drafts already exist for today (dedup) — `demo-reset` or wait until tomorrow |
| Claude still uses template | Check `DRAFT_MODE=claude` and API key; check `Draft source` in draft file |
| Finance exposure is 0 | All at-risk SKUs have pending drafts (exposure hidden once drafted) |
| Approve fails | Draft ID must match pending filename stem exactly |

---

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — timed walkthrough (L8)
