from __future__ import annotations

from src.modules.integration.domain.status_mapping import CanonicalStatus, map_native_status


def test_odoo_status_mapping() -> None:
    assert map_native_status("ODOO", "sale") is CanonicalStatus.CONFIRMED
    assert map_native_status("ODOO", "done") is CanonicalStatus.FULFILLED
    assert map_native_status("ODOO", "cancel") is CanonicalStatus.CANCELLED
    assert map_native_status("ODOO", "sale", invoice_status="invoiced") is CanonicalStatus.CLOSED
    assert map_native_status("ODOO", "draft") is None


def test_unregistered_erp_type_is_none_never_raises() -> None:
    """ERP_NEXT and SAP are both currently unregistered (see STATUS_MAPPERS) — this is
    the behavior a new, not-yet-wired-up ERP type must have: safely ignored, not an
    error. Re-registering ERP_NEXT with its own mapper is the intended way to support it
    again; this test would then need ERP_NEXT's real expectations, like
    `test_odoo_status_mapping` has for Odoo."""
    assert map_native_status("ERP_NEXT", "Completed") is None
    assert map_native_status("SAP", "whatever") is None
    assert map_native_status("ODOO", None) is None
    assert map_native_status("", "") is None
