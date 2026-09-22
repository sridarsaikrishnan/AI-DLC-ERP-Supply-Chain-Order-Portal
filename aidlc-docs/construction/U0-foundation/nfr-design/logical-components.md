# Logical Components — U0 Platform Foundation

Logical (technology-mapped but not yet deployed) components realizing the NFR patterns. These live in the `foundation` module and are consumed by U1–U4.

---

## LC-1: Persistence Layer
- **JobStore** — table + repository for the async Job model; claim query with `FOR UPDATE SKIP LOCKED`.
- **TenantScopedRepository (base)** — enforces tenant predicate + fail-closed (P-4).
- **Config repositories** — ErpInstanceRepository, RoutingRuleRepository, MappingRepository (platform config; not tenant-scoped).
- **Domain repositories** — OrderRepository, StatusHistoryRepository (tenant-scoped).
- **IdempotencyStore** — table with UNIQUE(dedupe_key) for P-3.
- Backed by PostgreSQL (JSONB used for mapping DSL entries/expressions and flexible config).

## LC-2: Queue & Worker Host
- **Enqueuer** — implements Process 3 (enqueue): persists Job (PENDING), sets attempt/max, dedupe_key.
- **Poller** — short-interval loop (P-1) claiming batches.
- **WorkerHost** — implements Process 4 (consume): reconstructs SecurityContext from job.tenantId, invokes registered handler, applies retry/backoff (P-2), marks terminal status.
- **HandlerRegistry** — U3 registers handlers by job type (SUBMISSION, CORRECTIVE_ACTION, STATUS_SYNC).

## LC-3: Security Context Propagation
- **ContextProvider** — holds the current SecurityContext (per request and per job).
- **ContextMiddleware (API ingress)** — resolves context via U1 Identity; attaches to request scope.
- **JobContextBinder** — on consume, builds context from job.tenantId.

## LC-4: Observability Middleware
- **CorrelationMiddleware** — inbound `X-Correlation-Id` or generate; attach to context; copy onto Jobs (P-5).
- **StructuredLogger** — JSON logger enriched with correlation id, tenant id, module, job id.
- **MetricsCollector** — request and job metrics.
- **HealthEndpoints** — /livez, /readyz (readyz checks DB).

## LC-5: Canonical Model & Validation
- **Canonical schemas** (from functional design) as typed models.
- **Validator** — implements Process 1 (BR-1); pure functions -> in partial PBT scope.

## LC-6: Config Resolution
- **ConfigResolver** — implements Process 5: ordered routing rules, mapping definitions by (instance, dataType, direction), active instances.

---

## Mapping to Patterns
| Logical Component | Realizes |
|---|---|
| JobStore, Poller, WorkerHost | P-1 Queue/Worker |
| WorkerHost | P-2 Retry/Backoff |
| IdempotencyStore | P-3 Idempotency |
| TenantScopedRepository, ContextProvider | P-4 Tenant Isolation |
| CorrelationMiddleware, StructuredLogger, MetricsCollector, HealthEndpoints | P-5 Observability |
| Canonical Validator, ConfigResolver | Functional processes (PBT-partial candidates) |

## Module Placement (per unit-of-work.md folder-per-module)
```
src/modules/foundation/
├── persistence/      # LC-1 (repositories, JobStore, IdempotencyStore)
├── queue/            # LC-2 (enqueuer, poller, worker host, handler registry)
├── context/          # LC-3 (security context + propagation)
├── observability/    # LC-4 (correlation, logging, metrics, health)
├── canonical/        # LC-5 (schemas + validator)
└── config/           # LC-6 (config resolver + config models)
```
