# Requirements — ERP & Supply Chain Order Portal

## Intent Analysis Summary

- **User Request**: Build an application portal that lets external clients place and manage orders against multiple ERP systems (SAP, ERP Next, Odoo), where each ERP can run multiple instances. The portal drives an order-management workflow and routes each request to the correct ERP instance without hand-writing bespoke integrators/connectors. Start small (two ERPs, four business data types) and grow toward self-service ERP onboarding and cross-system automation, so adding the next ERP takes days, not months.
- **Request Type**: New Project (greenfield)
- **Scope Estimate**: Cross-system (a routing/integration platform spanning multiple external ERP systems)
- **Complexity Estimate**: Complex (multi-tenant, multi-ERP, workflow lifecycle, extensibility goals)
- **Requirements Depth**: Comprehensive

## MVP Scope Statement

The MVP is an intentional proof-of-concept (see quality posture below). It proves the portal works against **two ERPs — ERP Next and Odoo** — for **four business data types** — **Sales Orders, Order Status/Tracking, Product Catalog, and Inventory Availability**. It routes orders to the correct ERP instance using a **configuration-driven canonical mapping layer** (no AI-assisted connector generation in MVP). The architecture is deliberately designed so a future ERP is added by authoring configuration/mapping (days of effort), not by re-architecting the platform.

### Explicitly In Scope (MVP)
- Web portal for external clients to place and track orders
- Canonical (ERP-agnostic) data model for the four business data types
- Configuration-driven mapping between the canonical model and each ERP's API
- Content-based routing to the correct ERP instance
- Full order lifecycle tracking, including corrective actions (resubmit, cancel, amend) back into the ERP
- Support for multiple instances per ERP type (multi-tenant clients AND multi-region/business-unit instances)
- Client authentication via username/password with MFA
- Logical multi-tenant data isolation (row-level tenant filtering)

### Explicitly Out of Scope (MVP — future direction)
- AI-assisted connector generation from API specs (documented as future capability)
- Self-service ERP onboarding wizard for admins (auto-discovery/field mapping)
- Automated cross-system workflows, specifically order fallback/failover between ERP instances
- Partner/programmatic (API-key) client access — MVP is a single client org type, human users only
- SAP adapter (deferred; ERP Next + Odoo chosen for MVP)
- Hardened security and resiliency baselines (deferred to a later phase)

---

## Functional Requirements

### FR-1: Client Order Placement
- **FR-1.1**: External clients shall place orders for the supported business data types through a web portal UI.
- **FR-1.2**: The portal shall present an ERP-agnostic (canonical) order entry experience; clients do not need to know which ERP fulfills their order.
- **FR-1.3**: The portal shall validate order data against the canonical model before submission.

### FR-2: Supported Business Data Types
The portal shall support end-to-end handling of these four canonical business objects:
- **FR-2.1**: Sales Orders — create and submit.
- **FR-2.2**: Order Status/Tracking — read current status and status history.
- **FR-2.3**: Product Catalog — browse/lookup products available for ordering.
- **FR-2.4**: Inventory Availability — check stock/availability prior to or during ordering.

### FR-3: ERP Routing
- **FR-3.1**: The portal shall route each order to the correct target ERP instance based on **order content** (e.g., product line, region, warehouse) evaluated at submission time.
- **FR-3.2**: Routing rules shall be configuration-driven and modifiable without code changes.
- **FR-3.3**: The portal shall support multiple instances per ERP type and select the specific instance per the routing rules.
- **FR-3.4**: If no routing rule matches an order, the portal shall reject the order with a clear, actionable error.

### FR-4: Canonical Model & Configuration-Driven Mapping
- **FR-4.1**: The portal shall define a canonical data model for each of the four business data types, independent of any specific ERP.
- **FR-4.2**: The portal shall translate between the canonical model and each ERP's native schema using configuration/mapping definitions (field mapping, value mapping, endpoint configuration).
- **FR-4.3**: Adding support for a new ERP or a new instance shall be achievable by authoring configuration/mapping plus a thin adapter, without modifying the core routing/workflow engine.
- **FR-4.4**: Mapping configuration shall support the two MVP ERPs: ERP Next and Odoo.

### FR-5: Order Lifecycle Management
- **FR-5.1**: The portal shall track full order lifecycle status as the ERP updates it (e.g., submitted, accepted, processing, shipped, invoiced).
- **FR-5.2**: The portal shall reflect ERP-side status changes back to the client view.
- **FR-5.3**: The portal shall allow authorized clients to trigger corrective actions back into the ERP: resubmit, cancel, and amend an order.
- **FR-5.4**: The portal shall record an audit trail of order state transitions and corrective actions.

### FR-6: Multi-Instance / Multi-Tenancy
- **FR-6.1**: The portal shall support ERP instances that vary by customer/client (multi-tenant) and by business unit/region (multi-instance within a client).
- **FR-6.2**: Each order and its data shall be associated with the owning client tenant.
- **FR-6.3**: Client users shall only see data belonging to their own tenant (logical/row-level isolation).

### FR-7: Authentication & Authorization
- **FR-7.1**: External client users shall authenticate with username/password.
- **FR-7.2**: The portal shall support multi-factor authentication (MFA).
- **FR-7.3**: Each user shall belong to exactly one client organization (single org type for MVP).
- **FR-7.4**: Authorization shall restrict corrective actions (resubmit/cancel/amend) to appropriately permitted users.

### FR-8: Error Handling & Submission Feedback
- **FR-8.1**: The portal shall surface ERP acknowledgment and error responses to the client in an understandable form.
- **FR-8.2**: Failed submissions shall be retryable by the user (aligned with FR-5.3 resubmit).

---

## Non-Functional Requirements

### NFR-1: Scale & Performance
- **NFR-1.1**: The MVP shall be designed for moderate volume — hundreds to low thousands of orders/day across all clients.
- **NFR-1.2**: The architecture shall have headroom to scale beyond MVP volume without redesign of the core model.

### NFR-2: Extensibility (Primary Architectural Driver)
- **NFR-2.1**: Adding a new ERP shall take on the order of days, not months, achieved via the canonical-model + configuration-driven mapping + thin adapter pattern.
- **NFR-2.2**: The core routing and workflow engine shall be decoupled from ERP-specific details.
- **NFR-2.3**: The design shall leave clear extension points for future AI-assisted connector generation, self-service onboarding wizard, and cross-system automation (fallback/failover) — designed-for but not built in MVP.

### NFR-3: Multi-Tenancy & Data Isolation
- **NFR-3.1**: Tenant data isolation shall be enforced by row-level tenant filtering in a shared datastore (logical isolation).
- **NFR-3.2**: No client shall be able to read or query another client's order data.

### NFR-4: Integration Protocols
- **NFR-4.1**: The MVP shall integrate with ERP Next and Odoo over their standard APIs (recommended: ERP Next REST API; Odoo XML-RPC/JSON-RPC). Final protocol choice per ERP to be confirmed during Application/Functional Design.
- **NFR-4.2**: The adapter layer shall abstract protocol differences so the core engine is protocol-agnostic.

### NFR-5: Observability & Auditability
- **NFR-5.1**: The portal shall log order submissions, routing decisions, ERP responses, and state transitions sufficiently to trace any order end-to-end.

### NFR-6: Deployment
- **NFR-6.1**: Deployment target is not yet decided; a recommendation will be made during Infrastructure Design. The application shall be built to be deployment-target-agnostic where reasonable (containerizable).

### NFR-7: Quality Posture (MVP)
- **NFR-7.1**: This is an intentional proof-of-concept MVP. The Security baseline and Resiliency baseline extensions are NOT enforced for MVP; they are to be applied in a later hardening phase before production use against real ERP systems.
- **NFR-7.2**: Property-Based Testing is applied in **partial** mode — for pure functions and serialization round-trips (notably the canonical↔ERP mapping/transformation logic).

---

## Assumptions & Decisions Log

- **Two ERPs for MVP**: ERP Next and Odoo (A1=C). SAP deferred.
- **Instances vary by both tenant and business unit/region** (A2=C).
- **Four data types**: Sales Orders, Order Status/Tracking, Product Catalog, Inventory Availability (A3=A).
- **Routing by order content** at submission time (B1=B).
- **Full lifecycle tracking + corrective actions** back into ERP (B2=C).
- **MVP uses config-driven canonical mapping; no AI generation in MVP** (Clarification 1=C). AI-assisted generation is a documented future capability.
- **Access model for MVP**: username/password + MFA, single client org type; partner/programmatic (API-key) access deferred (Clarification 2=C, overriding original A4=D for MVP scope).
- **Self-service onboarding** = future admin wizard with connection details + auto-discovery (C2=A) — future direction only.
- **Cross-system automation** = order fallback/failover (C3=B) — future direction only.
- **Moderate volume** target (D1=B).
- **Logical/row-level tenant isolation** (D4=B).
- **Deployment target undecided** — recommend later (D3=D).
- **Extensions**: Security OFF (E1=B), Resiliency OFF (E2=B), PBT Partial (E3=B). Lightweight PoC posture confirmed (Clarification 3=A).

---

## Key Requirements Summary

The core of this system is an **extensible, configuration-driven order-routing platform** with a **canonical data model** at its center. Clients place orders in ERP-agnostic terms; a content-based router picks the correct ERP instance; a mapping/adapter layer translates canonical data to each ERP's API; and the platform tracks the full order lifecycle with corrective actions. The dominant architectural driver (NFR-2) is that adding the next ERP is a configuration exercise measured in days. Security and resiliency hardening, AI-assisted onboarding, self-service wizards, and cross-system failover are explicitly designed-for but deferred beyond MVP.
