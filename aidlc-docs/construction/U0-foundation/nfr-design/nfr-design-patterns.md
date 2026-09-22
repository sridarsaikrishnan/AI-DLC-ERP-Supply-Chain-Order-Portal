# NFR Design Patterns — U0 Platform Foundation

Patterns incorporating the approved NFR requirements. All choices below use the recommended options (Q1–Q5 = A/B/A/A/A), proceeding on recommendation as the user deferred.

---

## P-1: Job Queue & Worker (DB-backed)
- **Pattern**: Transactional job table in PostgreSQL; workers claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT :batch`.
- **Polling (Q1=A)**: Short-interval poll (1–2s) with batch claim. Adequate for moderate volume; no external broker.
- **Concurrency safety**: `SKIP LOCKED` ensures the two app instances never claim the same job (NFR-U0-SCALE-2, NFR-U0-REL-2).
- **Claim lifecycle**: PENDING -> (claimed) IN_PROGRESS -> SUCCEEDED | FAILED.

## P-2: Retry & Backoff
- **Pattern (Q2=B)**: Exponential backoff with a cap. On failure, compute `next_visible_at = now + min(base * 2^attempt, cap)`; job becomes claimable again after that time.
- **Bounded (BR-3.2)**: Stop after `maxAttempts`; mark FAILED. No dead-letter table for MVP (resiliency baseline OFF), but FAILED jobs remain queryable.

## P-3: Idempotency (durable)
- **Pattern (Q5=A)**: Idempotency table with a UNIQUE constraint on `dedupe_key`. Before performing side effects, the handler attempts an insert of the dedupe key in the same transaction; a uniqueness violation means "already processed" -> skip side effect (BR-3.3).
- **Applies to**: ERP submissions and corrective actions (prevents duplicate ERP calls on retry).

## P-4: Tenant Isolation (repository-enforced)
- **Pattern (Q4=A)**: A `TenantScopedRepository` base that injects `tenant_id = :ctx.tenant_id` into every query/write for tenant-owned aggregates, and raises an authorization error if no SecurityContext/tenantId is present (fail-closed, BR-2.1/BR-2.2).
- **Cross-tenant**: single-record fetch whose row tenant_id != context -> treated as not found (BR-2.3, no existence leak).
- **Rationale over DB RLS**: application-level enforcement is simpler and DB-portable for the PoC; RLS noted as a future hardening option.

## P-5: Observability
- **Correlation id (Q3=A)**: Accept inbound `X-Correlation-Id` if present, else generate at API ingress; store on the request context and copy onto enqueued Jobs so async processing shares the trace.
- **Structured logging (NFR-U0-OBS-1/2)**: JSON logs including correlation id, tenant id (where safe), unit/module, and job id.
- **Metrics (NFR-U0-OBS-3)**: request count/latency; job counts by status; retry counts.
- **Health (NFR-U0-OBS-4)**: liveness/readiness endpoints per instance (readiness checks DB connectivity).

## P-6: Security Posture (documented deviations)
- Per Q7=A: no password hashing, ERP credentials may be inline, no explicit parameterized-query mandate. Recorded as accepted risks in nfr-requirements.md. SQLAlchemy default usage still parameterizes unless raw SQL is hand-built.

## Compliance Summary (enabled extensions)
- **Security baseline**: DISABLED (Extension config) — N/A, not enforced.
- **Resiliency baseline**: DISABLED — N/A, not enforced. (Retry/idempotency included as functional requirements, not baseline enforcement.)
- **Property-Based Testing (Partial)**: Applicable — routing/validation pure functions and canonical/mapping serialization round-trips are in scope; queue/DB patterns here are integration-tested rather than PBT. Compliant (scope respected).
