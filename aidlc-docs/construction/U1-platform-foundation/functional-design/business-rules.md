# Business Rules — U1 Platform Foundation

Foundational rules enforced by U1 and inherited by every unit. IDs `BR-U1-xx`.

## Tenant isolation & access
- **BR-U1-01** Every request/message resolves an immutable `TenantContext` from a validated token claim; the tenant is never taken from parameters or body. (FR-01, AC-01, Q7=A)
- **BR-U1-02** Every tenant-scoped query applies the tenant filter; additionally, RLS policies on projection and reference/config tables enforce isolation at the DB for the app-query role. (Q2=X, SECURITY-11)
- **BR-U1-03** Axon event-store tables are accessed only by the framework/projector via a privileged role that bypasses RLS; they are never queried tenant-scoped. (Q2=X)
- **BR-U1-04** Two roles only: `RESELLER` (tenant-scoped) and `OPERATOR` (admin, not tenant-scoped, role-checked, audited). Deny-by-default. (Q3=A, SECURITY-08)
- **BR-U1-05** Object-level ownership is checked on every resource referenced by id (prevent IDOR). (SECURITY-08)

## No ERP identity (structural)
- **BR-U1-06** Reseller DTOs are a separate type set with no field for ERP name, instance, `connectionId`, `erpCustomerId`, or `erpOrderId`. Leakage is prevented by construction, not filtering. (FR-19, AC-02)
- **BR-U1-07** All errors map to a **closed/sealed** `CanonicalError` set; reseller-facing messages carry only a canonical code + safe text; raw ERP text/identity never reaches a reseller. The sealed type forces new error paths to pick an existing safe code. (Q5, FR-19)

## Identity, money, time
- **BR-U1-08** IDs are prefixed, time-sortable (UUIDv7/ULID): `ord_/po_/itm_/cust_/conn_/bind_/tnt_/whk_/aud_`. (Q1=A)
- **BR-U1-09** Money is `BigDecimal` + ISO-4217; amounts stored as received from the ERP; no FX conversion; half-up rounding only for display. Quantities are `BigDecimal` + unit of measure. (Q4=A)
- **BR-U1-10** All timestamps are UTC `Instant` (ISO-8601); currency ISO-4217; country ISO-3166 alpha-2. (Q8=A)

## Uniqueness & lifecycle
- **BR-U1-11** `UNIQUE(tenantId, connectionId)` and `UNIQUE(connectionId, erpCustomerId)` on bindings — a reseller has at most one customer per instance, and an ERP customer maps to at most one tenant. (AC-05)
- **BR-U1-12** `UNIQUE(connectionId, erpOrderId)` on the order/delivery projection — one owning order per ERP record (enables reverse routing). 
- **BR-U1-13** One owning connection per tenant-visible item (`sku`); duplicates flagged as a conflict and withheld from tenants until resolved. (AC-06)
- **BR-U1-14** Reference/config entities are soft-deleted/disabled (status flags), never hard-deleted, preserving audit/history. (Q7=A)
- **BR-U1-15** Reference/config aggregates use optimistic concurrency (`version`); the `Order` aggregate uses Axon's event sequence. (Q8=A)

## Event sourcing
- **BR-U1-16** The `Order` aggregate is event-sourced: commands append events; state is a fold over the stream; no direct row mutation. (ES)
- **BR-U1-17** Event schema changes are handled by upcasters; no snapshotting in the MVP (revisit with real event-volume data). (Q6)
- **BR-U1-18** Domain events are published for integration only via the transactional outbox (atomic with the event append); consumers are idempotent (dedup by `eventId`) and per-order ordered (`MessageGroupId = orderId`). (RESILIENCY-10, no dual-write)

## Audit & integrity
- **BR-U1-19** Every operator mutation is recorded append-only with actor, action, before/after, timestamp; application roles cannot delete/modify audit records. (FR-38, SECURITY-13/14)
- **BR-U1-20** ERP connection credentials are AES-GCM encrypted at rest with a key from Secrets Manager/KMS and a stored key id; never logged or returned in plaintext. (SECURITY-01/12, NFR-06)
