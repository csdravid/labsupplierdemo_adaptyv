# Push to GitHub

This folder is the **shareable copy** for Adaptyv — no personal interview notes, no session drafts, public Docs tab.

## What's included vs your local `lab-supplier-agent-v2`

| Included | Excluded |
| --- | --- |
| Full agent code + tests | `GEMINI_RESEARCH_PROMPT.md` |
| Sample data + policy | Personal `INTERVIEW_QA`, `DEMO_SCRIPT` prep |
| Architecture docs | Password-gated Docs tab |
| One sample approved draft | Your pending drafts / activity history |
| Empty `drafts/pending/` | `.env` |

**Tomorrow:** demo from `lab-supplier-agent-v2` (your live state). **GitHub:** share this folder.

## Commands

```bash
cd ~/Desktop/lab-supplier-agent-adaptyv
python -m pytest tests/ -v

git init
git add .
git status    # confirm .env is not listed
git commit -m "Lab supplier agent — Adaptyv demo"

# Create private repo on github.com, then:
git remote add origin https://github.com/YOUR_USER/lab-supplier-agent-adaptyv.git
git branch -M main
git push -u origin main
```

Use a **private** repo — `inventory.csv` contains supplier contact emails.
