# NFR Design Plan — U1 Platform Foundation

**Unit**: U1 Platform Foundation. Turns U1 NFR requirements into concrete **patterns** and **logical components**. Answer the `[Answer]:` tags; recommended options marked.

---

## Section A — Questions

## Question 1 — Domain-event → integration relay pattern
How do committed `Order` events reach SNS/SQS (the event-driven boundary)?

A) **Axon tracking event processor** publishes to SNS; Axon's event store + tracking token IS the durable log (replayable, at-least-once) — no separate outbox table for ES events. A small outbox is used only for CRUD entities that must emit events (e.g., binding verified). (recommended)

B) Separate transactional outbox table + poller for everything (uniform, but duplicates what Axon already guarantees)

X) Other

[Answer]: A - once Order is event-sourced, the Axon event-store commit + tracking-processor token already IS a durable, replayable, at-least-once outbox for that aggregate; a separate outbox table for the same events would be two sources of truth for one fact. Keep a small conventional outbox only where there is no event store behind the write, i.e. the CRUD reference/config entities (connections, bindings, webhook endpoints, item ownership, audit).

## Question 2 — Projection rebuild / recovery
How are CQRS projections rebuilt (e.g., after a bug fix or new projection)?

A) Replayable Axon **tracking processors**: reset the processor's token to replay from the event store; projections are disposable and rebuildable (recommended)

B) Manual rebuild scripts

X) Other

[Answer]: A

## Question 3 — Caching
What is cached in-process for U1?

A) Cognito **JWKS** (with refresh), ERP **connection config + declarative mappings** (loaded on deploy, Q2=B), and reference lookups; short TTL / explicit refresh (recommended)

B) No caching for the MVP

X) Other

[Answer]: A - one boundary worth stating explicitly: everything cached here is shared, rarely-changing, or globally-scoped (JWKS, connection config/mappings, reference lookups). Nothing tenant-scoped or business-critical (orders, customer bindings) is in this list, and it should stay that way - caching a tenant-scoped record risks serving stale or wrong-tenant data, which is exactly the failure mode the RLS backstop (functional design plan Q2) exists to prevent.

## Question 4 — Credential encryption key management (AES-GCM)
How is the AES-GCM key for ERP credentials managed?

A) **KMS envelope encryption**: a KMS-generated data key encrypts credentials; the encrypted data key + `keyId` stored with the ciphertext (recommended; behind a `CredentialCipher` port so local/Floci uses a dev key)

B) Symmetric key material stored in Secrets Manager, referenced by `keyId`

X) Other

[Answer]: A

## Question 5 — Consumer concurrency & ordering
Concurrency model for processors/consumers at MVP scale?

A) Single-segment tracking processors where per-order ordering matters; SQS FIFO `MessageGroupId = orderId` for integration; tune segments/parallelism later from metrics (recommended)

B) Parallel segments / higher concurrency now

X) Other

[Answer]: A - Axon's default tracking-processor segmentation is already consistent-hashed by aggregate id, so even multiple segments preserve per-order ordering; this is a throughput knob, not a correctness one. Starting single-segment and tuning later from the event-store append rate / projection lag metrics (NFR requirements plan Q6) is the same reasoning already applied to deferring snapshot tuning - don't tune against a guess when the real signal will exist soon.

## Question 6 — Logical components confirmation
Confirm U1 introduces these logical components: Axon event store (PostgreSQL) + command/query gateways; tracking event processors + projectors; SNS topic + SQS FIFO queues + DLQs; `TokenValidator` + `TenantContextHolder` + authorization guards; RLS policies (projection/reference tables) + privileged projector role; `CredentialCipher`; OpenTelemetry pipeline with correlation-id propagation; health endpoints (DB, SQS reachability, Cognito JWKS).

A) Confirm (recommended)

X) Other / additions

[Answer]: A - one addition: name the small CRUD outbox table + relay/poller (from Q1) as its own logical component. It is a real component distinct from the Axon-based relay and isn't otherwise covered by 'tracking event processors + projectors', which is ES-specific language; without naming it, logical-components.md could end up missing the one relay path that actually needs a hand-built table and poller.

---

## Section B — Generation checklist (after approval)
- [ ] `nfr-design-patterns.md` — ES/CQRS relay, projection replay/rebuild, caching, envelope encryption, idempotency/ordering, tenant-isolation (app + RLS), observability/health, timeouts (per-external-call defaults)
- [ ] `logical-components.md` — the U1 logical components and how they integrate (event store, processors/projectors, SNS/SQS+DLQ, token/tenant/authz, RLS + roles, cipher, OTEL, health)
