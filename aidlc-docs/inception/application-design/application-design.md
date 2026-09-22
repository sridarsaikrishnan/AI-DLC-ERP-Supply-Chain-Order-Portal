# Application Design (Consolidated) — ERP & Supply Chain Order Portal

This document consolidates the application design. Detailed artifacts:
- `components.md` — component definitions, responsibilities, interfaces
- `component-methods.md` — method signatures and I/O types
- `services.md` — service layer and orchestration
- `component-dependency.md` — dependency matrix, communication patterns, data flow, diagram

---

## 1. Architectural Overview

**Style**: Modular monolith with clean module boundaries and an internal async queue, explicitly designed so modules can be extracted into microservices later. This fits the intentional lightweight PoC posture (Security/Resiliency baselines OFF, moderate volume) while preserving the same end-state as a microservices architecture.

**Coarse-grained module groups (future extraction seams)**:
- **Identity** — authentication, MFA, tenant/role context, authorization
- **Portal/Order** — client-facing order operations, canonical model, lifecycle
- **Integration** — routing, mapping/translation (DSL), ERP adapters, async workers
- **Admin/Config** — ERP instance registration, routing rules, mappings, config view

**Primary architectural driver (NFR-2)**: adding a new ERP is configuration + a thin adapter (days, not months). Achieved by isolating ERP specifics in the Integration group behind a common adapter interface and a mapping DSL, keeping the core order/routing engine ERP-agnostic.

## 2. Key Design Decisions

| Decision | Choice | Source |
|---|---|---|
| Architecture style | Modular monolith, extract-to-services later | Clarification 1 (recommended) |
| Module boundaries | Coarse-grained: Portal/Order, Integration, Admin/Config, Identity | Clarification 2 = A |
| ERP communication | Fully async via internal queue/workers; status via polling and/or webhooks | Q2 = C |
| Mapping representation | Small mapping DSL, admin-managed via minimal UI | Q3 = B, US-Q5 = B |
| Routing rules | Ordered, first-match-wins, explicit fallback rejection | Q4 = C |
| Lifecycle states | Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled, Amended | Q5 = B |
| Tech stack | To be recommended in NFR Requirements | Q6 = A |
| Tenant isolation | Row-level filtering in shared store | Req D4 = B |

## 3. Components (summary)

| ID | Component | Module Group |
|---|---|---|
| C1 | Identity & Access | Identity |
| C2 | Order Intake API | Portal/Order |
| C3 | Canonical Model | Portal/Order |
| C4 | Order Lifecycle Manager | Portal/Order |
| C5 | Routing Engine | Integration |
| C6 | Mapping / Translation Engine | Integration |
| C7 | ERP Adapter Layer | Integration |
| C8 | Async Work Queue & Workers | Integration |
| C9 | Admin Configuration | Admin/Config |
| C10 | Persistence / Data Store | Cross-cutting |

## 4. Services (summary)

| ID | Service | Module Group | Core Orchestration |
|---|---|---|---|
| S1 | Order Service | Portal/Order | Place order, corrective actions, reads |
| S2 | Integration Service | Integration | Async pipeline: route -> map -> adapter -> lifecycle update; status sync |
| S3 | Admin/Config Service | Admin/Config | Onboard instances, manage routing/mappings, config view |
| S4 | Identity Service | Identity | Login/MFA, security context, authorization |

## 5. Primary Flows (summary)

**Order submission**: Client -> Order Intake API -> (auth, validate, persist Submitted, enqueue) -> ack. Async worker: route -> (NoMatch -> Failed) -> map canonical->ERP -> adapter.submit -> record Accepted/Failed.

**Status sync**: scheduler/webhook -> worker -> adapter.fetchStatus / receiveWebhook -> map ERP->canonical -> lifecycle applyStatusUpdate (latest-wins + history).

**Corrective action**: Client -> Order Intake API -> (auth, validate state, enqueue) -> ack. Async worker: map -> adapter.sendCorrectiveAction -> record outcome.

**Admin config**: Administrator -> Admin UI/API -> register instance / define routing rules / define mapping DSL (validate) / view config.

## 6. Alignment to Requirements & Stories
- **Extensibility (NFR-2)**: Integration group + adapter interface + mapping DSL localize all ERP-specific work.
- **Content-based routing (FR-3, US-6.2)**: Routing Engine with ordered first-match-wins + fallback rejection.
- **Full lifecycle + corrective actions (FR-5, US-4.x, US-5.x)**: Lifecycle Manager with fuller state set and corrective orchestration.
- **Multi-tenancy (FR-6, NFR-3)**: Security context + row-level tenant filtering in persistence.
- **Auth (FR-7, US-1.x)**: Identity Service with username/password + MFA.
- **Admin config via minimal UI (US-6.x)**: Admin/Config Service.

## 7. Deferred (designed-for, not built in MVP)
AI-assisted connector generation, self-service onboarding wizard, cross-system failover, SAP adapter, partner/API-key access. The adapter interface, mapping DSL, and routing model provide the extension points for these.
