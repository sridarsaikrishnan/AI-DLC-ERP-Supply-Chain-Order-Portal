# NFR Requirements — U1 Platform Foundation

U1-specific non-functional targets, tied to the global NFRs (`requirements.md` NFR-01..13) and the enabled extensions. Answers: Q1=A, Q2=A, Q3=A, Q4=A, Q5=A, Q6=A.

## Performance
- **NFR-U1-P1** Command synchronous ack latency (e.g., create order returns id + status): **p95 < 300 ms, p99 < 800 ms** at moderate load (Q18=B). Rationale: a JVM/Axon/Postgres round trip (aggregate load without snapshot, event append, response) makes a tighter target unjustified without traffic data; tighten once measured. (Q1=A, FR-07)
- **NFR-U1-P2** Read-model projection lag (event stored → projection updated): **p95 < 1 s, p99 < 3 s** under normal load. Read-your-writes for the submitter is satisfied by the command response echoing resulting state + version (NFR-13), so sub-second projection freshness is not required. (Q2=A)

## Availability & scale
- **NFR-U1-A1** Single-region, multi-AZ; RDS Multi-AZ; internal availability target ~99.5% (RESILIENCY-02/08). (Q4=A)
- **NFR-U1-A2** Event store and projections sized for moderate volume (hundreds–low-thousands of orders/day). Scale and snapshot tuning deferred to Infrastructure Design, driven by real event-volume metrics. (Q4=A, ties to snapshot-deferral decision)

## Reliability
- **NFR-U1-R1** Transactional outbox guarantees no dual-write; integration consumers are idempotent (dedup by `eventId`), per-order ordered (`MessageGroupId = orderId`). (RESILIENCY-10, BR-U1-18)
- **NFR-U1-R2** Optimistic concurrency on reference/config aggregates; Axon sequence for the `Order` aggregate. (BR-U1-15)

## Security
- **NFR-U1-S1** JWT validation (JWKS/issuer/audience/expiry) on every request; immutable `TenantContext`; deny-by-default; object-level checks. (SECURITY-08)
- **NFR-U1-S2** Tenant isolation defense-in-depth: application filter + PostgreSQL RLS on projection/reference tables (app-query role); Axon event-store tables via privileged role bypassing RLS. (SECURITY-11, BR-U1-02/03)
- **NFR-U1-S3** ERP credentials AES-GCM encrypted (key from Secrets Manager/KMS); no secrets/PII/ERP-identity in logs. (SECURITY-01/03/12)
- **NFR-U1-S4** Sealed canonical error set; reseller messages never carry raw ERP text/identity. (FR-19, BR-U1-07)

## Maintainability / quality gates
- **NFR-U1-M1** PBT (jqwik) in CI with logged seed (PBT-08) — **blocking regardless**; dependency vulnerability scan + committed lock files + pinned images (SECURITY-10) — **blocking regardless**.
- **NFR-U1-M2** Coverage threshold on domain modules; static analysis (SpotBugs + Checkstyle/Spotless).
- **NFR-U1-M3** **ArchUnit** tests enforce module dependency direction (domain modules must not depend on Spring/JPA/infrastructure; nothing depends on `app/*`) — protects the Q6=C modular layout from decay. (Q5=A)

## Observability
- **NFR-U1-O1** OpenTelemetry with a correlation id propagated across command → event → projection → integration. (NFR-07)
- **NFR-U1-O2** Metrics: event-store append rate, **per-aggregate event count**, **projection lag**, outbox backlog. Projection-lag metric powers the NFR-U1-P2 alarm; append-rate/event-count is the signal to revisit snapshotting later with real data. (Q6=A)

## Property-based testing
- **NFR-U1-T1** Framework jqwik + JUnit 5 (PBT-09); properties per `functional-design/testable-properties.md` (P-U1-01..13), shrinking on, seed logged, in CI. Example-based tests pin business-critical paths (PBT-10).
