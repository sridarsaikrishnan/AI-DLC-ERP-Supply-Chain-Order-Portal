# Tech Stack Decisions — U0 Platform Foundation (applies to whole monolith)

U0 is the shared foundation, so these choices apply across all units.

| Concern | Decision | Rationale | Source |
|---|---|---|---|
| Language / runtime | **Python** | Strong for the data mapping/transform and DSL evaluation at the heart of this system; readable; fast to build. | Q1=B |
| Web framework | **FastAPI** (recommended within Python) | Async-friendly (fits the async pipeline), typed request/response models, OpenAPI out of the box. Confirmable, but chosen as the standard modern Python API framework. | Derived from Q1 |
| Datastore | **PostgreSQL** | Relational fit for tenant-scoped orders/status/config; JSONB stores the flexible mapping DSL and config docs without a second datastore. | Q2=recommend → Postgres |
| ORM / DB access | **SQLAlchemy** (recommended) | Mature Python ORM; supports the repository pattern from U0. | Derived |
| Async queue | **DB-backed job table + poller** | Fewest moving parts for the PoC; no separate broker; directly supports at-least-once + bounded retry + idempotency (BR-3). Uses `SELECT ... FOR UPDATE SKIP LOCKED` so the two app instances (Q5=B) don't double-process. | Q3=recommend → C |
| App instances | **2 instances**, no formal SLA | Basic redundancy without resiliency baseline. | Q5=B |
| Observability | **Structured logging + metrics + health endpoints** | Trace orders end-to-end (NFR-5); health endpoints for the 2 instances. | Q6=C |
| Security posture | **No minimal safeguards (Q7=A)** — see NFR-SEC below | User's explicit PoC decision. Documented as known risk. | Q7 clarification=A |
| Testing | **pytest** + **Hypothesis** (property-based, partial scope) | PBT partial applies to pure functions (routing/validation) and serialization round-trips (canonical/mapping). | Extension config (PBT=Partial) |

## Notes
- Framework/ORM picks (FastAPI, SQLAlchemy) are the recommended Python defaults; if you have a different preference, flag it and I'll adjust in Infrastructure Design / Code Generation.
- The DB-backed queue keeps the PoC to a single infrastructure dependency (PostgreSQL). If volume grows beyond the moderate target, this is the first thing to swap for a real broker (documented as future work).
