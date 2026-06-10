#!/usr/bin/env python3
"""Supplier reorder agent CLI."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from supplier_agent.config import draft_mode_status
from supplier_agent.drafts import approve_draft, create_drafts, list_drafts, status_summary
from supplier_agent.finance import format_finance_table
from supplier_agent.paths import ACTIVITY, APPROVED, PENDING, ROOT, SPEND_LOG
from supplier_agent.rules import check_items


def _draft_kwargs(args: argparse.Namespace) -> dict:
    if getattr(args, "claude", False):
        return {"force_template": False}
    if getattr(args, "template", False):
        return {"force_template": True}
    return {"force_template": None}


def cmd_check(_: argparse.Namespace) -> int:
    low = check_items()
    if not low:
        print("All items above reorder point.")
        return 0
    print(f"# Low stock ({len(low)} items)\n")
    print("| SKU | Item | On hand | Reorder at | Order qty | Supplier |")
    print("| --- | --- | --- | --- | --- | --- |")
    for i in low:
        crit = " CRITICAL" if i.critical else ""
        print(
            f"| {i.sku} | {i.item}{crit} | {i.on_hand} | {i.reorder_point} "
            f"| {i.reorder_qty} | {i.supplier} |"
        )
    return 0


def cmd_finance(_: argparse.Namespace) -> int:
    print(format_finance_table())
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    created = create_drafts(**_draft_kwargs(args))
    print(f"Draft mode: {draft_mode_status()}")
    if not created:
        print("No new drafts (either stock OK or drafts already pending).")
        return 0
    print(f"Created {len(created)} draft(s):\n")
    for p in created:
        print(f"  - {p}")
    print("\nApprove: python -m supplier_agent.cli approve <draft_id>")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    pending, approved = list_drafts()
    print("# Draft PO emails\n")
    print(f"## Pending ({len(pending)})")
    if pending:
        for p in pending:
            print(f"- `{p.stem}`")
    else:
        print("- _none_")
    print(f"\n## Approved ({len(approved)})")
    if approved:
        for p in approved:
            print(f"- `{p.stem}`")
    else:
        print("- _none_")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    dest = approve_draft(args.draft_id, expedite=args.expedite)
    print(f"Approved: {dest}")
    print("Logged to spend_log.csv — copy email body to mail client and send manually.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    low = check_items()
    print(f"Draft mode: {draft_mode_status()}")
    print(f"Low stock: {len(low)} item(s)")
    created = create_drafts(low, **_draft_kwargs(args))
    print(f"New drafts: {len(created)}")
    pending, approved = list_drafts()
    print(f"Pending approval: {len(pending)} · Approved (ready to send): {len(approved)}")
    if pending:
        print("\nPending:")
        for p in pending:
            print(f"  - {p.stem}")
    from supplier_agent.activity import log_activity

    log_activity("daily run", f"{len(low)} low, {len(created)} new drafts", f"{len(pending)} pending")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    s = status_summary()
    low = s["low_items"]
    pending = s["pending_paths"]
    print("═" * 50)
    print("  SUPPLIER REORDER AGENT — status")
    print("═" * 50)
    print(f"  Draft mode:         {draft_mode_status()}")
    print(f"  Inventory SKUs:     {s['total_skus']}")
    print(f"  Below threshold:    {s['low_stock']}")
    print(f"  Drafts pending:     {s['pending']}")
    print(f"  Drafts approved:    {s['approved']}")
    print("  Guardrail:          NO auto-send")
    print("═" * 50)
    if low:
        print("\nNeeds reorder:")
        for i in low:
            flag = " [draft pending]" if any(p.stem.startswith(f"{i.sku}_") for p in pending) else ""
            print(f"  • {i.sku}: {i.on_hand}/{i.reorder_point} — {i.item}{flag}")
    return 0


def cmd_demo_reset(_: argparse.Namespace) -> int:
    """Clear pending drafts and activity for a clean demo (keeps spend_log history)."""
    for folder in (PENDING, APPROVED):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
    if ACTIVITY.exists():
        ACTIVITY.unlink()
    print("Demo reset: cleared pending/approved drafts and activity.md")
    print(f"Kept: {SPEND_LOG.name}, {ROOT / 'data' / 'inventory.csv'}")
    return 0


def _add_draft_flags(parser: argparse.ArgumentParser) -> None:
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--template",
        action="store_true",
        help="force template drafts (default behaviour)",
    )
    g.add_argument(
        "--claude",
        action="store_true",
        help="use Claude when DRAFT_MODE=claude and API key set",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Lab supplier reorder agent")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="show items below reorder point").set_defaults(func=cmd_check)
    sub.add_parser("finance", help="expedite exposure and at-risk SKUs").set_defaults(func=cmd_finance)
    sub.add_parser("list", help="list pending and approved drafts").set_defaults(func=cmd_list)
    sub.add_parser("status", help="summary for screen-share").set_defaults(func=cmd_status)
    sub.add_parser("demo-reset", help="clear drafts + activity for demo").set_defaults(func=cmd_demo_reset)

    d = sub.add_parser("draft", help="create draft PO emails for low stock")
    _add_draft_flags(d)
    d.set_defaults(func=cmd_draft)

    r = sub.add_parser("run", help="check + draft (typical daily run)")
    _add_draft_flags(r)
    r.set_defaults(func=cmd_run)

    a = sub.add_parser("approve", help="human gate — approve draft and log spend")
    a.add_argument("draft_id", help="e.g. A1435101_20260610")
    a.add_argument(
        "--expedite",
        action="store_true",
        help="record expedite surcharge on this PO (default: standard shipping only)",
    )
    a.set_defaults(func=cmd_approve)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
