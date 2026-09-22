# Personas — ERP & Supply Chain Order Portal

## Persona 1: Client Order User (external)

- **Name / Archetype**: "Priya" — Operations/Procurement user at a client organization
- **Type**: External client user (single organization membership)
- **Goals**:
  - Place orders quickly without needing to know which ERP fulfills them
  - Check product catalog and inventory availability before ordering
  - Track order status through its full lifecycle
  - Correct problems (resubmit failed orders, cancel, amend) when needed
- **Context & Characteristics**:
  - Belongs to exactly one client tenant; only sees that tenant's data
  - Business user, not technical; expects an ERP-agnostic experience
  - Authenticates with username/password + MFA
- **Pain Points Addressed**:
  - Today would need to know/interact with specific ERP systems directly
  - No single place to track an order end-to-end across ERP boundaries
- **Success Criteria**:
  - Can place, track, and correct orders entirely through the portal
- **Maps to Epics**: E1 (Access), E2 (Order Placement), E3 (Catalog & Inventory), E4 (Lifecycle Tracking), E5 (Corrective Actions)

## Persona 2: Platform Administrator (internal)

- **Name / Archetype**: "Sam" — Integration/Platform administrator operating the portal
- **Type**: Internal administrator
- **Goals**:
  - Register ERP instances (ERP Next, Odoo) and their connection details
  - Define content-based routing rules that send orders to the right instance
  - Manage canonical↔ERP field/value mappings so a new ERP is onboarded in days
  - Verify routing and mapping behavior via a minimal internal UI
- **Context & Characteristics**:
  - Technically capable; understands ERP APIs and the canonical model
  - Uses a minimal internal admin UI (not a full self-service wizard in MVP)
- **Pain Points Addressed**:
  - Onboarding a new ERP historically takes months of custom connector work
- **Success Criteria**:
  - Can add/adjust ERP instances, routing rules, and mappings without changing core code
- **Maps to Epics**: E6 (Routing & Mapping Configuration)

---

## Persona-to-Epic Map

| Epic | Client Order User | Platform Administrator |
|---|---|---|
| E1 Client Access & Authentication | ✔ | (also authenticates) |
| E2 Order Placement | ✔ | |
| E3 Catalog & Inventory Lookup | ✔ | |
| E4 Order Lifecycle Tracking | ✔ | |
| E5 Order Corrective Actions | ✔ | |
| E6 Routing & Mapping Configuration | | ✔ |
