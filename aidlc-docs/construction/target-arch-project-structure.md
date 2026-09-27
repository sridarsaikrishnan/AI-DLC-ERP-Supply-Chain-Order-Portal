# Project Structure Blueprint — for review (Python, target architecture)

Goal: a codebase a new developer can navigate by names alone. One shared library, domain
modules in one folder, tests co-located per folder, explicit schema, strict types, clean
layering, and a local-setup guide. **No application code is written until this is approved.**

## 0. Guiding principles
- **Package root is `src/`** (import as `src.shared…`, `src.modules…`). Consolidates the current `src.modules`/`src.app`/`src.shared`/`src.platform` into one clean layout.
- **Three layers, one direction of dependency** (enforced by `import-linter`):
  `shared` ← `modules` (domain) ← `api` / `worker` (hosts). Domain never imports hosts or cloud SDKs.
- **Ports & adapters**: a module declares interfaces (`ports.py`); adapters implement them under `infrastructure/`. Swapping Postgres/EventBridge/ERP is an adapter change.
- **Event sourcing only where it earns it**: `ordering` (the Order aggregate) is event-sourced via the shared kernel; every other module is CRUD that emits domain events.
- **Naming tells you the layer**: `*_service.py` (application), `aggregate.py`/`events.py`/`commands.py` (domain), `*_repository.py`/`*_adapter.py` (infrastructure), `schema.py`/`resolvers.py` (GraphQL), `routes.py` (HTTP).
- **Types**: strict `mypy` on everything; `pydantic` at boundaries (GraphQL input, webhook payloads, config); frozen dataclasses in the pure domain; `py.typed` shipped.

## 1. Top-level layout
```
erp-platform/
  README.md                     # quickstart, points to docs/local-setup.md
  pyproject.toml                # single dep source + tool config (mypy, ruff, pytest, import-linter, coverage)
  docker-compose.yml            # postgres + floci + odoo + app (local stack)
  .env.example                  # every env var with safe local defaults
  alembic.ini
  migrations/                   # ← THE DATABASE SCHEMA (Alembic version history)
    versions/
  docs/
    local-setup.md              # ← LOCAL SETUP GUIDE (step-by-step for a new dev)
    conventions.md              # naming, layering, testing rules
    architecture.md             # links to aidlc-docs/.../target-architecture.md
    events-catalog.md           # every domain/integration/public event + payload
  src/                          # package root (import as src.*)
    shared/                     # ← THE SHARED LIBRARY (reusable, no domain logic)
    modules/                    # ← DOMAIN MODULES (one folder per bounded context)
    api/                        # ← DELIVERY: GraphQL + HTTP (inbound webhooks, health)
    worker/                     # ← ASYNC: consumers, schedulers, outbox relay
  tests/
    e2e/                        # cross-module end-to-end (order → routing → webhook → read)
    load/                       # optional perf smoke
```
(Per-module and per-shared-package unit tests are **co-located**, see §6.)

## 2. The shared library — `src/shared/`
Reusable building blocks only. No business rules here.
```
shared/
  eventsourcing/        # the ES kernel: DomainEvent, Aggregate, EventStore(Port)+InMemory,
                        #   EventSourcedRepository, Outbox, EventPublisher, serialization, snapshots, errors
  messaging/            # event envelope, EventPublisher port + adapters (inline, eventbridge)
  persistence/          # db engine/session, UnitOfWork, Base, RLS helpers, tenant-scoped repo base
  identity/             # SecurityContext, tenant/correlation context, auth guards, JwtVerifier port
  secrets/              # SecretStore port + adapters (env, secrets_manager)
  config/               # pydantic-settings Settings (typed env)
  observability/        # structured logging, correlation ids, metrics, tracing hooks
  types/                # value objects: Id/ULID helpers, Money, common aliases, Result
  errors/              # shared error taxonomy + mapping to HTTP/GraphQL
  testing/              # shared test utils: in-memory adapters, builders, fixtures
```

## 3. Domain modules — `src/modules/` (one folder each)
```
modules/
  tenancy/              # resellers/tenants; TenantConnectionBinding (create + verify); uniqueness
  connections/          # ERP connection registry (base_url/db/user + secret_ref)
  catalog/              # items + ownership (owning_connection_id) + conflict detection
  ordering/             # Order aggregate — EVENT SOURCED (commands, events, projections)
  integration/          # ErpAdapter port + Odoo/ERPNext adapters, DeclarativeMappingEngine, delivery
  webhooks_inbound/     # ← ERP → platform ingestion (verify, attribute, dedupe)
  webhooks_outbound/    # ← platform → reseller signed webhooks + delivery log (optional/secondary)
  audit/                # audit trail (who/what/when, before/after)
```

### 3a. Anatomy of a module (template — same shape everywhere)
```
modules/ordering/
  README.md             # what this context owns, its events, invariants, edge cases
  domain/               # pure, no I/O
    aggregate.py        # Order(Aggregate) — behavior + invariants
    events.py           # OrderSubmitted, OrderValidated, OrderRejected, ... (@register_event)
    commands.py         # CreateSalesOrder, CancelSalesOrder, AmendSalesOrder (typed)
    value_objects.py    # OrderLine, Quantity, etc. (frozen)
    policies.py         # pure rules (ownership routing, mixed-ERP rejection)
    errors.py
  application/          # orchestration; depends on ports, not adapters
    order_service.py    # command handlers: load aggregate, decide, save, emit
    handlers.py         # integration-event handlers this module consumes from the bus
    ports.py            # interfaces this module needs (OrderRepository, EventPublisher, Clock...)
  projections/          # read models (CQRS) that GraphQL serves
    order_summary.py    order_detail.py  order_timeline.py  projector.py
  infrastructure/       # adapters implementing this module's ports
    order_repository.py # EventSourcedRepository[Order] bound to the store
    projection_store.py
  tests/                # ← CO-LOCATED TESTS for this module
    domain/  application/  projections/  infrastructure/
  # NOTE: no GraphQL here — the GraphQL surface is CENTRALIZED in api/graphql/ (see §4).
  #       api resolvers call this module's application services + read projections.
```
CRUD modules (tenancy, connections, catalog) drop `domain/aggregate.py` event-sourcing and use a
simple typed entity + repository, but keep the same folder shape so every module reads the same.

## 4. Delivery — `src/erp_portal/api/`  (where the outside world reaches in)
```
api/
  app.py                # FastAPI composition root: mounts GraphQL + HTTP routers, middleware
  graphql/              # ← CENTRALIZED GraphQL (all types/resolvers live here, not in modules)
    reseller/           # ← PUBLIC RESELLER GRAPHQL API (no ERP identity by construction)
      types.py          # reseller-safe GraphQL types
      resolvers.py      # query/mutation resolvers -> module application services + projections
      context.py        # builds tenant/roles context from Cognito JWT
      schema.py         # assembles the reseller schema
      server.py         # Strawberry router + depth/complexity limits, introspection off in prod
    operator/           # ← OPERATOR GRAPHQL API (full types)
      types.py  resolvers.py  context.py  schema.py  server.py
    _shared/            # shared scalars, enums, error mapping, dataloaders (N+1)
  http/
    webhooks.py         # ← INBOUND ERP WEBHOOK ROUTES: POST /erp/webhook/{connectionId}
                        #    (delegates to modules/webhooks_inbound)
    health.py           # /livez, /readyz, /metrics
  middleware/           # correlation id, security headers, error handler, rate limit
  tests/                # api-level tests (schema shape, authz, header/CORS, webhook auth)
```

## 5. Async — `src/erp_portal/worker/`
```
worker/
  main.py               # worker entrypoint (APP_ROLE=worker)
  consumers/            # SQS FIFO consumers
    order_processing.py # OrderSubmitted -> validate + ownership routing
    order_delivery.py   # OrderReadyForDelivery -> ErpAdapter.submit
    projector.py        # events -> read models
    webhook_dispatch.py # optional outbound reseller webhooks
  schedulers/
    reconciliation.py   # fallback poll per connection (missed inbound webhooks)
  relay/
    outbox_relay.py     # outbox -> EventBridge (the publish port)
  tests/
```

## 6. Tests — "proper tests in each folder"
- **Co-located unit tests** live in each module's / shared package's `tests/` mirroring its subfolders (`domain/`, `application/`, ...). A folder and its tests travel together.
- **Layered strategy**: domain (pure, incl. **property-based** with Hypothesis) → application (with in-memory adapters from `shared/testing`) → infrastructure (integration, real Postgres via container) → `tests/e2e/` (full flow).
- **Coverage gate + PBT** for pure functions (ownership routing, status mapping, reverse-routing attribution). Config in `pyproject.toml`.

## 7. Schema (explicit, in three places)
- **Database**: `migrations/versions/*` (Alembic) — tables, the three UNIQUE constraints, and RLS policies. This is the authoritative DB schema history.
- **GraphQL**: code-first Strawberry types **centralized** under `api/graphql/{reseller,operator}/` (`types.py` + `resolvers.py` + `schema.py`); resolvers call module application services + read projections. SDL exported to `docs/` for review. Reseller schema types **cannot express ERP identity** (FR-19 by construction).
- **Events**: the registered event classes in each module's `domain/events.py` (+ `docs/events-catalog.md`), versioned for upcasting.

## 8. "Where do I find…?" quick map (for a new dev)
| I want… | Look in |
|---|---|
| Inbound ERP webhooks (collect data) | `api/http/webhooks.py` → `modules/webhooks_inbound/` |
| Outbound reseller webhooks | `modules/webhooks_outbound/` (dispatched by `worker/consumers/webhook_dispatch.py`) |
| Public reseller GraphQL API | `api/graphql/reseller/` |
| Operator GraphQL API | `api/graphql/operator/` |
| The shared/reusable library | `src/erp_portal/shared/` |
| Event-sourcing kernel | `src/erp_portal/shared/eventsourcing/` |
| Order business logic | `modules/ordering/domain/` |
| Routing (which ERP an order goes to) | `modules/ordering/domain/policies.py` |
| ERP connectors (Odoo/ERPNext) | `modules/integration/infrastructure/` |
| DB schema / migrations | `migrations/versions/` |
| Read models (what GraphQL serves) | each module's `projections/` |
| Async consumers / relay / scheduler | `src/erp_portal/worker/` |
| Config / env vars | `shared/config/` + `.env.example` |
| How to run locally | `docs/local-setup.md` |
| Tests for module X | `modules/X/tests/` |

## 9. Tooling (`pyproject.toml`)
`mypy` (strict on `erp_portal`), `ruff` (lint+format), `pytest` + `pytest-cov` + `hypothesis`,
`import-linter` (layer contracts), `alembic`, `pydantic-settings`. Pinned versions + lock file (SEC-10).

## 10. Local setup guide (`docs/local-setup.md`) — outline to be filled
1. Prereqs (Python 3.11, Docker). 2. `docker compose up` (postgres + floci + odoo + app). 3. `alembic upgrade head`. 4. Seed a demo connection + verified binding + items. 5. Open reseller GraphQL / operator GraphQL / health. 6. Configure Odoo Automation Rule → inbound webhook. 7. Run tests (`pytest`, `mypy`, `ruff`, `lint-imports`).

## 11. Migration note
Existing `src/modules`, `src/app`, `src/shared` consolidate into the `src/{shared,modules,api,worker}`
layout. The working Odoo adapter moves to `modules/integration/infrastructure/`; the started kernel
relocates `src/platform/eventsourcing/` → `src/shared/eventsourcing/` (kept, per Q-D).

## Resolved (approved) structure decisions
- **Q-A → `src` root** (no `erp_portal` package). Import as `src.shared.*`, `src.modules.*`.
- **Q-B → co-located tests per module** (each module owns its `tests/`), plus `tests/e2e/`.
- **Q-C → centralized GraphQL** under `api/graphql/{reseller,operator}/`; modules expose application services + projections only (no GraphQL in modules).
- **Q-D → keep the kernel**, relocated to `src/shared/eventsourcing/`.
