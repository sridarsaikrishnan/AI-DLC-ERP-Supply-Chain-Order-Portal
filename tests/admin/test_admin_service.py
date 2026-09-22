"""U4 tests: mapping completeness (pure), DTO validation. DB-free."""

from src.modules.foundation.config.models import DataType
from src.modules.admin.service import AdminService


def test_unmapped_required_reports_missing_fields():
    # SALES_ORDER requires client_reference, currency, line_items
    entries = [{"source_path": "client_reference", "target_path": "ref"}]
    unmapped = AdminService._unmapped_required(DataType.SALES_ORDER, entries)
    assert "currency" in unmapped
    assert "line_items" in unmapped
    assert "client_reference" not in unmapped


def test_unmapped_required_all_mapped():
    entries = [
        {"source_path": "client_reference", "target_path": "ref"},
        {"source_path": "currency", "target_path": "cur"},
        {"source_path": "line_items", "target_path": "lines"},
    ]
    assert AdminService._unmapped_required(DataType.SALES_ORDER, entries) == []
