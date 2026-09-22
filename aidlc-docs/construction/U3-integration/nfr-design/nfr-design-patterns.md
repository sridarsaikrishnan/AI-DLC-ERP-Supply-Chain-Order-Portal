# NFR Design Patterns — U3 Integration

Inherits U0 patterns. U3-specific:

## P-U3-1: Adapter Plugin Pattern
- `ErpAdapter` interface + a registry mapping ErpType -> adapter implementation. Adding an ERP = register a new adapter. Realizes NFR-U3-EXT-1.

## P-U3-2: Transient vs Terminal Failure
- Adapters return `AdapterResult.terminal`; handlers raise on transient (U0 retry/backoff) and mark Failed on terminal (BR-U3-2).

## P-U3-3: Idempotent Handlers
- dedupe_key = order_id + action + version; U0 IdempotencyStore guarantees a single ERP side effect per key (BR-U3-6).

## P-U3-4: Mapping Application (deterministic)
- Pure translation functions -> partial PBT candidate (canonical->erp->canonical round-trip for field-entry maps).

## Compliance Summary
- Security: DISABLED — N/A (inline ERP creds accepted per Q7=A, flagged).
- Resiliency: DISABLED — N/A (retry/idempotency are functional, not baseline; no auto-failover per Q4=A).
- PBT (Partial): mapping round-trip in scope; adapters/handlers unit + integration tested.
