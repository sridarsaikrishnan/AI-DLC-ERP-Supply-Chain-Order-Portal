# Construction — Phase 1 Code Generation Plan (Target Architecture)

**Goal:** the domain core, correctness-first, on plain PostgreSQL, runnable locally (floci +
Odoo container). No cloud coupling yet — AWS services sit behind ports with local adapters.
Full Order event-sourcing (the `eventsourcing` library), GraphQL, and managed services land
in Phase 2/3.

**Scope boundary:** Phase 1 builds tenancy + ownership routing + the event backbone (outbox +
domain events) + inbound webhook ingress. In Phase 1 the `Order` is a simple persisted
aggregate that **emits** domain events; it is **converted to the `eventsourcing` library in
Phase 2**. This ordering gets isolation/routing correctness locked before the ES machinery.

**Env note:** this sandbox has no package-install network and a broken venv, so steps are
authored + byte-compiled + logic-verified; `pip install`, Alembic run, and floci bring-up are
documented for a normal-network environment.

## Structure & tooling
- [ ] New layout: `src/platform/{canonical,domain,infrastructure,api,worker}`; domain depends only on canonical; infrastructure implements ports; api/worker are thin hosts.
- [ ] `import-linter` contract enforcing the dependency direction (domain never imports infrastructure/boto3).
- [ ] Dependencies added (pinned): `alembic`, `import-linter`. (Defer `strawberry-graphql`, `eventsourcing`, `boto3` to their phases.)

## Data model + migrations (Alembic)
- [ ] Alembic scaffolding (`alembic.ini`, `env.py`, `versions/`) — replaces raw `.sql` + ad-hoc `create_all`.
- [ ] Tables: `erp_connections(secret_ref)`, `tenant_connection_bindings(erp_customer_id,status)`, `items(owning_connection_id,sku)`, `orders(owning_connection_id,erp_order_id,lifecycle_state,tenant_id,client_reference,payload)`, `order_status_history`, `outbox`, `mapping_definitions`, `webhook_endpoints`, `audit_log`.
- [ ] Constraints: `UNIQUE(tenant_id,connection_id)`, `UNIQUE(connection_id,erp_customer_id)`, `UNIQUE(connection_id,erp_order_id)`.
- [ ] Postgres **row-level security** policies on reseller-readable tables (tenant defense-in-depth). (SEC-01/08)

## Ports
- [ ] `ErpAdapter`, `EventPublisher`, `SecretStore`, `Clock`, `IdGenerator` (ULID/UUIDv7).
- [ ] Local adapters: `InlineEventPublisher` (in-process, for tests/simple local) + `EventBridgePublisher` (floci/AWS); `EnvSecretStore` (local) + `SecretsManagerSecretStore` (floci/AWS).

## Domain (pure, tenant-aware)
- [ ] Canonical models (reuse/extend current `canonical/models.py`).
- [ ] Tenancy: connection registry; binding create + **verify** flow; item ownership + **conflict detection** (same SKU from two connections).
- [ ] **Ownership routing** (pure): resolve single `owning_connection_id` from order items; **reject mixed-ERP**; persist on order; never re-derive.
- [ ] **Reverse-routing resolver** (pure): `(connection_id, erp_order_id) -> order -> tenant`; binding-gated for customer/item.
- [ ] **Reseller vs operator DTOs** — reseller types carry no ERP identity (FR-19 by construction).

## Eventing backbone
- [ ] Event envelope (`eventId, eventType, occurredAt, tenantId, aggregateId, version, correlationId, payload`) + domain event types (OrderSubmitted, OrderValidated, OrderRejected, OrderReadyForDelivery, OrderSentToErp, ErpOrderStatusChanged, ...).
- [ ] Outbox writer (append in same tx as state change) + outbox **relay** (poller, `SKIP LOCKED`) publishing via `EventPublisher`.

## Inbound webhook ingress
- [ ] `POST /erp/webhook/{connectionId}`: HMAC auth (per-connection secret via `SecretStore`), attribute via reverse-routing keys, **dedupe** (delivery id / natural key), append integration event, return 200 fast. (SEC-05/13)
- [ ] Reconciliation sweeper skeleton (scheduled) using `ErpAdapter.fetch_status`.

## Integration adapter migration
- [ ] Move the working Odoo JSON-RPC adapter into the new `ErpAdapter` port location; keep the stub for tests; selection via env.

## Security (baseline — Phase-1 applicable)
- [ ] Input validation (pydantic) + body-size limits + parameterized SQL; generic errors + global error handler; structured logging with correlation id, secrets/PII scrubbed; fail-closed tenant scoping; object-level authz in services; no plaintext secrets (SecretStore). (SEC-03/05/08/09/12/15)

## Tests (PBT partial + example)
- [ ] PBT: ownership routing (mixed-ERP always rejected; single owner resolved), status mapping totality, reverse-routing attribution never crosses tenants.
- [ ] Example: binding verify; webhook attribution + dedupe + unattributable-drop; cross-tenant read -> NotFound; mixed-ERP reject; ownership conflict detection.

## Local run (floci)
- [ ] `docker-compose`: postgres + floci + odoo; app boots with `InlineEventPublisher`+`EnvSecretStore` (simplest) or floci-backed adapters; seed one connection + verified binding + items for a demo.

## Verification (where runtime allows)
- [ ] `alembic upgrade head`; run tests; local flow: place order -> ownership routing -> outbox event -> inbound webhook attributes status back. (ES/GraphQL arrive Phase 2.)

## Explicitly deferred
- Phase 2: convert `Order` to the `eventsourcing` library (replay/snapshots/upcasters), projectors + read models, GraphQL (Strawberry) reseller/operator schemas.
- Phase 3: Cognito, Secrets Manager/KMS, EventBridge + SQS FIFO + DLQ, CDK deploy to ECS Fargate, per-connection circuit breaker.
