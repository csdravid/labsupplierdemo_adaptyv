#!/usr/bin/env python3
"""Lab supplier agent — localhost web UI (127.0.0.1:8787).

Usage:
    python web/app.py
    python web/app.py --no-open
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PORT = 8787

# Sidebar order for Docs tab (stem → label)
DOC_PAGES: list[tuple[str, str]] = [
    ("README", "Index"),
    ("OVERVIEW", "Overview"),
    ("ARCHITECTURE", "Architecture"),
    ("PROJECT_STRUCTURE", "Structure"),
    ("LAYERS", "Layers"),
    ("DATA_MODEL", "Data model"),
    ("OPERATIONS", "Operations"),
    ("BENCHLING", "Benchling"),
    ("DEMO_WALKTHROUGH", "Demo"),
]

sys.path.insert(0, str(ROOT))

from supplier_agent.activity import log_activity, read_activity_rows
from supplier_agent.config import draft_mode_status
from supplier_agent.drafts import approve_draft, create_drafts, list_drafts, read_draft_summary, status_summary
from supplier_agent.finance import analyze_item, finance_summary
from supplier_agent.paths import ACTIVITY, APPROVED, PENDING
from supplier_agent.rules import check_items

TABS = ("control", "finance", "drafts", "activity", "docs")


def _badge(text: str, kind: str) -> str:
    return f'<span class="badge {kind}">{html.escape(text)}</span>'


def _source_badge(source: str) -> str:
    s = (source or "template").lower()
    cls = "claude" if "claude" in s else "template"
    return _badge(s, cls)


def _risk_badges(meta: dict[str, str]) -> str:
    parts = []
    if meta.get("Expedite risk", "").lower().startswith("yes"):
        parts.append(_badge("expedite risk", "risk"))
    if meta.get("Run blocked", "").lower().startswith("yes"):
        parts.append(_badge("run blocked", "blocked"))
    return " ".join(parts)


def _low_stock_html() -> str:
    low = check_items()
    if not low:
        return '<p class="muted">All items above reorder point.</p>'
    rows = []
    for i in low:
        fin = analyze_item(i)
        flags = []
        if fin.expedite_risk:
            flags.append(_badge("expedite", "risk"))
        if fin.run_blocked:
            flags.append(_badge("run blocked", "blocked"))
        if i.critical:
            flags.append(_badge("critical", "critical"))
        flag_html = " ".join(flags)
        rows.append(
            f"<tr><td>{html.escape(i.sku)}</td>"
            f"<td>{html.escape(i.item)} {flag_html}</td>"
            f"<td>{i.on_hand}</td>"
            f"<td>{i.reorder_point}</td>"
            f"<td>{i.reorder_qty}</td>"
            f"<td>CHF {fin.planned_cost_chf:g}</td>"
            f"<td>{html.escape(i.supplier)}</td></tr>"
        )
    return (
        "<table><tr><th>SKU</th><th>Item</th><th>On hand</th>"
        "<th>Reorder at</th><th>Qty</th><th>Planned</th><th>Supplier</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _finance_html() -> str:
    s = finance_summary()
    rows = []
    for r in s["at_risk_skus"]:
        flags = []
        if r.expedite_risk:
            flags.append(_badge("expedite", "risk"))
        if r.run_blocked:
            flags.append(_badge("run blocked", "blocked"))
        if r.draft_pending:
            flags.append(_badge("draft pending", "pending"))
        rows.append(
            f"<tr><td>{html.escape(r.item.sku)}</td>"
            f"<td>{html.escape(r.item.item[:40])}</td>"
            f"<td>{r.days_until_stockout}</td>"
            f"<td>{r.lead_time_days}d</td>"
            f"<td>CHF {r.planned_cost_chf:g}</td>"
            f"<td>CHF {r.expedite_surcharge_chf:g}</td>"
            f"<td>{' '.join(flags)}</td></tr>"
        )
    table = (
        "<table><tr><th>SKU</th><th>Item</th><th>Days left</th>"
        "<th>Lead</th><th>Planned</th><th>Surcharge</th><th>Flags</th></tr>"
        + "".join(rows)
        + "</table>"
        if rows
        else '<p class="muted">No at-risk SKUs.</p>'
    )
    return f"""
    <div class="headline">{html.escape(s["roi_headline"])}</div>
    <div class="stats" style="margin-top:12px">
      <div class="stat"><div class="n">CHF {s["monthly_spend_chf"]:g}</div><div class="l">Spend MTD</div></div>
      <div class="stat"><div class="n">CHF {s["expedite_spend_mtd"]:g}</div><div class="l">Expedite MTD</div></div>
      <div class="stat"><div class="n">{s["at_risk_count"]}</div><div class="l">At risk</div></div>
      <div class="stat"><div class="n">{s["run_blocked_count"]}</div><div class="l">Run blocked</div></div>
    </div>
    <div class="card" style="margin-top:16px">
      <h2>At-risk SKUs</h2>
      {table}
    </div>
    """


def _drafts_html(pending_only: bool = True) -> str:
    pending, approved = list_drafts()
    paths = pending if pending_only else approved
    if not paths:
        label = "pending" if pending_only else "approved"
        return f'<p class="muted">No {label} drafts.</p>'
    blocks = []
    for p in paths:
        meta = read_draft_summary(p)
        subject = meta.get("Subject", p.stem)
        source = meta.get("Draft source", "template")
        risk = _risk_badges(meta)
        exposure = meta.get("Expedite exposure", "")
        body_preview = html.escape(meta["body"][:1200])
        if pending_only:
            blocks.append(
                f'<div class="draft-card">'
                f"<h3>{html.escape(p.stem)} {_source_badge(source)} {risk}</h3>"
                f'<p class="muted">{html.escape(subject)}'
                f'{f" · {html.escape(exposure)}" if exposure else ""}</p>'
                f'<details><summary>Preview email</summary><pre>{body_preview}</pre></details>'
                f'<form method="post" action="/approve">'
                f'<input type="hidden" name="draft_id" value="{html.escape(p.stem)}">'
                f'<button type="submit" class="ok">Approve</button>'
                f"</form></div>"
            )
        else:
            blocks.append(
                f'<div class="draft-card">'
                f"<h3>{html.escape(p.stem)} {_source_badge(source)} {risk}</h3>"
                f'<p class="muted">{html.escape(subject)}</p>'
                f"</div>"
            )
    return "\n".join(blocks)


def _doc_link_href(url: str) -> str | None:
    if url.startswith(("http://", "https://", "mailto:")):
        return None
    name = Path(url.split("#")[0]).name
    if not name.endswith(".md"):
        return None
    stem = name[:-3]
    if (DOCS_DIR / f"{stem}.md").exists():
        return f"/?tab=docs&doc={quote(stem)}"
    return None


def _inline_md(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)

    def _link(m: re.Match[str]) -> str:
        label, url = m.group(1), m.group(2)
        doc_href = _doc_link_href(url)
        if doc_href:
            return f'<a href="{doc_href}">{label}</a>'
        return f'<a href="{html.escape(url)}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)
    return text


def _render_markdown(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_code = False
    code_buf: list[str] = []
    list_buf: list[str] = []

    def flush_list() -> None:
        nonlocal list_buf
        if list_buf:
            out.append("<ul>" + "".join(f"<li>{_inline_md(x)}</li>" for x in list_buf) + "</ul>")
            list_buf = []

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush_list()
            if in_code:
                out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if not line.strip():
            flush_list()
            i += 1
            continue
        if line.strip() == "---":
            flush_list()
            out.append("<hr>")
            i += 1
            continue
        if line.startswith("# "):
            flush_list()
            out.append(f"<h1>{_inline_md(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            flush_list()
            out.append(f"<h2>{_inline_md(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            flush_list()
            out.append(f"<h3>{_inline_md(line[4:].strip())}</h3>")
        elif line.startswith("> "):
            flush_list()
            out.append(f"<blockquote>{_inline_md(line[2:].strip())}</blockquote>")
        elif line.lstrip().startswith("|") and "|" in line:
            flush_list()
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            if len(rows) >= 2 and all(set(c) <= {"-", ":"} for c in rows[1]):
                rows = [rows[0]] + rows[2:]
            if rows:
                hdr = rows[0]
                body = rows[1:]
                out.append(
                    "<table><tr>"
                    + "".join(f"<th>{_inline_md(c)}</th>" for c in hdr)
                    + "</tr>"
                    + "".join(
                        "<tr>" + "".join(f"<td>{_inline_md(c)}</td>" for c in r) + "</tr>" for r in body
                    )
                    + "</table>"
                )
            continue
        elif re.match(r"^\s*-\s+", line):
            list_buf.append(re.sub(r"^\s*-\s+", "", line))
        else:
            flush_list()
            out.append(f"<p>{_inline_md(line.strip())}</p>")
        i += 1

    flush_list()
    if in_code and code_buf:
        out.append(f"<pre><code>{html.escape(chr(10).join(code_buf))}</code></pre>")
    return "\n".join(out)


def _docs_nav(current: str) -> str:
    allowed = {stem for stem, _ in DOC_PAGES}
    if current not in allowed:
        current = "README"
    links = "".join(
        f'<a class="{"active" if stem == current else ""}" '
        f'href="/?tab=docs&doc={quote(stem)}">{html.escape(label)}</a>'
        for stem, label in DOC_PAGES
    )
    return f'<nav class="doc-nav" aria-label="Documentation">{links}</nav>'


def _docs_html(current: str = "README") -> str:
    stem = current.replace(".md", "")
    allowed = {s for s, _ in DOC_PAGES}
    if stem not in allowed:
        stem = "README"
    path = DOCS_DIR / f"{stem}.md"
    if not path.exists():
        return '<p class="muted">Documentation file not found.</p>'
    rendered = _render_markdown(path.read_text(encoding="utf-8"))
    edit_note = (
        f'<p class="muted doc-edit">Source: <code>docs/{stem}.md</code>'
        " — edit in your editor; refresh browser to see changes."
        " Repo-root guides: <code>DRAFT_MODES.md</code>, <code>DATA_GUIDE.md</code>.</p>"
    )
    return f'{_docs_nav(stem)}<div class="card doc-content">{rendered}{edit_note}</div>'


def _demo_reset() -> None:
    for folder in (PENDING, APPROVED):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
    if ACTIVITY.exists():
        ACTIVITY.unlink()
    log_activity("demo reset", "cleared drafts + activity", "spend_log kept")


def _activity_html() -> str:
    rows = read_activity_rows(25)
    if not rows:
        return '<p class="muted">No activity yet.</p>'
    trs = []
    for ts, action, detail, follow in reversed(rows):
        trs.append(
            f"<tr><td>{html.escape(ts)}</td><td>{html.escape(action)}</td>"
            f"<td>{html.escape(detail)}</td><td>{html.escape(follow)}</td></tr>"
        )
    return (
        "<table><tr><th>When</th><th>Action</th><th>Detail</th><th>Follow-up</th></tr>"
        + "".join(trs)
        + "</table>"
    )


def _page(msg: str = "", tab: str = "control", doc: str = "README") -> bytes:
    if tab not in TABS:
        tab = "control"
    s = status_summary()
    mode = draft_mode_status()
    flash = f'<p class="flash">{html.escape(msg)}</p>' if msg else ""
    tab_links = "".join(
        f'<a class="{"active" if tab == t else ""}" href="/?tab={t}">{t.title()}</a>'
        for t in TABS
    )

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lab Supplier Agent</title>
  <style>
    :root {{
      --bg: #f5f5f5; --card: #ffffff; --border: #e0e0e0;
      --text: #1a1a1a; --muted: #666666; --accent: #0066cc; --ok: #22863a;
      --warn: #c41e3a; --purple: #6f42c1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      background: var(--bg); color: var(--text); margin: 0; padding: 24px 20px;
      line-height: 1.5; -webkit-font-smoothing: antialiased;
    }}
    .wrap {{ max-width: 960px; margin: 0 auto; }}
    h1 {{ margin: 0 0 4px; font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }}
    .sub {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 20px; }}
    .flash {{ background: #edf7ed; border: 1px solid #b7dfb9; color: #1e4620;
      padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; }}
    .headline {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
      padding: 14px 16px; font-size: 0.95rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .tabs {{ display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap; }}
    .tabs a {{ color: var(--muted); text-decoration: none; padding: 8px 16px;
      border: 1px solid var(--border); border-radius: 6px; background: var(--card);
      font-size: 0.875rem; }}
    .tabs a:hover {{ border-color: #ccc; color: var(--text); }}
    .tabs a.active {{ color: var(--accent); border-color: var(--accent); font-weight: 500; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 16px; }}
    .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
      padding: 14px 12px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .stat .n {{ font-size: 1.5rem; font-weight: 600; color: var(--text); }}
    .stat .l {{ color: var(--muted); font-size: 0.75rem; margin-top: 2px; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
      padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .card h2 {{ margin: 0 0 12px; font-size: 0.95rem; font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 0.85rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }}
    tr:last-child td {{ border-bottom: none; }}
    button {{ font-family: inherit; background: var(--accent); color: #fff; border: none;
      padding: 9px 16px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500; }}
    button:hover {{ filter: brightness(0.95); }}
    button.ok {{ background: var(--ok); }}
    button.secondary {{ background: var(--card); border: 1px solid var(--border); color: var(--text); }}
    button.danger {{ background: var(--card); border: 1px solid #e8b4b8; color: var(--warn); }}
    .row {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .draft-card {{ border: 1px solid var(--border); border-radius: 8px; padding: 14px;
      margin-bottom: 12px; background: #fafafa; }}
    .draft-card h3 {{ margin: 0 0 6px; font-size: 0.95rem; font-weight: 600; }}
    pre {{ white-space: pre-wrap; font-size: 0.8rem; background: #f9f9f9; border: 1px solid var(--border);
      padding: 12px; border-radius: 6px; overflow-x: auto; color: #333; }}
    .badge {{ font-size: 0.68rem; padding: 2px 8px; border-radius: 999px; margin-left: 4px;
      white-space: nowrap; font-weight: 500; }}
    .badge.claude {{ background: #e8f0fe; color: #1a56db; }}
    .badge.template {{ background: #fef9e7; color: #92600a; }}
    .badge.risk {{ background: #fde8e8; color: var(--warn); }}
    .badge.blocked {{ background: #f3e8ff; color: var(--purple); }}
    .badge.critical {{ background: #fff4e5; color: #b45309; }}
    .badge.pending {{ background: #f0f0f0; color: var(--muted); }}
    .guard {{ color: var(--ok); font-weight: 500; }}
    details.demo-tools {{ margin-top: 8px; }}
    details.demo-tools summary {{ cursor: pointer; user-select: none; }}
    details.demo-tools[open] {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }}
    .doc-content h1 {{ font-size: 1.35rem; margin: 0 0 12px; }}
    .doc-content h2 {{ font-size: 1.1rem; margin: 24px 0 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
    .doc-content h3 {{ font-size: 1rem; margin: 18px 0 8px; }}
    .doc-content p, .doc-content li {{ font-size: 0.9rem; }}
    .doc-content ul {{ margin: 8px 0 12px; padding-left: 1.4rem; }}
    .doc-content blockquote {{ margin: 12px 0; padding: 10px 14px; background: #f9f9f9;
      border-left: 3px solid var(--accent); color: var(--muted); }}
    .doc-content code {{ font-size: 0.85em; background: #f0f0f0; padding: 1px 5px; border-radius: 3px; }}
    .doc-content pre {{ margin: 12px 0; }}
    .doc-content pre code {{ background: none; padding: 0; }}
    .doc-content a {{ color: var(--accent); }}
    .doc-content hr {{ border: none; border-top: 1px solid var(--border); margin: 20px 0; }}
    .doc-edit {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border); }}
    .doc-nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }}
    .doc-nav a {{ font-size: 0.8rem; padding: 6px 12px; border: 1px solid var(--border);
      border-radius: 6px; text-decoration: none; color: var(--muted); background: var(--card); }}
    .doc-nav a:hover {{ color: var(--text); border-color: #ccc; }}
    .doc-nav a.active {{ color: var(--accent); border-color: var(--accent); font-weight: 500; }}
  </style>
</head>
<body>
<div class="wrap">
  <h1>Lab Supplier Agent</h1>
  <p class="sub">Threshold rules → draft PO → human approve · <span class="guard">NO auto-send</span><br>
  <span class="muted">Draft mode: {html.escape(mode)}</span></p>
  {flash}

  <nav class="tabs">{tab_links}</nav>

  <div class="panel {'active' if tab == 'control' else ''}" id="control">
    <div class="stats">
      <div class="stat"><div class="n">{s['total_skus']}</div><div class="l">SKUs</div></div>
      <div class="stat"><div class="n">{s['low_stock']}</div><div class="l">Below threshold</div></div>
      <div class="stat"><div class="n">{s['pending']}</div><div class="l">Pending</div></div>
      <div class="stat"><div class="n">{s['approved']}</div><div class="l">Approved</div></div>
    </div>
    <div class="card">
      <h2>Actions</h2>
      <div class="row">
        <form method="post" action="/run"><button type="submit">Check + draft</button></form>
        <form method="post" action="/run-claude"><button type="submit" class="secondary">Draft with Claude</button></form>
      </div>
      <p class="muted" style="margin-top:10px">Same as <code>cli run</code> — template by default. Claude needs <code>DRAFT_MODE=claude</code> in .env.</p>
      <details class="demo-tools">
        <summary class="muted">Demo prep (CLI: demo-reset)</summary>
        <p class="muted">Clears pending/approved drafts and activity. Keeps inventory and spend log.</p>
        <form method="post" action="/demo-reset"
          onsubmit="return confirm('Clear all drafts and activity? Spend log is kept.');">
          <button type="submit" class="danger">Reset demo</button>
        </form>
      </details>
    </div>
    <div class="card">
      <h2>Low stock</h2>
      {_low_stock_html()}
    </div>
  </div>

  <div class="panel {'active' if tab == 'finance' else ''}" id="finance">
    {_finance_html()}
  </div>

  <div class="panel {'active' if tab == 'drafts' else ''}" id="drafts">
    <div class="card">
      <h2>Pending approval</h2>
      {_drafts_html(pending_only=True)}
    </div>
    <div class="card">
      <h2>Approved (ready to send manually)</h2>
      {_drafts_html(pending_only=False)}
    </div>
  </div>

  <div class="panel {'active' if tab == 'activity' else ''}" id="activity">
    <div class="card">
      <h2>Recent activity</h2>
      {_activity_html()}
    </div>
  </div>

  <div class="panel {'active' if tab == 'docs' else ''}" id="docs">
    {_docs_html(doc)}
  </div>
</div>
</body>
</html>"""
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass

    def _redirect(self, msg: str, tab: str = "control", *, doc: str = "README") -> None:
        loc = f"/?msg={quote(msg)}&tab={quote(tab)}"
        if tab == "docs":
            loc += f"&doc={quote(doc)}"
        self.send_response(303)
        self.send_header("Location", loc)
        self.end_headers()

    def do_GET(self) -> None:
        q = parse_qs(urlparse(self.path).query)
        tab = (q.get("tab") or ["control"])[0]
        msg = (q.get("msg") or [""])[0]
        doc = (q.get("doc") or ["README"])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_page(msg, tab, doc))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        form = {k: v[0] for k, v in parse_qs(body).items()}
        path = urlparse(self.path).path
        try:
            if path == "/run":
                low = check_items()
                created = create_drafts(low, force_template=None)
                log_activity("web run", f"{len(low)} low, {len(created)} new drafts", "template default")
                self._redirect("Agent run complete — check Drafts tab.", tab="drafts")
            elif path == "/run-claude":
                low = check_items()
                created = create_drafts(low, force_template=False)
                log_activity("web run", f"{len(low)} low, {len(created)} new drafts", "claude requested")
                self._redirect("Run complete (Claude if configured).", tab="drafts")
            elif path == "/approve":
                did = form.get("draft_id", "").strip()
                dest = approve_draft(did)
                self._redirect(f"Approved {did} → {dest.name}", tab="drafts")
            elif path == "/demo-reset":
                _demo_reset()
                self._redirect("Demo reset — drafts and activity cleared.", tab="control")
            else:
                self.send_error(404)
        except Exception as exc:
            self._redirect(f"Error: {exc}", tab="control")


def _open_browser(url: str) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", url], check=False)
            return
    except Exception:
        pass
    webbrowser.open(url)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print("Lab Supplier Agent web UI running.")
    print(f"  URL: {url}")
    print(f"  Mode: {draft_mode_status()}")
    print("  Keep this Terminal open. Press Ctrl+C to stop.")
    if "--no-open" not in argv:
        _open_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
