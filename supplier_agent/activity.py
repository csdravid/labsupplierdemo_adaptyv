from __future__ import annotations

from datetime import datetime

from supplier_agent.paths import ACTIVITY


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def log_activity(action: str, detail: str, follow_up: str = "") -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = f"| {ts} | Supplier | {_cell(action)} | {_cell(detail)} | {_cell(follow_up)} |\n"
    if not ACTIVITY.exists():
        ACTIVITY.write_text(
            "# Supplier agent — activity log\n\n"
            "| timestamp | domain | action | detail | follow-up |\n"
            "| --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    with ACTIVITY.open("a", encoding="utf-8") as f:
        f.write(row)


def read_activity_rows(limit: int = 20) -> list[tuple[str, str, str, str]]:
    if not ACTIVITY.exists():
        return []
    rows: list[tuple[str, str, str, str]] = []
    for line in ACTIVITY.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 5 and parts[0] != "timestamp":
            rows.append((parts[0], parts[2], parts[3], parts[4]))
    return rows[-limit:]
