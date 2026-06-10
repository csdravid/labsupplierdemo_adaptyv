from __future__ import annotations

from supplier_agent.rules import check_items, lead_time_days, load_inventory, read_sku_overrides


def test_inventory_loads_14_skus():
    assert len(load_inventory()) == 14


def test_sku_overrides_from_policy():
    overrides = read_sku_overrides()
    assert overrides["A1435101"] == 2
    assert overrides["E2621S"] == 3


def test_override_applied_to_item():
    by_sku = {i.sku: i for i in load_inventory()}
    assert by_sku["A1435101"].reorder_qty == 2
    assert by_sku["E2621S"].reorder_qty == 3


def test_six_items_below_reorder_point():
    low = check_items()
    skus = {i.sku for i in low}
    assert skus == {
        "E2621S",
        "C2527H",
        "A1435101",
        "S1120-3810",
        "SLGP033RS",
        "78420",
    }


def test_critical_items_have_flags():
    by_sku = {i.sku: i for i in load_inventory()}
    assert by_sku["A1435101"].critical is True
    assert by_sku["A1435101"].on_hand == 0
    assert by_sku["E2621S"].next_run_date is not None
    assert by_sku["C2527H"].critical is False


def test_lead_time_lookup():
    assert lead_time_days("Starlab CH") == 2
    assert lead_time_days("Sigma-Aldrich") == 5
    assert lead_time_days("Unknown Supplier") == 5
