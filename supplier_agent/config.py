"""Runtime config — template drafts by default; Claude API opt-in."""
from __future__ import annotations

import os
from pathlib import Path

from supplier_agent.paths import ROOT


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def draft_mode() -> str:
    """`template` (default) or `claude`."""
    return os.environ.get("DRAFT_MODE", "template").strip().lower()


def use_claude_drafts() -> bool:
    return draft_mode() == "claude"


def anthropic_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip() or None


def claude_ready() -> bool:
    return use_claude_drafts() and anthropic_api_key() is not None


def draft_mode_status() -> str:
    mode = draft_mode()
    if mode == "claude":
        if anthropic_api_key():
            return "claude (API key set)"
        return "claude requested but ANTHROPIC_API_KEY missing — will fall back to template"
    return "template (default — no API calls)"


def resolve_force_template(force_template: bool | None) -> bool:
    """How generate_draft / create_drafts pick template vs Claude.

    - force_template=True  → always template
    - force_template=False → try Claude if DRAFT_MODE=claude + key, else template
    - force_template=None  → template unless DRAFT_MODE=claude and key set
    """
    if force_template is True:
        return True
    if force_template is False:
        return not claude_ready()
    return not claude_ready()
