# Demo walkthrough

## Setup

```bash
pip install -r requirements.txt
python -m supplier_agent.cli run
python web/app.py
```

Open **http://127.0.0.1:8787**

## Flow (~3 minutes)

### 1. Control

- 14 SKUs, 6 below reorder
- Low-stock table with expedite / run-blocked / critical badges
- **Check + draft** creates pending PO emails (template default)

### 2. Finance

- ROI headline — expedite exposure in CHF
- At-risk SKU table sorted by urgency
- **A1435101 Expi293**: 0 on hand, ~CHF 12,465 planned, ~CHF 4,986 expedite exposure, run blocked

### 3. Drafts

- Preview draft email markdown
- **Approve** — human gate; moves to approved, logs spend

### 4. Activity

- Audit trail: draft, approve, run events

## CLI equivalent

```bash
python -m supplier_agent.cli status
python -m supplier_agent.cli finance
python -m supplier_agent.cli list
python -m supplier_agent.cli approve <draft_id>
```

## Key talking point

> "No send button. Ops copies the approved email to their mail client. The agent proposes; humans commit."
