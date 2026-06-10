# Draft modes — template (default) vs Claude API

## Default: template (no API)

Interview demos and daily testing use **template** drafts. Same finance frontmatter, no network, no cost.

```bash
# Default — no .env required
python -c "from supplier_agent.drafts import create_drafts; from supplier_agent.rules import check_items; create_drafts(check_items())"
```

## Parallel track: Claude API

When you want natural-language emails from Claude:

```bash
cp .env.example .env
# Edit .env:
#   DRAFT_MODE=claude
#   ANTHROPIC_API_KEY=sk-ant-...

python -c "from supplier_agent.drafts import create_drafts; from supplier_agent.rules import check_items; create_drafts(check_items())"
```

Drafts will show `**Draft source:** claude` and include the model name.

## Overrides (code / future CLI)

| Call | Behaviour |
|------|-----------|
| `create_drafts()` | Respect `DRAFT_MODE` in `.env` (default template) |
| `create_drafts(..., force_template=True)` | Always template |
| `create_drafts(..., force_template=False)` | Claude if `DRAFT_MODE=claude` + key, else template |

## Check current mode

```bash
python -c "from supplier_agent.config import draft_mode_status; print(draft_mode_status())"
```

## Fallback

If `DRAFT_MODE=claude` but the API fails (no key, network, rate limit), drafts **fall back to template** automatically — demo never breaks.
