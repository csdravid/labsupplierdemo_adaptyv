# Overview

## Problem

Lab ops tracks consumables in spreadsheets. When stock drops below reorder point — especially before a scheduled run — delays trigger **expedite surcharges** (often thousands of CHF). Supplier emails are still drafted and sent manually, with little visibility into exposure.

## Solution

A lightweight agent that:

1. Applies **deterministic rules** to inventory + policy
2. Computes **finance context** (planned cost, expedite exposure, run-blocked)
3. Generates **draft PO emails** (template by default; Claude optional)
4. Requires **human approval** before anything is sent
5. Logs every action for audit

## Architecture (one paragraph)

CSV inventory and markdown policy feed `rules.py` and `finance.py`. Low-stock SKUs get draft markdown files via `drafts.py` using either `draft_template.py` or optional `draft_claude.py`. Humans approve via CLI or web UI; approvals append to `spend_log.csv` and `activity.md`. CLI and web are thin shells over the tested Python package.

## Benchling

**Benchling** = customers order protein expression **services** from their ELN.  
**This agent** = internal **consumables** reorder from external suppliers. Complementary workflows.

## Guardrails

- No SMTP / auto-send
- Human approve gate
- Template fallback if Claude unavailable
- Append-only activity log

## Tech stack

Python 3.11+, stdlib HTTP server for UI, optional `anthropic` SDK, pytest.
