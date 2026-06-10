from __future__ import annotations

import supplier_agent.drafts as drafts_mod
import supplier_agent.finance as finance_mod

from supplier_agent.drafts import (
    approve_draft,
    create_drafts,
    draft_id,
    existing_pending_ids,
    sku_from_draft_id,
)
from supplier_agent.rules import check_items, load_inventory


def test_create_drafts_default_is_template(tmp_path, monkeypatch):
    monkeypatch.delenv("DRAFT_MODE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-would-use-if-not-template-default")
    monkeypatch.setattr(drafts_mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(drafts_mod, "APPROVED", tmp_path / "approved")
    import supplier_agent.activity as act

    monkeypatch.setattr(act, "ACTIVITY", tmp_path / "activity.md")

    low = check_items()[:1]
    created = create_drafts(low)
    assert len(created) == 1
    assert "Draft source:** template" in created[0].read_text(encoding="utf-8")


def test_create_template_drafts(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts_mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(drafts_mod, "APPROVED", tmp_path / "approved")
    import supplier_agent.activity as act

    monkeypatch.setattr(act, "ACTIVITY", tmp_path / "activity.md")

    low = check_items()
    created = create_drafts(low, force_template=True)
    assert len(created) == len(low)
    for path in created:
        text = path.read_text(encoding="utf-8")
        assert "Draft source:** template" in text
        assert "Expedite risk:" in text
        assert "Planned cost:" in text
        assert "PENDING" in text


def test_draft_dedup_same_day(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts_mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(drafts_mod, "APPROVED", tmp_path / "approved")
    import supplier_agent.activity as act

    monkeypatch.setattr(act, "ACTIVITY", tmp_path / "activity.md")

    low = check_items()[:1]
    first = create_drafts(low, force_template=True)
    second = create_drafts(low, force_template=True)
    assert len(first) == 1
    assert len(second) == 0


def test_sku_from_draft_id():
    assert sku_from_draft_id("A1435101_20260610") == "A1435101"
    assert sku_from_draft_id("S1120-3810_20260610") == "S1120-3810"


def test_approve_draft_moves_and_logs_spend(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts_mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(drafts_mod, "APPROVED", tmp_path / "approved")
    import supplier_agent.activity as act

    monkeypatch.setattr(act, "ACTIVITY", tmp_path / "activity.md")
    monkeypatch.setattr(finance_mod, "SPEND_LOG", tmp_path / "spend_log.csv")

    low = check_items()[:1]
    created = create_drafts(low, force_template=True)
    did = created[0].stem
    dest = approve_draft(did)
    assert dest.parent.name == "approved"
    assert not (tmp_path / "pending" / f"{did}.md").exists()
    text = dest.read_text(encoding="utf-8")
    assert "APPROVED" in text
    assert "approved — ready to send manually" in text
    spend = (tmp_path / "spend_log.csv").read_text(encoding="utf-8")
    assert f"PO-{did}" in spend
    assert low[0].sku in spend


def test_approve_draft_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(drafts_mod, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(drafts_mod, "APPROVED", tmp_path / "approved")
    import pytest

    with pytest.raises(FileNotFoundError):
        approve_draft("MISSING_20260610")


def test_expi293_draft_has_high_exposure():
    item = next(i for i in load_inventory() if i.sku == "A1435101")
    from supplier_agent.draft_template import draft_email

    did = draft_id(item)
    text = draft_email(item, did)
    assert "Expedite exposure:** CHF 4986" in text or "4986" in text
    assert "Run blocked:** yes" in text
