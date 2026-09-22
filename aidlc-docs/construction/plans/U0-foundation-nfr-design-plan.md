# NFR Design Plan — U0 Platform Foundation

## Context
Most NFR patterns for U0 are already determined by the NFR Requirements answers:
- DB-backed job queue with `SELECT ... FOR UPDATE SKIP LOCKED` (2-instance safe)
- At-least-once + bounded retry + idempotency by dedupeKey
- Row-level tenant isolation (auto filter + fail-closed)
- Structured logging + correlation id propagation + metrics + health endpoints
- Security safeguards intentionally skipped (Q7=A, documented risks)

This plan confirms the remaining design-level choices. Answer the `[Answer]:` tags (or "recommend").

## Execution Checklist (artifacts)
- [ ] `nfr-design-patterns.md` (patterns: queue/worker, idempotency, tenant filter, retry, observability)
- [ ] `logical-components.md` (logical components: job store, poller, worker host, repository layer, logging/metrics middleware)

---

## Questions

## Question 1
For the DB-backed job poller, what polling/claim approach?

A) Short-interval polling (e.g., every 1-2s) with `FOR UPDATE SKIP LOCKED` batch claim (simple, adequate for moderate volume) (recommended)

B) `LISTEN/NOTIFY` (Postgres) to wake workers immediately + fallback poll

C) Recommend

[Answer]: 

## Question 2
Retry backoff strategy for failed jobs (bounded retry already decided)?

A) Fixed delay between retries

B) Exponential backoff with a cap (recommended)

C) Immediate retry up to maxAttempts (simplest)

D) Recommend

[Answer]: 

## Question 3
Where should the correlation/trace id come from?

A) Generated at API ingress if absent; accepted from an inbound `X-Correlation-Id` header if present; propagated to jobs (recommended)

B) Always generated fresh at ingress (ignore inbound headers)

C) Recommend

[Answer]: 

## Question 4
How should tenant isolation be implemented technically in the repository layer?

A) A base repository that injects a `tenant_id = :ctx` predicate on every tenant-owned query, and raises if context is missing (fail-closed) (recommended)

B) Postgres Row-Level Security (RLS) policies enforced at the DB using a session variable

C) Recommend

[Answer]: 

## Question 5
Idempotency enforcement mechanism for handlers?

A) Unique constraint on `dedupeKey` in an idempotency/outbox table; handler checks-or-inserts before performing side effects (recommended)

B) In-memory/cache dedupe (not durable)

C) Recommend

[Answer]: 

---

Fill in the `[Answer]:` tags and let me know when done.
