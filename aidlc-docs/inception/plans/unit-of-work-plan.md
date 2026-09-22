# Unit of Work Plan — ERP & Supply Chain Order Portal

## Purpose
Decompose the system into units of work for the CONSTRUCTION phase. Because the architecture is a **modular monolith** (single deployable), each unit is a **logical module** with clean boundaries that doubles as a future microservice extraction seam. Please answer the questions by filling in the `[Answer]:` tags, then let me know.

---

## Proposed Unit Decomposition (draft, for your review)

Aligned to the 4 coarse-grained module groups from Application Design, plus shared foundations:

- **U0. Platform Foundation (shared)** — canonical model (C3), persistence (C10), tenant context plumbing, async queue infra (C8 base). Shared by all units.
- **U1. Identity & Access** — C1 (auth, MFA, context, authorization). Stories: E1.
- **U2. Ordering & Lifecycle** — C2 Order Intake API, C4 Lifecycle Manager. Stories: E2, E3 (client-facing lookups), E4, E5.
- **U3. Integration (Routing + Mapping + Adapters + Workers)** — C5, C6, C7, C8 workers. Stories: supports E2/E3/E4/E5 fulfillment; E6 mapping/routing execution.
- **U4. Admin & Configuration** — C9 admin UI/API (register instances, routing rules, mapping DSL, config view). Stories: E6.

Note: E3 (catalog/inventory lookup) spans U2 (client API) and U3 (fetch/map from ERP). The plan questions below let you confirm where that boundary sits.

## Execution Checklist (mandatory artifacts)
- [ ] Generate `unit-of-work.md` (unit definitions, responsibilities, code organization strategy for greenfield)
- [ ] Generate `unit-of-work-dependency.md` (dependency matrix)
- [ ] Generate `unit-of-work-story-map.md` (stories mapped to units)
- [ ] Validate unit boundaries and dependencies
- [ ] Ensure all stories assigned to units

---

## Planning Questions

## Question 1
Do the proposed units (U0 Foundation, U1 Identity, U2 Ordering & Lifecycle, U3 Integration, U4 Admin & Config) match how you want to break down the work?

A) Yes — use these units as proposed

B) Yes, but split U3 Integration into two units: "Routing & Mapping" and "Adapters & Workers"

C) Yes, but merge U1 Identity into U0 Foundation (treat auth as foundational)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
For the catalog/inventory lookup (E3), where should the boundary sit?

A) Client-facing lookup API lives in U2; actual fetch+map from ERP lives in U3 (U2 calls U3)

B) Put the entire lookup path (API + fetch + map) in U3 Integration, with U2 only proxying

C) Other (please describe after [Answer]: tag below)

[Answer]: use recommended

## Question 3
What build order / dependency sequence do you want for construction?

A) Foundation first (U0), then Identity (U1), then Integration (U3), then Ordering & Lifecycle (U2), then Admin (U4)

B) Foundation first (U0), then Admin (U4) so instances/routing/mappings exist, then Integration (U3), then Ordering (U2), Identity (U1) alongside

C) Recommend the optimal sequence based on dependencies

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
How should units share the canonical model and persistence (U0)?

A) U0 is a shared internal library/module all units depend on (recommended for a monolith)

B) Each unit owns its own copy/subset of models (more isolation, more duplication)

C) Other (please describe after [Answer]: tag below)

[Answer]: recommended

## Question 5
Code organization for the monolith (greenfield). Preferred layout?

A) Single repository, one app, folder-per-module (e.g., /modules/identity, /modules/ordering, /modules/integration, /modules/admin, /modules/foundation) — clean extraction seams (recommended)

B) Single repository, layered by technical type (controllers/, services/, repositories/) with modules as subfolders

C) Monorepo with separate packages per module (heavier, closer to microservice layout)

D) Other (please describe after [Answer]: tag below)

[Answer]: recommended

## Question 6
Will any unit have distinct scaling/deployment needs in the future extraction that should be noted now?

A) Integration (U3) is the most likely to need independent scaling (ERP I/O + workers) — note it as first extraction candidate

B) No distinct needs anticipated — treat all equally

C) Other (please describe after [Answer]: tag below)

[Answer]: recommended

---

Once all `[Answer]:` tags are filled in, tell me and I'll analyze for ambiguities, then generate the unit artifacts.
