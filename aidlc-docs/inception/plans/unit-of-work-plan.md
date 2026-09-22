# Unit of Work Plan — ERP & Supply Chain Order Portal

**Role**: Software architect / product owner
**Purpose**: Decompose the system into **units of work** (development/design units) and sequence them. This is a **modular monolith** (two deployables `api` + `worker`, plus `ui`), so a "unit" is a logical grouping of capability modules and stories for design + build — **not** an independently deployed service.

**Architecture note (2026-09-21)**: the system is **event-driven with event sourcing + CQRS via Axon Framework**. The `Order` aggregate is event-sourced (event store on PostgreSQL); reads come from CQRS projections. The Axon event store + projection framework is foundational and lives in **U1**; the event-sourced `Order` aggregate + projectors live in **U3**.

**How to use this file**: Answer the `[Answer]:` tags in Section A. Where you have no preference, pick the recommended option. After approval, Part 2 generates `unit-of-work.md`, `unit-of-work-dependency.md`, and `unit-of-work-story-map.md`.

---

## Proposed decomposition (for your review)

Mapping capability modules (`application-design.md` §4) and stories (`stories.md`) into 7 units:

| Unit | Capability modules | Key stories | Purpose |
|---|---|---|---|
| **U1 Platform Foundation** | `canonical-model`, `platform-infrastructure`, `access-control` + **Axon event store & CQRS projection framework** | US-003, US-004, US-016; cross-cutting DoD | Shared canonical model, persistence/messaging/outbox scaffolding, **Axon config (event store on PostgreSQL, command/query buses, projection framework)**, JWT/tenant-context/authorization. Built first. |
| **U2 ERP Integration** | `erp-integration` | US-027..US-031, US-036 | Adapter seam, Odoo (RPC) + ERPNext (REST) transports, mapping engine, connection registry, conformance suite. |
| **U3 Ordering, Routing & Delivery** | `order-management` (**event-sourced `Order` aggregate + projectors**), `order-routing`, `item-catalog` (ownership), delivery on `worker` | US-006, US-009, US-010, US-013, US-014, US-017..US-021, US-033 | Event-sourced order lifecycle (Axon), CQRS projections, routing, guaranteed delivery, status ingestion. |
| **U4 Reseller API & Webhooks** | reseller GraphQL on `api`, `webhook-delivery`, `customer-binding` (read), `item-catalog` (read) | US-005a, US-006, US-007q, US-011, US-012, US-022..US-026, US-024 | The reseller-facing GraphQL surface + webhooks + delivery log. |
| **U5 Operator Admin (API + Web)** | operator GraphQL on `api`, `customer-binding`, `item-catalog` (conflicts), `audit-trail`, operator React app | US-001, US-002, US-005, US-032..US-035 | Onboarding, bindings, connections, item-ownership conflicts, failed messages, audit. |
| **U6 Reseller Web App** | reseller React app | US-007, US-008, US-022, US-024 | The reseller UI (consumes U4). |
| **U7 Developer Enablement & Infrastructure** | Terraform, Docker Compose, seed tool, CI | US-037, US-038 | One-command local stack (Floci + Postgres), seed tool, IaC, pipeline. |

Proposed build order: **U1 → U2 → U3 → U4 → U5 → U6**, with **U7 developed alongside U1** (infra/local env needed early).

---

## Section A — Questions (please answer)

## Question 1
Is the 7-unit decomposition above at the right granularity?

A) Yes — use the 7 units as proposed

B) Coarser — merge into fewer units (e.g., combine U4+U6 reseller-facing, and U2+U3 into one "core engine")

C) Finer — split further (e.g., separate Webhooks from Reseller API, separate Ingestion from Delivery)

X) Other (describe after [Answer]: tag below)

[Answer]: A

## Question 2
What should drive the **build sequence**?

A) Foundation-first as proposed (U1 → U2 → U3 → U4 → U5 → U6; U7 alongside U1)

B) Thin end-to-end slice first (a minimal order flow across U1–U4 for one ERP), then broaden

C) Other (describe after [Answer]: tag below)

[Answer]: X - Like B (a thin end-to-end order flow across U1-U4), but covering both Odoo and ERPNext, not just one ERP. The claim being tested is that two differently-shaped ERPs fit one canonical model; validating with a single ERP would not test that.

## Question 3
How should the **two React apps** be treated as units?

A) Reseller Web App is its own unit (U6); operator Web App is bundled inside U5 (Operator Admin API + Web)

B) One combined "Frontend" unit for both apps

C) Two separate UI units (reseller UI, operator UI), each separate from its API

X) Other (describe after [Answer]: tag below)

[Answer]: A

## Question 4
Where should the shared capabilities (`canonical-model`, `platform-infrastructure`, `access-control`) live?

A) In a single **U1 Platform Foundation** unit that every other unit depends on (as proposed)

B) Split into two (a pure `canonical-model`/contracts unit and a separate platform/infra+security unit)

X) Other (describe after [Answer]: tag below)

[Answer]: A

## Question 5
Confirm the **code organization** (greenfield): a single Git **mono-repo** with a Gradle multi-module build for the backend (`api`, `worker` hosts + capability modules) and a `ui/` folder for the two React apps, `infra/` for Terraform.

A) Yes — single mono-repo, Gradle multi-module + `ui/` + `infra/` (recommended)

B) Separate repos (e.g., backend, frontend, infra)

X) Other (describe after [Answer]: tag below)

[Answer]: A

## Question 6
Team/ownership model influencing unit boundaries?

A) Single team builds all units sequentially (MVP) — boundaries are for design clarity, not parallel teams

B) Multiple parallel workstreams — optimize units for parallel development

X) Other (describe after [Answer]: tag below)

[Answer]: A

---

## Section B — Generation checklist (executed after approval)
- [x] Generate `unit-of-work.md` (unit definitions, responsibilities, modules, code organization strategy for greenfield)
- [x] Generate `unit-of-work-dependency.md` (dependency matrix + build/sequence order)
- [x] Generate `unit-of-work-story-map.md` (every story US-001..US-038 assigned to a unit; future US-F* noted)
- [x] Validate unit boundaries and that all stories are assigned
- [x] Confirm alignment with the capability modules and extension constraints
