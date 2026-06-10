from __future__ import annotations

from supplier_agent.activity import log_activity, read_activity_rows


def test_read_activity_rows(tmp_path, monkeypatch):
    import supplier_agent.activity as act

    log_file = tmp_path / "activity.md"
    monkeypatch.setattr(act, "ACTIVITY", log_file)
    log_activity("draft PO", "SKU-1 → test.md", "source=template")
    log_activity("approve PO", "SKU-1", "logged")
    rows = read_activity_rows(10)
    assert len(rows) == 2
    assert rows[0][1] == "draft PO"
    assert rows[1][1] == "approve PO"
