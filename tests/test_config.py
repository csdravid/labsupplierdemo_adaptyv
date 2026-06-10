from __future__ import annotations

import os

from supplier_agent.config import claude_ready, draft_mode, resolve_force_template, use_claude_drafts


def test_default_is_template(monkeypatch):
    monkeypatch.delenv("DRAFT_MODE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    assert draft_mode() == "template"
    assert use_claude_drafts() is False
    assert claude_ready() is False
    assert resolve_force_template(None) is True


def test_claude_mode_with_key(monkeypatch):
    monkeypatch.setenv("DRAFT_MODE", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    assert use_claude_drafts() is True
    assert claude_ready() is True
    assert resolve_force_template(None) is False


def test_claude_mode_without_key(monkeypatch):
    monkeypatch.setenv("DRAFT_MODE", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert claude_ready() is False
    assert resolve_force_template(None) is True


def test_force_flags_override_env(monkeypatch):
    monkeypatch.setenv("DRAFT_MODE", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert resolve_force_template(True) is True
    assert resolve_force_template(False) is False
