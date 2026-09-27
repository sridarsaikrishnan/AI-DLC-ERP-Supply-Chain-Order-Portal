from __future__ import annotations

from src.modules.integration.domain.status_mapping import CanonicalStatus, map_native_status


def test_odoo_status_mapping() -> None:
    assert map_native_status("ODOO", "sale") is CanonicalStatus.CONFIRMED
    assert map_native_status("ODOO", "done") is CanonicalStatus.FULFILLED
    assert map_native_status("ODOO", "cancel") is CanonicalStatus.CANCELLED
    assert map_native_status("ODOO", "sale", invoice_status="invoiced") is CanonicalStatus.CLOSED
    assert map_native_status("ODOO", "draft") is None


def test_erpnext_status_mapping() -> None:
    assert map_native_status("ERP_NEXT", "Completed") is CanonicalStatus.FULFILLED
    assert map_native_status("ERP_NEXT", "Cancelled") is CanonicalStatus.CANCELLED


def test_unknown_erp_or_status_is_none_never_raises() -> None:
    assert map_native_status("SAP", "whatever") is None
    assert map_native_status("ODOO", None) is None
    assert map_native_status("", "") is None
