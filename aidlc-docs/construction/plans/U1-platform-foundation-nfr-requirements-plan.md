# NFR Requirements Plan — U1 Platform Foundation

**Unit**: U1 Platform Foundation. NFRs and the global tech stack are already decided in `requirements.md` (NFR-01..13, Section 5, SECURITY/RESILIENCY/PBT). This plan sets **U1-specific targets** and confirms the inherited decisions.

**How to use**: answer the `[Answer]:` tags in Section A. Recommended options marked.

---

## Section A — Questions

## Question 1 — Command latency (synchronous ack)
Target for a command's synchronous response (e.g., create order returns id+status), given Q18=B (hundreds–low-thousands/day)?

A) p95 < 300 ms, p99 < 800 ms (recommended)

B) p95 < 150 ms (tighter)

C) No explicit target for MVP

X) Other

[Answer]: A - a JVM/Axon/Postgres round trip (aggregate load with no snapshot, event append, response) makes B's p95<150ms tight without real traffic data to justify it; A leaves room to tighten once measured.

## Question 2 — Read-model (projection) lag — eventual consistency bound (NFR-13)
How fresh must CQRS projections be after an event is stored?

A) p95 < 1 s, p99 < 3 s under normal load; alarm if sustained lag > 30 s (recommended)

B) Near-real-time (< 200 ms) required

C) No explicit target for MVP

X) Other

[Answer]: A - the client's own read-your-writes need is already met by the command response carrying the resulting state (NFR-13); nothing in the ten designed screens depends on sub-second projection freshness, and ERP delivery itself is far slower than 1s anyway, so B's <200ms would be effort spent on a gap nobody experiences.

## Question 3 — U1 tech-stack confirmations
Confirm the U1 library choices (all consistent with Section 5):
- Axon Framework (open source) with PostgreSQL JPA/JDBC event store (no Axon Server)
- Spring Data JPA + Hibernate for reference/config + projections; Flyway migrations
- Spring Security OAuth2 Resource Server for JWT validation (Cognito JWKS)
- ULID/UUIDv7 library for prefixed IDs
- jqwik + JUnit 5 + Testcontainers; AssertJ
- MapStruct (or hand-written mappers) for canonical↔DTO mapping

A) Accept all (recommended)

B) Accept with exceptions (describe)

X) Other

[Answer]: A - one clarification for code generation: MapStruct (or hand-written mappers) is for internal object mapping (entity to DTO to GraphQL type), never for the ERP canonical<->native mapping, which stays the declarative field-map config executed by the MappingEngine (application-design Q2=B). Keep those two kinds of 'mapping' distinct so this list is never read as replacing the MappingEngine.

## Question 4 — Availability & scale for U1
Confirm inherited targets apply to U1: single-region multi-AZ (RESILIENCY-08), RDS Multi-AZ, internal availability ~99.5% (RESILIENCY-02), moderate scale (Q18=B). Event store and projections sized for moderate volume; scale/snapshot tuning deferred to Infra Design.

A) Confirm inherited targets (recommended)

X) Other / different for U1

[Answer]: A

## Question 5 — Maintainability / quality gates for U1
Baseline quality gates for the foundation?

A) Coverage threshold on domain modules, PBT in CI with logged seed, static analysis (e.g., SpotBugs + Checkstyle/Spotless), dependency vulnerability scan (SECURITY-10), ArchUnit tests enforcing module dependency direction (recommended)

B) Lighter (build + tests only for MVP)

X) Other

[Answer]: A - note that the vulnerability scan and PBT-in-CI-with-a-logged-seed pieces of this aren't really optional against B: SECURITY-10 and PBT-08 already require them as blocking rules regardless of which option is picked here. ArchUnit enforcing module dependency direction is the right proportionate addition given the just-decided modular layout (Q6=C in application design): it mechanically stops the domain modules from picking up a Spring/JPA dependency and decaying into a big ball of mud, which matters more here than on a single-team project with no architectural boundaries to protect.

## Question 6 — Observability specifics for U1
Confirm OpenTelemetry with correlation id propagated across command→event→projection→integration, plus metrics for event-store append rate, projection lag, and outbox backlog.

A) Confirm (recommended)

X) Other

[Answer]: A - this is also what makes Q2's alarm and the earlier snapshot-deferral decision (functional design plan Q6) actionable rather than aspirational: you cannot alarm on projection lag without emitting it, and event-store append rate / per-aggregate event count is exactly the metric that would tell you it's time to revisit snapshotting later, with real data instead of a guess.

---

## Section B — Generation checklist (after approval)
- [x] `nfr-requirements.md` — NFR-U1-P1/P2, A1/A2, R1/R2, S1-S4, M1-M3, O1/O2, T1
- [x] `tech-stack-decisions.md` — U1 libraries + the MapStruct-vs-MappingEngine clarification; PBT-09 (jqwik) confirmed
