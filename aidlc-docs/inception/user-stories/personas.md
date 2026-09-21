# Personas — ERP & Supply Chain Order Portal

Four personas, per the approved story plan (Q1). Names are generic archetypes; any sample data in `design/` is fictional and is not reused here. The defining rule of the product is that **reseller-side personas must never see any ERP name, instance, or ERP record ID** (FR-19 / AC-02); only the operator persona may.

---

## P1 — Priya, the Platform Operator (Admin)
- **Role**: Works for the platform operator's organization, which owns the ERP systems. The single administrative persona; onboarding and support are duties within this role.
- **Surface**: The operator admin web UI (the six `Admin*` screens) and the admin GraphQL schema.
- **Goals**:
  - Onboard resellers and issue their API access.
  - Bind each reseller to its existing customer record in the right ERP connection.
  - Keep ERP connections, field mappings, and item ownership healthy.
  - Resolve failures (retrying, rejected, dead-lettered) and item-ownership conflicts.
  - Answer "what happened to this reseller's order" using raw ERP detail.
- **May see**: ERP names, instances, ERP record IDs, raw ERP errors, the audit trail.
- **Must never do**: expose ERP identity to resellers; create/modify ERP customer records in production.
- **Key journeys**: onboard a reseller → create OAuth client → create and verify customer bindings; monitor connection health; triage failed messages; resolve an item owned by two ERPs; review the audit trail.
- **Pain today**: every new ERP or reseller is a bespoke integration project taking months.

---

## P2 — Marco, the Reseller Integrator (machine-to-machine)
- **Role**: A developer at a reseller company who integrates their system with the platform's API.
- **Surface**: The reseller GraphQL API, authenticated via OAuth 2.0 client credentials; webhook endpoints they register.
- **Goals**:
  - Place, read, update, and cancel orders programmatically against one canonical API.
  - Receive reliable status updates via signed webhooks and a delivery log.
  - Integrate once and never worry about which back-end ERP fulfills an order.
- **Must never see**: which ERP or instance serves them, or any ERP record ID — in responses, errors, webhooks, or the delivery log.
- **Key journeys**: authenticate M2M → create an order → poll or receive webhook for status → inspect delivery attempts and replay.
- **Pain today**: each buyer/supplier ERP exposes a different API, format, and auth; integrations are brittle and per-ERP.

---

## P3 — Sofia, the Reseller Business User (web UI)
- **Role**: A non-technical operations user at a reseller company.
- **Surface**: The reseller web UI (`Main`, `OrderDetail`, `DeliveryLog`, `WebhookEndpoints`), authenticated via OIDC authorization code.
- **Goals**:
  - See orders and their current lifecycle status at a glance.
  - Drill into an order's lines, timeline, and delivery outcomes.
  - Understand when something needs attention (retrying, rejected) in plain language.
  - Manage webhook endpoints without developer help.
- **Must never see**: any ERP identity; error messages must be reseller-safe and actionable.
- **Key journeys**: sign in → scan the order list and attention notice → open an order → read the status timeline → check the delivery log.
- **Pain today**: no single, plain-language view of order status across the systems that fulfill them.

---

## P4 — Devin, the Platform Engineer
- **Role**: Engineer on the platform team who extends and operates the platform itself (not an operator admin, not a reseller).
- **Surface**: Configuration and mapping definitions, the conformance test suite, the seed tool, and the containerized local environment.
- **Goals**:
  - Add a new ERP (or a new instance) through configuration, declarative mappings, and fixtures — no bespoke connector code — targeting days, not months.
  - Prove a new/changed ERP integration with a passing conformance suite.
  - Run the whole stack locally with one command and seed fictional data safely on non-production targets only.
- **May see**: everything technical, including ERP identity, in non-production contexts.
- **Key journeys**: define a connection + mappings → run conformance tests against a real Odoo/ERPNext container → seed fictional data → start the local stack.
- **Pain today**: onboarding an ERP means writing and maintaining a dedicated integrator.

---

## Persona → Epic map (summary)
| Persona | Primary epics |
|---|---|
| P1 Platform Operator | Onboarding & Access, Operator Administration, Delivery & Reliability (triage), ERP Integration (ownership) |
| P2 Reseller Integrator | Ordering, Delivery & Reliability, Webhooks & Delivery Log, Routing & Isolation |
| P3 Reseller Business User | Ordering (view), Webhooks & Delivery Log, Routing & Isolation |
| P4 Platform Engineer | ERP Integration & Extensibility, Developer Enablement |
