# Functional Design Plan — U1 Platform Foundation

**Unit**: U1 Platform Foundation (`canonical-model`, `platform-infrastructure`, `access-control`, Axon event store + projection framework).
**Scope of this functional design**: the shared **business** foundations that every other unit builds on — the canonical domain model, the reference/config entities, tenant-isolation and authorization rules, the canonical error taxonomy, and the event-sourcing/command/event contracts for the `Order` aggregate. Infrastructure specifics (AWS/Terraform, Axon tuning) come in NFR/Infrastructure Design.

**How to use this file**: answer the `[Answer]:` tags in Section A. Recommended options are marked; pick them if you have no preference. Much is already fixed in `application-design/` (canonical-model, events, tenancy-and-routing), so these are the open functional decisions.

---

## Section A — Questions

## Question 1 — Identifier scheme
How should platform IDs look?

A) Prefixed, sortable IDs — `ord_…`, `itm_…`, `cust_…`, `conn_…`, backed by UUIDv7/ULID (recommended: readable, time-sortable, opaque)

B) Plain UUIDv4

C) Database sequences / numeric IDs

X) Other

[Answer]: A

## Question 2 — Tenant isolation enforcement
How is tenant scoping enforced at the data layer?

A) Application-level: an enforced tenant filter applied via `TenantContext` on every repository/query, with object-level ownership checks (recommended for MVP)

B) PostgreSQL Row-Level Security (RLS) as the primary mechanism

C) Both — application-level scoping plus RLS as a database backstop (strongest, more setup)

X) Other

[Answer]: X - C's substance (application-level TenantContext, already Q7=A in application design, plus PostgreSQL RLS as a backstop), scoped precisely: RLS on the CQRS projection tables and the reference/config tables (ErpConnection binding, WebhookEndpoint, ItemOwnership, AuditEntry), which are where tenant-scoped queries actually run. Not on Axon's internal event-store tables (domain_event_entry etc.): those are never queried in a tenant-scoped way, only by the framework/projector process, which uses its own privileged role that bypasses RLS; the app-query role is the one bound by RLS policies. Justification: SECURITY-11 requires defense-in-depth, no single control should be the sole line of defense, and tenant isolation is this platform's core promise (FR-01, US-016) - one missed WHERE-tenant_id clause in a new query should not be enough to leak across tenants.

## Question 3 — Authorization roles
What role model for the MVP?

A) Two roles: `RESELLER` (tenant-scoped) and `OPERATOR` (admin) (recommended)

B) `RESELLER` + granular operator permissions (onboarding, connections, mappings, bindings, audit as separate grants)

X) Other

[Answer]: A

## Question 4 — Money & rounding
How is money represented?

A) `BigDecimal` amount + ISO-4217 currency; amounts taken as-is from the ERP; no FX conversion; round half-up only for display (recommended)

B) Integer minor units (e.g., cents)

X) Other

[Answer]: A

## Question 5 — Canonical error taxonomy
How granular are the reseller-safe canonical error codes?

A) A small fixed enum, e.g. `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `MIXED_ERP_ORDER`, `ERP_UNAVAILABLE`, `FORBIDDEN`, `RATE_LIMITED`, `INTERNAL` — each with a reseller-safe message; raw ERP errors mapped into these (recommended)

B) Freeform error strings

X) Other

[Answer]: A - model the enum as a closed/sealed set (Java sealed interface or enum), so the compiler forces every new error path to pick one of the existing reseller-safe codes. That is what makes FR-19/AC-02 structurally enforced rather than a convention a future change can quietly break.

## Question 6 — Event sourcing specifics (Order aggregate)
Snapshots and identifiers for the Axon-sourced `Order`?

A) Aggregate id = `orderId`; snapshot every N events (e.g., 50); upcasters for event evolution (recommended)

B) No snapshots for the MVP (replay full stream)

X) Other

[Answer]: X - Aggregate id = orderId, and upcasters for event evolution (both effectively required once you event-source anything meant to run in production and change over time - skipping upcasters just defers the pain to the first schema change). Skip snapshotting for the MVP rather than pre-committing to every 50 events: an order's event stream is short (create, submit, validate, route, a handful of retry/status events, close - rarely more than 15-20 events), so periodic snapshotting has no payoff yet, and picking a threshold now would be tuning against no evidence. Axon supports snapshotting natively; enable and tune it later from real event-volume data in NFR/Infrastructure Design.

## Question 7 — Reference/config data lifecycle
Delete semantics for connections, bindings, webhook endpoints, item ownership?

A) Soft-delete / disable (status flags like active/disabled/paused); nothing hard-deleted — preserves audit and history (recommended)

B) Hard-delete

X) Other

[Answer]: A

## Question 8 — Conventions to confirm (bundle)
Confirm these defaults (answer A to accept all, or note exceptions):
- Times are UTC, ISO-8601, stored as `Instant`.
- Currency codes ISO-4217; country codes ISO-3166 alpha-2.
- All monetary and quantity values use `BigDecimal`.
- Optimistic concurrency on reference/config aggregates (version column); the `Order` aggregate uses Axon's sequence.

A) Accept all conventions (recommended)

X) Other / exceptions (describe)

[Answer]: A

---

## Section B — Generation checklist (executed after answers approved)
- [x] `business-logic-model.md` — foundational flows: command→event→projection for `Order`; tenant-context resolution; canonical error mapping; audit write path; SOLID adherence
- [x] `domain-entities.md` — value objects, event-sourced `Order`, reference/config entities, projections, ER diagram, isolation model
- [x] `business-rules.md` — BR-U1-01..20: tenant isolation, authorization, uniqueness (AC-05/06), no-ERP-identity (FR-19, sealed errors), money/rounding, event sourcing, audit
- [x] `testable-properties.md` — PBT-01: P-U1-01..13 incl. ES/CQRS replay & projection consistency, uniqueness invariants, tenant-scope & no-ERP-identity invariants
- [x] Validate against U1 stories (US-003, US-004, US-015, US-016) and extension constraints (SECURITY/RESILIENCY/PBT)
