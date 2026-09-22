# Application Design — ERP & Supply Chain Order Portal

**Date**: 2026-09-21
**Stage**: INCEPTION → Application Design
**Consolidates**: `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`, `canonical-model.md`, `events.md`.

### Reading guide (start here)
| Read this | To understand |
|---|---|
| `tenancy-and-routing.md` | Whether it's a microservice, how modules are separated, how an ERP **instance** maps to a **reseller** (bindings), and how inbound data is reverse-routed to the right reseller without cross-tenant leakage |
| `canonical-model.md` | What a reseller **sends in**, the **canonical model** internally, and what they **get back** — with sample JSON and GraphQL, the canonical↔ERP **status mapping table**, and how ERP identity is kept out of reseller types (FR-19) |
| `events.md` | Every message: commands, internal domain events, integration events, and public webhook events — with names, payloads, and the SNS/SQS queues they travel on |
| `services.md` | The concrete services (proper class names) in `api` and `worker`, and the end-to-end orchestration flows |
| `components.md` | The 19 components, their responsibilities and which deployable hosts them |
| `component-methods.md` | Interface signatures per component |
| `component-dependency.md` | Dependency matrix, data-flow diagram, and the screen→component→API mapping |
**Inputs**: `requirements.md` (FR-01..FR-40, NFR, SECURITY/RESILIENCY/PBT), `stories.md` (US-001..US-038, US-F1..US-F7), `personas.md` (P1..P4), `design/README.md` (10 screens), and the approved `application-design-plan.md` answers.

This is a high-level design: components, interfaces, services, and dependencies. Detailed business rules, data schemas, and the lifecycle state machine specifics are produced per unit in Functional Design.

---

## 1. Architecture at a glance
- **Style**: modular monolith, event-driven between processes. Three deployables: `api` (Spring Boot), `worker` (Spring Boot), `ui` (two React apps). AWS-native.
- **Design decisions applied** (from the plan):
  - Q1=A — one `api` process, two isolated GraphQL schemas: reseller `/graphql`, operator `/admin/graphql`.
  - Q2=B — canonical↔ERP mappings are version-controlled files, loaded on deploy (operator runtime editing deferred; MVP has a read-only mapping viewer).
  - Q3=C — common `ErpAdapter` + a transport-agnostic request engine, with per-ERP **transport adapters** (Odoo XML-RPC/JSON-RPC, ERPNext REST) for protocol/auth/status quirks. *(Verified 2026-09-21: ERPNext is REST; Odoo is primarily RPC — see FR-24, O-12/O-13.)*
  - Q4=A — routing + lifecycle state machine live in the `worker`; `api` accepts commands and serves reads.
  - Q5=B — read model = same PostgreSQL tables queried directly (no separate projections for the MVP).
  - Q6=C — hybrid Gradle multi-module: feature/domain modules + shared infrastructure/contracts + thin `api`/`worker` app modules.
  - Q7=A — a dedicated tenant-context component injects an immutable `TenantContext`.
  - Q8=A — a distinct ingestion component per adapter, in-app scheduler.
  - Q9=A — two separate React apps (strongest reseller/operator isolation, FR-19).
- **Technology** (Section 5 of requirements): Java 21 + Spring Boot (Spring for GraphQL), React, RDS PostgreSQL, Amazon SQS FIFO + SNS, Amazon Cognito, ECS Fargate, Terraform; Floci for local AWS emulation.

## 2. Components (summary)
Shared: **C-01** Contracts, **C-02** Persistence, **C-03** Messaging, **C-04** Identity, **C-05** Security & Tenant Context, **C-06** Observability.
Domain: **C-07** Ordering, **C-08** Routing, **C-08b** Catalog & Item Ownership, **C-09** Customers & Bindings, **C-10** ERP Integration, **C-11** Delivery & Reliability, **C-12** Ingestion, **C-13** Webhooks & Delivery Log, **C-14** Audit.
Edge: **C-15** Reseller API, **C-16** Operator Admin API, **C-17** Reseller Web App, **C-18** Operator Web App, **C-19** Developer Enablement.
Full responsibilities and interfaces: see `components.md` and `component-methods.md`.

## 3. Service layer & orchestration
`api` intake + reads; `worker` runs the order-processing saga, delivery, ingestion, webhook dispatch, and the outbox relay. All ERP access flows through a single `ErpGateway`. Cross-process communication is via transactional outbox → SNS → SQS FIFO (per-order ordering). Full flows: see `services.md`.

## 4. Gradle module layout (Q6=C)

Modules are named for **what they do** (a capability), not for a layer. Each line shows the module and its responsibility.

```
# shared
:canonical-model          the shared language: canonical entities, domain events, error codes, reseller vs operator DTOs
:platform-infrastructure  implements the domain ports: persistence (JPA+Flyway), messaging (SQS/SNS/outbox),
                          identity (Cognito/JWT), credential crypto, observability

# domain capabilities
:order-management         order aggregate + lifecycle state machine + create/update/cancel + queries
:order-routing            resolve the one owning ERP connection from item ownership; reject mixed-ERP orders
:erp-integration          ErpAdapter seam + transport adapters (Odoo RPC, ERPNext REST) + mapping engine + connection registry + conformance
:item-catalog             items (read-only to resellers) + single-owner rule + duplicate-SKU conflict detection
:customer-binding         tenant<->ERP-customer bindings + verification + onboarding match suggestions
:webhook-delivery         webhook endpoints + signing + delivery log + replay
:audit-trail              append-only audit records with before/after values
:access-control           JWT validation, tenant-context resolution, authorization, Cognito admin provisioning

# application hosts (thin; compose the domain capabilities)
:api                      hosts reseller /graphql + operator /admin/graphql; command intake + reads
:worker                   hosts order processing, ERP delivery, status ingestion, webhook dispatch, outbox relay

# frontend
ui/reseller  ui/operator  React apps (one per audience)
```

**Old → new names** (renamed for clarity): `contracts → canonical-model`, `infrastructure → platform-infrastructure`, `domain:ordering → order-management`, `domain:routing → order-routing`, `domain:integration → erp-integration`, `domain:catalog → item-catalog`, `domain:customers → customer-binding`, `domain:webhooks → webhook-delivery`, `domain:audit → audit-trail`, `domain:identity-access → access-control`, `app:api → api`, `app:worker → worker`.

## 5. Screen mapping & UI gaps
Ten designed screens map to reseller (C-17) and operator (C-18) apps and their backend components (table in `component-dependency.md`, Section 4). **Not-yet-designed** surfaces to design later in the existing style: sign in, new-order form + line editor, item catalog, mapping viewer. Reseller screens structurally exclude ERP identity (FR-19/AC-02).

## 6. How key requirements are met
| Requirement | Design mechanism |
|---|---|
| No ERP identity to resellers (FR-19/AC-02) | Separate reseller DTOs + reseller GraphQL schema (C-01, C-15); ErpGateway isolates ERP detail; error sanitization to canonical codes |
| Tenant isolation (FR-01/AC-01) | Immutable TenantContext (C-05) from token claim; object-level checks; deny-by-default |
| One order = one ERP (FR-16/17, AC-03) | RoutingService resolves at Validated and persists an immutable decision (C-08) |
| Mixed-ERP rejection (FR-18/AC-04) | RoutingService raises a reseller-safe rejection before any ERP call |
| Guaranteed delivery (FR-29, AC-07/16) | Outbox + SQS FIFO + retry/backoff + DLQ; idempotent DeliveryOrchestrator (C-03, C-11) |
| Reads during outage (FR-31/AC-10) | Queries served from PostgreSQL read model; no ERP call on read path (C-07, C-12) |
| Add an ERP in days (FR-24..27, AC-12) | ErpAdapter seam + MappingEngine + ConnectionRegistry + ConformanceRunner (C-10); API-first for future US-F7 |
| Bindings/ownership uniqueness (FR-20/22, AC-05/06) | BindingService + ItemOwnershipService with DB uniqueness constraints (C-09, C-08b) |
| Audit (FR-38) | Append-only AuditService on every admin mutation (C-14) |

## 7. Extension compliance at this stage
- **Security (blocking)**: isolation, token validation, input validation, DTO separation, audit, least-privilege IAM all have a home component (C-04/05/14/15). No design-level blocking finding. Detailed control verification continues in NFR/Infrastructure Design and Code Generation.
- **Resiliency (blocking)**: durable queue/DLQ (C-03), retry/idempotency (C-11), timeouts/circuit breakers/bulkheads (C-10), health/metrics (C-06), degraded-mode reads (C-12). Managed Cognito/SQS/SNS are multi-AZ (RESILIENCY-08; O-10 closed). No blocking finding.
- **PBT (blocking, full)**: property-bearing components identified (mapping round-trip C-10, idempotency C-11/12, routing determinism C-08, uniqueness C-09/08b, lifecycle state machine C-07); formal property identification (PBT-01) happens in Functional Design. No blocking finding.

## 8. Open items relevant to design
- **O-08** webhook signing scheme / delivery-log retention → detail in the Webhooks unit (C-13).
- **O-09** order update/cancel rules per state → Functional Design of Ordering (C-07).
- **O-07** whether "Sent to ERP" wording is shown to resellers → Ordering/UI.
- **O-04** whether each reseller already has an ERP customer record → Customers & Bindings (C-09).
- **US-036 note**: operator runtime mapping editing deferred (Q2=B); MVP ships a read-only mapping viewer.

## 9. Suggested units (preview for Units Generation)
Platform Core & Contracts; ERP Integration (adapters + mapping + conformance); Ordering & Routing & Delivery; Reseller API & Webhooks; Reseller Web App; Operator Admin (API + Web App); Identity & Access (Cognito integration); Platform/Infra & Developer Enablement. Formalized and sequenced in Units Generation.
