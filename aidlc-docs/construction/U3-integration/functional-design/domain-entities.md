# Domain Entities — U3 Integration

Technology-agnostic. U3 owns no new persisted tables (it uses U0's orders, status history, jobs, config). It defines runtime/behavioral entities.

## ErpAdapter (interface)
Common contract all ERP adapters implement:
- `submit(erp_payload, connection) -> AdapterResult` (erp_reference or error)
- `fetch_status(erp_reference, connection) -> native_status`
- `send_corrective_action(action, erp_reference, connection) -> AdapterResult`
- `check_connectivity(connection) -> bool`

Implementations (MVP, Q2=B): `ErpNextStubAdapter`, `OdooStubAdapter` (simulators). Real HTTP adapters are a later drop-in behind the same interface.

## AdapterResult
- `success: bool`
- `erp_reference: str | None`
- `native_status: str | None`
- `error: str | None`
- `terminal: bool` (True = permanent failure, do not retry; False = transient)

## ErpPayload
- Opaque per-ERP dict produced by the mapping engine from a canonical object.

## MappingApplication (behavior, Q1=A)
- Applies MappingDefinition to translate canonical <-> ERP:
  - `field_entries`: copy source_path -> target_path, applying value_map if present
  - `expressions`: for MVP treated as direct/renamed copies (no complex transform engine)

## StatusReconciliation (behavior)
- Maps a native ERP status string to a canonical LifecycleState via the FROM_ERP mapping's value_map; applies latest-wins to the order (U0 BR, via U2/U0).

## AdapterAction (enum)
- CANCEL, AMEND, RESUBMIT

## Relationships (text)
```
Job (U0) --triggers--> handler (U3) --uses--> RoutingEvaluation (U0), MappingApplication (U3), ErpAdapter (U3)
ErpAdapter --talks to--> external ERP (stub in MVP)
Adapter result --updates--> Order lifecycle (U0 tables)
```
