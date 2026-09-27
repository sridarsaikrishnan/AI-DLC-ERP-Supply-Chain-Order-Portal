# Requirements Delta — Target Architecture (Increment 3)

Supersedes/extends `requirements.md` for the "solid base" pivot. Style: AWS-native,
Python, event-driven, event-sourced (Order only), GraphQL API, single PostgreSQL,
binding/ownership tenancy. Managed AWS services sit behind ports so the domain stays
portable.

## Locked decisions
| # | Decision | Choice |
|---|---|---|
| D1 | API surface | **GraphQL** — separate reseller and operator schemas |
| D2 | Event→bus relay | **Transactional outbox poller** behind a `EventPublisher` port (CDC deferred) |
| D3 | Order routing | **Ownership-based** (item → owning connection); mixed-ERP rejected; decision persisted |
| D4 | Event sourcing scope | **`Order` aggregate only**; all other aggregates are CRUD + emitted domain events |
| D5 | Data store | **Single PostgreSQL** (Aurora Serverless v2): event store + outbox + projections + config |
| D6 | Compute | **ECS Fargate** for `api` + `worker`; **Lambda** only for outbox relay + scheduler tick |
| D7 | Portability | AWS-native services **behind ports/adapters**; no domain code imports an AWS SDK |

## Changed requirements (supersede prior answers)
- **FR-ROUTE (supersedes B1=B "route by order content").** An order routes to exactly one ERP connection derived from the ownership of its line items. Orders whose items span multiple connections are **rejected** (reseller-safe message). The resolved `owningConnectionId` is persisted on the order at validation time and is **never re-derived** thereafter.
- **NFR-DATA (supersedes multi-store).** Exactly one relational database holds the event store, outbox, read projections, and configuration/tenancy tables. No second database engine.

## Added requirements
### Tenancy & isolation
- **FR-BIND.** Operators create and verify a `TenantConnectionBinding` linking a reseller (`tenantId`) to an ERP connection (`connectionId`) with that reseller's `erpCustomerId`. States: `TO_VERIFY` → `VERIFIED`.
- **FR-UNIQ.** Enforce `UNIQUE(tenantId, connectionId)`, `UNIQUE(connectionId, erpCustomerId)`, `UNIQUE(connectionId, erpOrderId)` at the database.
- **FR-REV.** Inbound ERP data is attributed to exactly one tenant before any publication: orders via `(connectionId, erpOrderId)`, customers/items via a `VERIFIED` binding. Unattributable records are ignored, never broadcast.
- **FR-OWN.** Items are owned by exactly one connection; visible to a reseller only via a binding. Same SKU from two connections raises an ownership conflict for operator resolution.
- **FR-19 (reaffirmed, now structural).** ERP identity (`connectionId`, instance label, `erpCustomerId`, `erpOrderId`) never appears in the **reseller GraphQL schema**, webhooks, or delivery log. Guaranteed by schema separation, not by filtering.

### API (GraphQL)
- **FR-GQL-1.** Two GraphQL schemas/endpoints: `reseller` (reseller-safe types only) and `operator` (full operator types). Each authenticated via Cognito JWT; tenant/roles resolved into the GraphQL context.
- **FR-GQL-2.** Writes are **mutations mapped to commands** (`createSalesOrder`, `cancelSalesOrder`, `amendSalesOrder`, `registerWebhookEndpoint`, `onboardReseller`, `createCustomerBinding`, …). Reads are **queries over projections**.
- **FR-GQL-3 (optional).** `orderStatusChanged` subscription for live updates; webhooks remain the durable integration channel.

### Eventing & integration
- **FR-EVT.** Every state change is a domain event with the envelope: `eventId`, `eventType`, `occurredAt`, `tenantId`, `aggregateId`, `version`, `correlationId`, `payload`.
- **FR-QUEUE.** Domain events publish to EventBridge → SQS **FIFO** per consumer with `MessageGroupId = aggregateId`; exhausted messages go to a **DLQ** for operator triage.
- **FR-INGEST (primary ERP→platform).** The platform exposes a per-connection inbound webhook (`POST /erp/webhook/{connectionId}`) that ERPs call on status/item/customer changes. It authenticates (per-connection HMAC/secret), attributes to a tenant via reverse-routing keys before any publication, dedupes (at-least-once, unordered), appends an integration event, and returns `200` fast. Unattributable payloads are dropped.
- **FR-RECONCILE.** A scheduled reconciliation sweeper polls each connection since a cursor as a fallback for missed/dropped webhooks; it is the safety net, not the primary path.
- **FR-WEBHOOK-OUT (optional, secondary).** Reseller *outbound* webhooks (us → reseller) are signed (HMAC; secret shown once, stored hashed), retried with backoff, logged per attempt, and dead-lettered. Secondary to GraphQL retrieval.
- **FR-READ (client retrieval).** Clients retrieve data primarily via **GraphQL** queries (optionally subscriptions); outbound webhooks are a convenience push, not the system of record for reads.

## Non-functional
- **NFR-ES.** `Order` is event-sourced using the **`eventsourcing` (pyeventsourcing) library** on PostgreSQL — event stream is the source of truth; state rebuilt by replay with periodic snapshots; schema evolution via the library's upcasters. Hand-rolling the event store is out of scope (build-vs-buy = buy). Only the `Order` aggregate is event-sourced; other aggregates are CRUD emitting domain events.
- **NFR-CQRS.** Reads are served from projections (`order_summary`, `order_detail`, `order_timeline`, `delivery_view`); eventual consistency is acceptable and surfaced in UX.
- **NFR-CONSISTENCY.** Event append + outbox insert occur in one DB transaction (no dual-write). Optimistic concurrency via `UNIQUE(aggregate_id, version)`. Consumers are idempotent on `eventId`; delivery is at-least-once.
- **NFR-GQL-SEC.** GraphQL enforces query **depth and complexity limits**, disables introspection in production, uses **persisted queries** where cacheable, tenant-scopes every resolver, and applies field-level authorization. The reseller schema cannot express ERP-identity fields.
- **NFR-RESILIENCE.** External ERP calls have timeouts, retry/backoff via SQS + DLQ, and a **per-connection circuit breaker**; degraded ERPs cannot exhaust shared workers (bulkhead).
- **NFR-SEC (required — Security baseline enabled).** The Security extension is **ON** for this target. ERP credentials and webhook signing keys live in Secrets Manager/KMS (stored as `secret_ref`, never plaintext); auth via Cognito JWKS; encryption at rest+transit; least-privilege IAM; object-level authorization (IDOR prevention); rate limiting; append-only audit. Full rule mapping in `application-design/target-architecture.md` §11. Security gaps are blocking findings during Construction.

## Resolved decisions
- **O-SEC → YES.** Security baseline enabled (was: recommended). Supersedes the prior PoC posture (plaintext creds / security off).
- **O-GQL-SUB → NO (base).** GraphQL queries are the client read path; subscriptions deferred.
- **O-MANAGED-GQL → Strawberry-in-Python** behind API Gateway/ALB (portable). AppSync rejected.
- **O-INGEST → confirmed.** Inbound webhooks primary; reconciliation sweeper default every 15 min/connection; onboarding includes ERP webhook setup (Odoo Automation Rule; ERPNext native).
