# Application Design Plan — ERP & Supply Chain Order Portal

**Role**: Software architect
**Purpose**: Identify the high-level components, their responsibilities and interfaces, the service/orchestration layer, and the dependencies between them — mapping to the requirements (FR-01..FR-40), the stories (US-001..US-038), and the ten designed screens. Detailed business logic and data models come later in Functional Design.

**How to use this file**: Answer every `[Answer]:` tag in Section A. Many architectural choices are already fixed by the requirements (see "Already decided" below), so these questions focus only on the open component-boundary decisions. Where you have no strong preference, pick the recommended option and I'll proceed.

## Already decided (from requirements — not re-asked)
- Modular monolith, two deployables (`api`, `worker`) plus a `ui` container; Java + Spring Boot + Spring for GraphQL, React, RDS PostgreSQL, Amazon SQS FIFO + SNS, Amazon Cognito (identity), AWS/ECS, Terraform. Local dev via Floci (emulates Cognito/SQS/SNS) + a real PostgreSQL container.
- Canonical model with declarative field mappings (no template language); adapter seam per ERP; transactional outbox; retry + dead-letter topics; read model for reseller queries.
- Separate reseller vs operator GraphQL schemas; no ERP identity on reseller surfaces (FR-19).

---

## Section A — Application Design Questions (please answer)

## Question 1
How should the `api` deployable expose the two audiences?

A) One Spring Boot process hosting two separate GraphQL schemas/endpoints (reseller at `/graphql`, operator at `/admin/graphql`), isolated by schema and authorization

B) Two separate API processes (reseller-api and operator-api) from the start

C) One process, one schema, separated only by field-level authorization

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
How should the canonical↔ERP mapping definitions be stored and loaded?

A) In PostgreSQL (operator-editable at runtime via admin UI), versioned, cached in-process

B) As version-controlled config files (JSON/YAML) shipped with the app, reloaded on deploy

C) Hybrid — files are the source of truth in git, imported into PostgreSQL for runtime editing and audit

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
How should ERP adapters be structured so a new ERP is "config + mappings", not code?

A) A single generic REST adapter driven entirely by connection config + mappings; ERP-specifics live in config and a small set of named transform functions

B) A thin per-ERP adapter class implementing a common `IErpAdapter` interface, registered in a provider registry; shared REST/mapping machinery underneath

C) Combination — common `IErpAdapter` + generic REST engine, with per-ERP adapters only for quirks (auth, pagination, status vocab)

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
Where does order routing and the lifecycle state machine live?

A) In the `worker` (routing resolved at Validated; state transitions driven by outbox/consumers), with the `api` only accepting commands and serving the read model

B) In the `api` (synchronous domain services), with the `worker` only for ERP delivery

C) Split — command validation in `api`, routing + delivery + status ingestion in `worker`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
How should the read model (what resellers query) be maintained?

A) Same PostgreSQL database, separate read-optimized tables/projections updated by the worker from canonical events

B) Same tables as the write model, queried directly (no separate projections) for the MVP

C) Separate read store

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
How should the Gradle multi-module build be organized at the top level (component boundaries)?

A) By layer: api, worker, domain, infrastructure, contracts, ui (few modules)

B) By feature/module: ordering, routing, integration(ERP), identity, webhooks, admin, platform — each with its own domain + infrastructure, composed into api/worker application modules

C) Hybrid — feature modules for the domain, shared infrastructure and contracts modules, thin api/worker application modules

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 7
How is the tenant identity resolved and enforced across components?

A) A dedicated auth/tenant-context component reads the validated token claim once per request/message and injects an immutable TenantContext that every query/command must use

B) Each resolver/handler reads the claim itself

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
Should the ERP status-change ingestion (poll/events) be its own component within the worker?

A) Yes — a distinct Ingestion component per adapter, translating ERP changes to canonical events on a schedule (in-app scheduler)

B) No — fold ingestion into the delivery adapter

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
For the operator admin UI and reseller UI, should they be one React app or two?

A) Two separate React apps (reseller, operator) served from the `ui` container, each hitting its own schema — strongest isolation, aligns with FR-19

B) One React app with role-based routing

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Section B — Methodology & Execution Checklist (executed after answers approved)

- [x] Load requirements, stories, personas, and `design/README.md` screen inventory
- [x] Identify components and responsibilities → `components.md`
- [x] Define component method signatures (interfaces, I/O types; business rules deferred) → `component-methods.md`
- [x] Define the service/orchestration layer → `services.md`
- [x] Define dependencies, communication patterns, and data flows → `component-dependency.md`
- [x] Map each of the ten designed screens to components, routes, and API operations
- [x] Note "Not yet designed" surfaces (sign in, new-order form, item catalog, mapping viewer) as components needing UI design later
- [x] Consolidate into `application-design.md`
- [x] Validate completeness and consistency against FR/US and extension constraints (SECURITY/RESILIENCY/PBT)

---

## Notes
- This stage is high-level: components, interfaces, services, dependencies. No detailed algorithms or schemas (those are Functional Design).
- Reseller-facing components must structurally exclude ERP identity (separate schema/DTOs), per FR-19/AC-02.
