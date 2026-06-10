from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Item:
    sku: str
    item: str
    supplier: str
    supplier_email: str
    catalog_no: str
    category: str
    on_hand: int
    reorder_point: int
    reorder_qty: int
    unit: str
    unit_cost_chf: float
    usage_per_week: float
    location: str
    storage: str
    critical: bool
    next_run_date: date | None
    last_ordered: str
    notes: str = ""

    @property
    def needs_reorder(self) -> bool:
        return self.on_hand <= self.reorder_point
