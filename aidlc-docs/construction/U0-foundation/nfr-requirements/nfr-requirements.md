# NFR Requirements — U0 Platform Foundation (baseline for whole monolith)

## Scalability
- **NFR-U0-SCALE-1**: Design for moderate volume — hundreds to low thousands of orders/day (Req NFR-1).
- **NFR-U0-SCALE-2**: Two application instances run concurrently (Q5=B). Shared state lives in PostgreSQL; the job poller must be safe under concurrent instances via `SELECT ... FOR UPDATE SKIP LOCKED`.
- **NFR-U0-SCALE-3**: The DB-backed queue is the first swap-out point if volume grows (documented future work).

## Performance
- **NFR-U0-PERF-1**: No hard performance targets for the PoC — best effort (Q4=C). Submission remains responsive by enqueuing work and processing ERP calls asynchronously.

## Availability
- **NFR-U0-AVAIL-1**: Basic redundancy via 2 app instances, no formal SLA (Q5=B). Brief downtime acceptable for MVP. Resiliency baseline OFF.

## Reliability
- **NFR-U0-REL-1**: Async jobs are at-least-once with bounded retry; handlers idempotent by dedupeKey (BR-3).
- **NFR-U0-REL-2**: Job poller must not double-process across the 2 instances (row-level locking).

## Observability (Q6=C)
- **NFR-U0-OBS-1**: Structured (JSON) logging across requests and jobs.
- **NFR-U0-OBS-2**: A correlation/trace id is generated per request and propagated onto enqueued jobs, so an order can be traced end-to-end (Req NFR-5).
- **NFR-U0-OBS-3**: Basic metrics (request counts/latency, job success/failure/retry counts).
- **NFR-U0-OBS-4**: Health/readiness endpoints for each app instance.

## Security Posture (Q7 clarification = A) — KNOWN RISK, DOCUMENTED
The user explicitly chose to skip minimal safeguards for the PoC. Recorded verbatim as decisions with associated risk:
- **NFR-U0-SEC-1 (accepted risk)**: Passwords are NOT hashed for MVP (stored as provided). **Risk**: plaintext credential exposure on any data access/breach. **Revisit**: mandatory in the deferred security-hardening phase before any real use.
- **NFR-U0-SEC-2 (accepted risk)**: ERP credentials MAY be stored inline in configuration/domain records for MVP (overrides the connectionRef-only intent from U0 functional design). **Risk**: secrets at rest in application tables. **Revisit**: move to a secrets manager / reference model during hardening.
- **NFR-U0-SEC-3 (accepted risk)**: No explicit parameterized-query mandate. **Risk**: SQL injection if string-built queries are used. **Mitigating note**: SQLAlchemy's normal usage parameterizes by default, so this risk is partially mitigated by the chosen ORM unless raw SQL is hand-built.
- **NFR-U0-SEC-4**: Full SECURITY baseline remains OFF for MVP (Extension config).

> ⚠️ These are intentional PoC tradeoffs approved by the user (Q7 clarification = A). They are flagged as blocking items to resolve before production and are logged in audit.md.

## Maintainability
- **NFR-U0-MAINT-1**: Folder-per-module layout with U0 as a shared module (from unit-of-work.md).
- **NFR-U0-MAINT-2**: Partial property-based testing (Hypothesis) for pure functions (routing/validation) and serialization round-trips (canonical/mapping) per the PBT=Partial extension setting.
- **NFR-U0-MAINT-3**: Repository pattern isolates persistence; queue behind an interface so it can be swapped later.
