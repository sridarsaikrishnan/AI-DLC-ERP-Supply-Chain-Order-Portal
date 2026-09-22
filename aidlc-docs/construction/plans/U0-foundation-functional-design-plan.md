# Functional Design Plan — U0 Platform Foundation

## Unit Context
U0 is the shared foundation depended on by all other units. It has no direct user stories but must define the technology-agnostic business/domain models and rules that everyone else builds on:
- **Canonical domain model**: CanonicalSalesOrder, CanonicalOrderStatus, CanonicalProduct, CanonicalInventory + validation
- **Config domain model**: ErpInstance, RoutingRule, MappingDefinition (owned here, used by U3/U4)
- **Tenant model & context**: Tenant, SecurityContext propagation, row-level isolation rules
- **Async queue abstraction**: Job model, enqueue/consume contract, basic retry semantics
- **Persistence contracts**: repository interfaces, tenant-aware access rules

This is technology-agnostic (no DB/framework choices yet — those come in NFR Requirements).

## Execution Checklist (artifacts)
- [ ] `business-logic-model.md` (foundation processes: validation, tenant scoping, enqueue/consume, config resolution)
- [ ] `business-rules.md` (validation rules, tenant isolation rules, retry/idempotency rules)
- [ ] `domain-entities.md` (canonical + config + tenant + job entities and relationships)

---

## Functional Design Questions

## Question 1
For the CanonicalSalesOrder, what core fields should the MVP canonical model include? (Pick the closest; refine in Other.)

A) Header (tenant, client ref, order date, ship-to, currency) + line items (product ref, quantity, unit, requested date) + free-form notes

B) Header + line items only (no notes, no currency — minimal)

C) Header + line items + pricing fields (unit price, totals) + notes

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
How should canonical product/inventory identity work across ERPs (since each ERP has its own IDs)?

A) Canonical uses a portal-side product key; mapping layer translates to/from each ERP's native product ID

B) Canonical carries the ERP-native product ID directly (client must know ERP product codes)

C) Portal-side key with optional client-facing SKU/alias, mapped to native IDs per instance

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
For tenant isolation rules at the foundation level, what's the enforcement approach?

A) Every tenant-owned repository call REQUIRES a tenant id from SecurityContext; queries without it are rejected (fail-closed)

B) Tenant id applied automatically as a global filter; developers can't bypass it

C) Both: automatic global filter AND fail-closed if context is missing (recommended)

D) Other (please describe after [Answer]: tag below)

[Answer]: Recommended

## Question 4
What retry/idempotency semantics should the async Job model guarantee for MVP (resiliency baseline is OFF, so keep it basic)?

A) At-least-once delivery with a bounded retry count; handlers must be idempotent (dedupe by job/order key)

B) At-most-once (no retry) — simplest, may drop on failure

C) At-least-once with retry + a dead-letter list for exhausted jobs (slightly more than basic)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
The MappingDefinition uses a small mapping DSL (decided earlier). At the foundation/domain level, how should we model it for MVP?

A) Store DSL as a text/document field on MappingDefinition; parsing/execution is U3's concern (foundation just persists it)

B) Model structured mapping entries (source path, target path, transform expr) as first-class entities

C) Hybrid: structured entries for simple field maps + a text expression field for complex transforms

D) Other (please describe after [Answer]: tag below)

[Answer]: recommeded

## Question 6
For RoutingRule at the domain level, how should conditions be represented?

A) A list of condition clauses (field, operator, value) ANDed together, plus target instance id and an explicit order index

B) A single expression string (evaluated by U3), plus target instance id and order index

C) Other (please describe after [Answer]: tag below)

[Answer]: recommeded

---

Fill in the `[Answer]:` tags and let me know when done.
