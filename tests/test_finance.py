from __future__ import annotations

from datetime import date

from supplier_agent.finance import (
    analyze_item,
    expedite_surcharge,
    finance_summary,
    record_approval,
)
from supplier_agent.rules import load_inventory


def test_expi293_run_blocked_and_expedite_risk():
    by_sku = {i.sku: i for i in load_inventory()}
    row = analyze_item(by_sku["A1435101"], today=date(2026, 6, 9))
    assert row.expedite_risk is True
    assert row.run_blocked is True
    assert row.days_until_stockout == 0
    assert row.savings_if_now_chf > 0


def test_healthy_plate_not_at_risk():
    by_sku = {i.sku: i for i in load_inventory()}
    row = analyze_item(by_sku["264573"], today=date(2026, 6, 9))
    assert row.expedite_risk is False
    assert row.run_blocked is False
    assert row.savings_if_now_chf == 0


def test_expedite_surcharge_max_flat_vs_percent():
    cfg = {"expedite_flat": 150.0, "expedite_percent": 40.0}
    small = expedite_surcharge(200, cfg)
    assert small == 150
    large = expedite_surcharge(5000, cfg)
    assert large == 2000


def test_finance_summary_has_roi_headline(monkeypatch):
    import supplier_agent.finance as fin

    monkeypatch.setattr(fin, "_draft_pending_for_sku", lambda sku: False)
    s = finance_summary(today=date(2026, 6, 9))
    assert s["expedite_exposure_chf"] > 0
    assert "CHF" in s["roi_headline"]
    assert s["run_blocked_count"] >= 1
    assert len(s["at_risk_skus"]) >= 2


def test_record_approval_appends_row(tmp_path, monkeypatch):
    import supplier_agent.finance as fin

    log = tmp_path / "spend_log.csv"
    monkeypatch.setattr(fin, "SPEND_LOG", log)
    item = load_inventory()[0]
    record_approval(item, "PO-TEST-001", expedite=False)
    text = log.read_text(encoding="utf-8")
    assert "PO-TEST-001" in text
    assert item.sku in text
