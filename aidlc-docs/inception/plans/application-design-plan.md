# Application Design Plan — ERP & Supply Chain Order Portal

## Purpose
This plan defines how we'll design the high-level components, services, and their dependencies. Please answer the questions by filling in the `[Answer]:` tags, then let me know. I'll resolve any ambiguities before generating the design artifacts.

---

## Proposed Component Landscape (draft, for your review)

Based on requirements and stories, I see these candidate components:

1. **Identity & Access** — authentication (username/password + MFA), tenant scoping, authorization for corrective actions.
2. **Order Intake / Portal API** — accepts canonical orders, validation, exposes client-facing operations.
3. **Canonical Model** — ERP-agnostic domain model for the four business data types (Sales Order, Order Status, Product Catalog, Inventory Availability).
4. **Routing Engine** — evaluates content-based rules to select the target ERP instance.
5. **Mapping / Translation** — converts canonical ↔ ERP-native payloads using stored mapping configuration.
6. **ERP Adapter Layer** — thin, per-ERP adapters (ERP Next, Odoo) that speak each ERP's protocol; new ERP = new config + thin adapter.
7. **Order Lifecycle Manager** — tracks lifecycle state, ingests ERP status updates, orchestrates corrective actions (resubmit/cancel/amend).
8. **Admin Configuration** — minimal internal UI/API to register ERP instances, manage routing rules and mappings, view current config.
9. **Persistence / Data Store** — tenant-scoped storage of orders, status history, config, mappings (row-level tenant isolation).

## Execution Checklist (mandatory artifacts)
- [ ] Generate `components.md` (component definitions + responsibilities + interfaces)
- [ ] Generate `component-methods.md` (method signatures + I/O types; business rules later)
- [ ] Generate `services.md` (service definitions + orchestration patterns)
- [ ] Generate `component-dependency.md` (dependency matrix + communication patterns + data flow)
- [ ] Generate consolidated `application-design.md`
- [ ] Validate design completeness and consistency

---

## Design Questions

## Question 1
What overall architectural style should the MVP use?

A) Modular monolith — one deployable app with clear internal module boundaries (simplest for a PoC; still cleanly separable later)

B) Microservices — separate services per major component from day one

C) Modular monolith now, with module boundaries explicitly designed so components can be extracted into services later (recommended)

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
How should the portal communicate with ERP instances (given the adapter layer)?

A) Synchronous calls to the ERP at submission time; status updates fetched by polling the ERP on a schedule

B) Synchronous submission, but status updates received via ERP webhooks/callbacks where supported (fallback to polling)

C) Fully asynchronous via an internal queue — submission is queued and processed by workers; status via polling and/or webhooks

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 3
How should the canonical↔ERP mapping be represented so admins can manage it (Q5=B minimal UI)?

A) Declarative mapping definitions stored as structured data (e.g., JSON/YAML records in the DB), edited via the admin UI

B) Rule/expression-based mapping (a small mapping DSL) stored and edited via the admin UI

C) Declarative field/value maps for the common case, plus optional expressions for the tricky fields

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4
How should the Routing Engine's content-based rules be structured?

A) Ordered list of condition→target-instance rules with first-match-wins precedence

B) Priority-scored rules (highest score wins), allowing overlap

C) Ordered rules with first-match-wins, plus an explicit default/fallback rejection when nothing matches

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 5
For the order lifecycle, how detailed should the state model be for MVP?

A) Minimal set: Submitted, Accepted, Failed, Cancelled

B) Fuller set: Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled, Amended

C) Configurable per ERP — canonical states plus ERP-specific mappings to those canonical states

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
Do you have a preferred technology stack for the design to assume, or should I recommend one in the NFR/Construction phase?

A) Recommend later (NFR Requirements stage) — no preference now

B) Prefer a specific stack (describe in Other: e.g., language, framework, database)

C) Constrain only the database now, recommend the rest later (describe DB in Other)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

Once all `[Answer]:` tags are filled in, tell me and I'll analyze for ambiguities, then generate the application design artifacts.
