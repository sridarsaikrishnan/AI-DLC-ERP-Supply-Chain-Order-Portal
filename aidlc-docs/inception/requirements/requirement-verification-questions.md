# Requirements Clarification Questions — ERP & Supply Chain Order Portal

Please answer every question below by filling in the letter after the `[Answer]:` tag. If none of the options fit, use the "Other" option and describe your answer.

---

## SECTION A: Scope & ERP Targets

## Question A1
You mentioned SAP, ERP Next, and Odoo, but also said "start small, proving it works with two ERPs." Which two ERP systems should be the initial build target?

A) SAP and ERP Next

B) SAP and Odoo

C) ERP Next and Odoo

D) All three from day one (no phased ERP rollout)

E) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question A2
Each ERP can have multiple instances (e.g., multiple SAP tenants). What distinguishes one instance from another in your environment?

A) Different customers/clients each have their own dedicated ERP instance

B) Different business units/regions within the same client share ERP types but run separate instances

C) Both A and B apply (multi-tenant AND multi-region/business-unit)

D) Instances are purely for environment separation (dev/test/prod), not real business segmentation

E) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question A3
What are the four kinds of business data/objects the portal must support end to end (e.g., Sales Orders, Purchase Orders, Inventory/Stock levels, Product Catalog/Pricing, Invoices, Shipment/ASN, Customer Master)? Please list your four, or pick the closest bundle below.

A) Sales Orders, Order Status/Tracking, Product Catalog, Inventory Availability

B) Sales Orders, Purchase Orders, Invoices, Shipment/ASN

C) Sales Orders, Inventory Availability, Pricing, Customer Master

D) Not yet decided — recommend a standard starter bundle

E) Other (please list your exact four after [Answer]: tag below)

[Answer]: A

## Question A4
Who are the "external clients" placing orders through this portal?

A) The company's own B2B customers/distributors ordering from the company's ERP-backed operations

B) Third-party partners/vendors who need to place orders into the company's various ERP systems on behalf of end customers

C) Internal business users across subsidiaries, treated as "external" to each ERP instance

D) A mix of B2B customers and partner organizations

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## SECTION B: Order Management Workflow & Routing

## Question B1
How should the portal determine which ERP instance an incoming order gets routed to?

A) Based on the client's account/tenant configuration (each client is pre-mapped to one ERP instance)

B) Based on order content (e.g., product line, region, warehouse) evaluated at submission time

C) Based on a combination of client mapping and order content rules

D) Client explicitly selects the target ERP/instance in the portal UI

E) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question B2
What should happen to an order workflow after it's routed to the target ERP?

A) Fire-and-forget — submit and only track final ERP acknowledgment/error

B) Full lifecycle tracking — the portal tracks order status changes (submitted, accepted, processing, shipped, invoiced, etc.) as the ERP updates them

C) Full lifecycle tracking plus the portal can trigger corrective actions (resubmit, cancel, amend) back into the ERP

D) Not yet decided — recommend based on best practice

E) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question B3
"Seamlessly route requests... without having to write integrators/connectors" — what should make this possible for a NEW ERP going forward?

A) A configuration-driven mapping layer (schema mapping + endpoint config, no custom code) that admins set up via UI/config files

B) A common canonical data model with adapter modules that are thin and standardized (still some code, but templated/generated)

C) Pre-built certified connectors shipped for known ERPs (SAP, ERP Next, Odoo, etc.) plus a config layer for instance-specific details

D) Fully AI-assisted connector generation from ERP API specs (OpenAPI/WSDL) with human review

E) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question B4
What are the primary integration protocols/APIs each ERP instance exposes today (or should the portal assume)?

A) REST/OData APIs (e.g., SAP OData services, Odoo XML-RPC/JSON-RPC, ERPNext REST API)

B) SOAP/RFC/IDoc-style interfaces (traditional SAP integration)

C) A mix depending on ERP — REST for ERPNext/Odoo, RFC/IDoc/OData for SAP

D) Not yet decided — recommend based on best practice per ERP

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## SECTION C: Growth Path & Extensibility

## Question C1
You said the goal is for "adding the next ERP to take days, not months." What's the MVP boundary — i.e., what should NOT be required to build for THIS first release?

A) No self-service ERP onboarding UI yet — a developer/admin still edits config or writes a small adapter, but no custom integration code plumbing

B) No automated cross-system workflows yet (e.g., auto-sync inventory across ERPs) — order routing only

C) No multi-instance load balancing/failover yet — single instance per ERP type is fine for MVP

D) All of the above should be deferred past MVP

E) Other (please describe after [Answer]: tag below)

[Answer]: adding the next ERP should be dynamic. we shouldnt be required to spent months if we have the new requirement of additional ERP

## Question C2
For the later "easier setup by customers" phase, what does self-service onboarding of a new ERP instance look like?

A) A wizard where an admin enters connection details (URL, credentials, ERP type) and the system auto-discovers or maps fields

B) An admin uploads/selects a mapping template (canonical field to ERP field) via UI, no discovery needed

C) Full API-spec ingestion (upload OpenAPI/WSDL) and the system generates the adapter automatically

D) Not a priority right now — just note it as a future direction in the design

E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question C3
For "automated workflows between systems" (mentioned as a future goal), what's an example of the kind of cross-system automation you have in mind?

A) Inventory sync — stock changes in one ERP reflected/reserved in another automatically

B) Order fallback/failover — if one ERP instance is down, route to another instance or queue for retry

C) Cross-ERP reporting/aggregation of order and fulfillment data

D) Not yet defined — just capture as a future extensibility requirement

E) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## SECTION D: Non-Functional & Operational Context

## Question D1
What scale should the MVP be designed to handle (orders/day across all clients)?

A) Low volume — tens to low hundreds of orders/day (pilot/proof of concept)

B) Moderate volume — hundreds to low thousands of orders/day

C) High volume — tens of thousands+ orders/day, needs to be designed for scale from day one

D) Not yet known — design for moderate volume with headroom to scale

E) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question D2
How should external clients authenticate to the portal?

A) Standard username/password with MFA option

B) OAuth2/OIDC (SSO) integration with client identity providers

C) API keys for programmatic/B2B integration clients (no human UI login)

D) A mix — UI users via OIDC/SSO, programmatic clients via API keys

E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question D3
Where should this system be deployed?

A) AWS cloud (specify preferred services if you have any in mind in "Other")

B) Azure cloud

C) On-premises / private data center

D) Not yet decided — recommend based on best practice

E) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question D4
What are your expectations for data residency/multi-tenancy isolation between different clients' order data?

A) Strict isolation required — client data must never be visible or queryable across tenants (e.g., separate schemas/DB-level isolation)

B) Logical isolation sufficient — row-level tenant filtering in a shared database is acceptable

C) Not a concern for MVP — revisit later

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## SECTION E: Extension Opt-Ins

## Question E1: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question E2: Resiliency Extensions
Should the resiliency baseline be applied to this project?

**What this extension is.** Enabling it applies a set of directional, design-time best practices for building resilient systems, derived from the AWS Well-Architected Framework (Reliability Pillar) and resilience-review guidance. It steers requirements, design, and code toward fault tolerance, high availability, observability, and recoverability.

**What this extension is NOT.** Enabling it does not make your workload production-ready, nor certify any availability, RTO, or RPO target. It's a starting point, not a substitute for a formal AWS Well-Architected Review.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question E3: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components — this portal's schema mapping/routing logic is a strong candidate)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

Once you've filled in all `[Answer]:` tags, let me know and I'll proceed to generate the requirements document.
