"""U3 tests: mapping application, routing via service (pure), stub adapters. DB-free."""

from src.modules.foundation.config.models import (
    DataType,
    Direction,
    ErpType,
    MappingDefinition,
    MappingEntry,
)
from src.modules.integration.adapter import AdapterAction, AdapterRegistry
from src.modules.integration.adapters.erpnext_stub import ErpNextStubAdapter
from src.modules.integration.mapping_engine import apply_mapping


def test_mapping_field_entries_and_value_map():
    mapping = MappingDefinition(
        mapping_id="m1",
        instance_id="i1",
        data_type=DataType.SALES_ORDER,
        direction=Direction.TO_ERP,
        field_entries=[
            MappingEntry(source_path="client_reference", target_path="ref"),
            MappingEntry(source_path="currency", target_path="cur", value_map={"USD": "usd"}),
        ],
    )
    source = {"client_reference": "PO-1", "currency": "USD"}
    result = apply_mapping(source, mapping)
    assert result["ref"] == "PO-1"
    assert result["cur"] == "usd"  # value_map applied


def test_mapping_nested_target_path():
    mapping = MappingDefinition(
        mapping_id="m2", instance_id="i1", data_type=DataType.SALES_ORDER, direction=Direction.TO_ERP,
        field_entries=[MappingEntry(source_path="ship_to.city", target_path="address.city")],
    )
    result = apply_mapping({"ship_to": {"city": "Metro"}}, mapping)
    assert result["address"]["city"] == "Metro"


def test_adapter_registry_and_submit():
    reg = AdapterRegistry()
    reg.register(ErpType.ERP_NEXT, ErpNextStubAdapter())
    adapter = reg.get(ErpType.ERP_NEXT)
    res = adapter.submit({"ref": "PO-1"}, "conn")
    assert res.success and res.erp_reference.startswith("ERPNEXT-")


def test_stub_cancel_rejected_after_shipped():
    adapter = ErpNextStubAdapter()
    ref = adapter.submit({}, "conn").erp_reference
    # advance to Shipped
    for _ in range(3):
        adapter.fetch_status(ref, "conn")
    res = adapter.send_corrective_action(AdapterAction.CANCEL, ref, "conn")
    assert res.success is False and "shipped" in (res.error or "")
