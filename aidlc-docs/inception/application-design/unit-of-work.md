# Units of Work — ERP & Supply Chain Order Portal

**Architecture**: Modular monolith (single deployable). Each unit is a logical module with clean boundaries that also serves as a future microservice extraction seam.

**Decomposition confirmed**: 5 units (Q1=A). **Shared model/persistence**: U0 is a shared internal module all units depend on (Q4=A). **Catalog/inventory boundary**: client-facing lookup API in U2, ERP fetch+map in U3 (Q2=A). **First extraction candidate**: U3 Integration (Q6=A).

---

## U0. Platform Foundation (shared)
- **Responsibility**: Shared building blocks used by all units.
- **Contents**:
  - Canonical Model (C3): `CanonicalSalesOrder`, `CanonicalOrderStatus`, `CanonicalProduct`, `CanonicalInventory`, validation
  - Persistence (C10): repositories, row-level tenant isolation, DB access
  - Tenant context plumbing (SecurityContext propagation)
  - Async queue infrastructure (C8 base: enqueue, worker host, retry primitive)
  - Config data model (ERP instances, routing rules, mapping definitions) — owned here so U3 and U4 share it
- **Depends on**: nothing (foundation)

## U1. Identity & Access
- **Responsibility**: Authentication, MFA, security context resolution, authorization.
- **Contents**: C1 Identity & Access; S4 Identity Service
- **Stories**: E1 (US-1.1, US-1.2, US-1.3)
- **Depends on**: U0 (persistence for user/tenant records)

## U2. Ordering & Lifecycle
- **Responsibility**: Client-facing order operations, canonical validation orchestration, lifecycle tracking, corrective-action initiation, catalog/inventory lookup API.
- **Contents**: C2 Order Intake API, C4 Lifecycle Manager; S1 Order Service
- **Stories**: E2 (US-2.1, US-2.2), E3 client API (US-3.1, US-3.2), E4 (US-4.1, US-4.2, US-4.3), E5 (US-5.1, US-5.2, US-5.3)
- **Depends on**: U0 (canonical model, persistence, queue), U1 (auth/context), U3 (async fulfillment: routing/mapping/adapters; catalog/inventory fetch+map)

## U3. Integration (Routing + Mapping + Adapters + Workers)
- **Responsibility**: The async engine that turns queued work into ERP interactions and lifecycle updates. Executes routing, mapping/translation, adapter calls, and status sync.
- **Contents**: C5 Routing Engine, C6 Mapping/Translation Engine, C7 ERP Adapter Layer (ErpNextAdapter, OdooAdapter), C8 Workers; S2 Integration Service
- **Stories**: fulfillment of E2/E3/E4/E5; execution of E6 routing/mapping (US-6.2, US-6.3 runtime behavior)
- **Depends on**: U0 (canonical model, persistence, config data model, queue)
- **Note**: First microservice extraction candidate (ERP I/O + workers scale independently).

## U4. Admin & Configuration
- **Responsibility**: Minimal internal UI/API for admins to register ERP instances, manage routing rules and mapping DSL, and view current config/connectivity.
- **Contents**: C9 Admin Configuration; S3 Admin/Config Service
- **Stories**: E6 (US-6.1, US-6.2 authoring, US-6.3 authoring, US-6.4)
- **Depends on**: U0 (config data model, persistence), U1 (admin auth), U3 (connectivity checks / mapping validation)

---

## Recommended Build Sequence (Q3=C)
1. **U0 Platform Foundation** — everything depends on it (canonical model, persistence, config data model, queue).
2. **U1 Identity & Access** — gates the APIs; needed before exposing U2/U4.
3. **U3 Integration** — the core engine; U2 depends on it for fulfillment. Exercised during construction using seed config (instances/routing/mappings) since the U4 authoring UI comes later.
4. **U2 Ordering & Lifecycle** — client-facing flows built on U3 fulfillment.
5. **U4 Admin & Configuration** — authoring UI/API built last; its data model already exists in U0, so U3 can run on seed config until U4 lands.

## Code Organization Strategy (Greenfield, Q5=A)
Single repository, one deployable app, folder-per-module for clean extraction seams:

```
/ (repo root)
├── src/
│   ├── modules/
│   │   ├── foundation/      # U0: canonical model, persistence, tenant, queue infra, config models
│   │   ├── identity/        # U1
│   │   ├── ordering/        # U2: order intake API, lifecycle
│   │   ├── integration/     # U3: routing, mapping, adapters, workers
│   │   └── admin/           # U4: admin UI/API
│   ├── app/                 # composition root / bootstrap / HTTP wiring
│   └── shared/              # cross-cutting utilities (logging, errors)
├── tests/
└── (build/config files per chosen stack — decided in NFR Requirements)
```

- Modules communicate through explicit interfaces (the component interfaces from Application Design), not by reaching into each other's internals.
- U0 is imported by all; no reverse dependencies into feature modules.
- Extraction path: a module folder + its U0 slice can be lifted into a service with HTTP/RPC replacing in-process calls.
