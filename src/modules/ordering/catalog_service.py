"""CatalogService (LC-U2-2, Q1=B/Q2=B).

Serves catalog + inventory from a portal-side seed for the PoC. Live ERP fetch via
U3 is the documented target; this keeps the PoC deterministic and DB-light.
"""

from __future__ import annotations

# Seed catalog keyed by product_key (default/primary instance context, Q2=B).
_CATALOG = {
    "P1": {"product_key": "P1", "name": "Widget", "description": "Standard widget"},
    "P2": {"product_key": "P2", "name": "Gadget", "description": "Standard gadget"},
    "P3": {"product_key": "P3", "name": "Sprocket", "description": "Standard sprocket"},
}

_INVENTORY = {
    "P1": {"product_key": "P1", "available_quantity": 500, "unit_of_measure": "EA"},
    "P2": {"product_key": "P2", "available_quantity": 120, "unit_of_measure": "EA"},
    "P3": {"product_key": "P3", "available_quantity": 0, "unit_of_measure": "EA"},
}


class CatalogService:
    def browse(self, query: str | None = None) -> list[dict]:
        items = list(_CATALOG.values())
        if query:
            q = query.lower()
            items = [p for p in items if q in p["name"].lower()]
        return items

    def availability(self, product_key: str) -> dict | None:
        return _INVENTORY.get(product_key)
