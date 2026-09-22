# U0 Platform Foundation — Code Summary

## Generated Files (application code at workspace root)

### Config / infra
- `requirements.txt`, `Dockerfile`, `docker-compose.yml` (app x2 + postgres + nginx), `nginx.conf`, `pytest.ini`, `README.md`

### Shared cross-cutting (`src/shared/`)
- `logging.py` — structured JSON logging enriched with correlation id
- `correlation.py` — inbound-or-generated correlation id via context var (P-5)
- `errors.py` — PortalError hierarchy (Validation/Authorization/NotFound/Configuration)
- `metrics.py` — in-process counters for /metrics

### App (`src/app/`)
- `main.py` — FastAPI composition root; correlation middleware; `/livez`, `/readyz`, `/metrics`; starts the poller on startup

### Foundation module (`src/modules/foundation/`)
- `canonical/models.py` — CanonicalSalesOrder/OrderLine/OrderStatus/Product/Inventory, LifecycleState
- `canonical/validator.py` — BR-1 validation (pure functions, PBT scope)
- `config/models.py` — ErpInstance, RoutingRule/RoutingCondition, MappingDefinition/Entry/Expression
- `config/resolver.py` — `evaluate_routing` (ordered first-match-wins + no-match; pure, PBT scope)
- `context/security_context.py` — SecurityContext + propagation (fail-closed support)
- `persistence/database.py` — SQLAlchemy engine/session
- `persistence/tables.py` — ORM tables (jobs, idempotency, config, orders, status history)
- `persistence/tenant_repository.py` — TenantScopedRepository (auto filter + fail-closed, BR-2)
- `queue/models.py` — Job / JobType / JobStatus
- `queue/job_store.py` — JobStore (SKIP LOCKED claim, backoff) + IdempotencyStore (unique dedupe_key)
- `queue/worker.py` — HandlerRegistry + WorkerHost (idempotent, retry/backoff, context per job)
- `queue/poller.py` — background short-interval poller

### Migrations (`migrations/`)
- `001_foundation.sql` — all foundation tables

### Tests (`tests/foundation/`)
- `test_validator.py` — canonical validation cases
- `test_routing.py` — routing precedence / no-match / operators
- `test_property_based.py` — Hypothesis: validation invariant + JSON round-trip

## Design → Code Mapping
- LC-1 Persistence → persistence/*
- LC-2 Queue/Worker → queue/*
- LC-3 Security Context → context/*
- LC-4 Observability → shared/logging, correlation, metrics; app health endpoints
- LC-5 Canonical + Validator → canonical/*
- LC-6 Config Resolver → config/*

## Verification Status (honest)
- Code authored against the U0 design. **Tests were NOT executed in this environment**: the machine has no working Python runtime (only Windows Store alias stubs) and no Docker. 
- DB-free pure-logic tests (validator, routing, property-based) are ready to run with `pytest` once Python 3.11+ is available.
- Repository/queue tests requiring PostgreSQL are deferred to the Build & Test phase.

## Accepted Risks (Q7=A)
- Plaintext passwords (U1 later), inline ERP credentials allowed in `erp_instances.connection_ref`, no explicit parameterized-query mandate (SQLAlchemy parameterizes by default). Flagged blocking-before-production.
