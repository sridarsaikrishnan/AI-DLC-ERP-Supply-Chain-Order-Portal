# Components — ERP & Supply Chain Order Portal

**Architecture**: Modular monolith with clean module boundaries and an internal async queue, designed so modules can be extracted into microservices later. Coarse-grained module groups (future extraction seams): **Portal/Order**, **Integration**, **Admin/Config**, **Identity**.

Each component below lists its purpose, responsibilities, and interface (external boundary). Detailed business rules are defined later in Functional Design (per-unit).

---

## Module Group: Identity

### C1. Identity & Access
- **Purpose**: Authenticate client users and enforce tenant scoping and authorization.
- **Responsibilities**:
  - Username/password authentication with MFA
  - Issue and validate session/access tokens
  - Resolve the caller's tenant and roles
  - Authorize sensitive actions (corrective actions, admin operations)
- **Interface**: `authenticate`, `verifyMfa`, `resolveContext(token) -> {userId, tenantId, roles}`, `authorize(context, action, resource)`

---

## Module Group: Portal/Order

### C2. Order Intake API (Portal API)
- **Purpose**: Client-facing entry point for order operations and lookups.
- **Responsibilities**:
  - Accept canonical order submissions and validate against the canonical model
  - Expose catalog/inventory lookups, order list/detail, and corrective actions
  - Enqueue submission and corrective-action work (async)
  - Enforce tenant scoping on all reads/writes
- **Interface**: `submitOrder`, `getOrder`, `listOrders`, `browseCatalog`, `checkAvailability`, `resubmitOrder`, `cancelOrder`, `amendOrder`

### C3. Canonical Model
- **Purpose**: ERP-agnostic domain model for the four business data types.
- **Responsibilities**:
  - Define canonical schemas: `CanonicalSalesOrder`, `CanonicalOrderStatus`, `CanonicalProduct`, `CanonicalInventory`
  - Provide validation of canonical objects
  - Serve as the contract between Portal/Order and Integration
- **Interface**: schema/type definitions + `validate(canonicalObject) -> ValidationResult`

### C4. Order Lifecycle Manager
- **Purpose**: Own the order lifecycle state and status history.
- **Responsibilities**:
  - Maintain lifecycle states: Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled, Amended
  - Apply state transitions from submission outcomes and ingested ERP updates
  - Record status history with timestamps
  - Orchestrate corrective actions (resubmit/cancel/amend) via the Integration group
- **Interface**: `recordSubmission`, `applyStatusUpdate`, `getStatus`, `getHistory`, `initiateCorrectiveAction`

---

## Module Group: Integration

### C5. Routing Engine
- **Purpose**: Select the target ERP instance for an order based on content.
- **Responsibilities**:
  - Evaluate ordered, first-match-wins content-based rules
  - Return the matched ERP instance, or a explicit "no route matched" rejection
  - Enforce rule precedence deterministically
- **Interface**: `route(canonicalOrder, tenantContext) -> RoutingResult{instanceId | NoMatch}`

### C6. Mapping / Translation Engine
- **Purpose**: Translate between canonical objects and ERP-native payloads using a stored mapping DSL.
- **Responsibilities**:
  - Load mapping definitions (DSL) for a given ERP instance and data type
  - Transform canonical -> ERP-native (outbound) and ERP-native -> canonical (inbound)
  - Report unmapped required fields
- **Interface**: `toErp(canonicalObject, instanceId) -> ErpPayload`, `fromErp(erpPayload, instanceId) -> CanonicalObject`, `validateMapping(instanceId) -> MappingReport`

### C7. ERP Adapter Layer
- **Purpose**: Thin, per-ERP adapters that speak each ERP's protocol.
- **Responsibilities**:
  - Implement a common adapter interface for ERP Next and Odoo
  - Handle protocol/transport specifics and credential use per instance
  - Submit orders, fetch status, and send corrective actions to the ERP
  - New ERP = new thin adapter + configuration/mapping (no core changes)
- **Interface** (common `ErpAdapter`): `submit(erpPayload, instanceConn)`, `fetchStatus(erpRef, instanceConn)`, `sendCorrectiveAction(action, erpRef, instanceConn)`, `checkConnectivity(instanceConn)`

### C8. Async Work Queue & Workers
- **Purpose**: Decouple client requests from ERP interactions.
- **Responsibilities**:
  - Enqueue submission, corrective-action, and status-fetch jobs
  - Process jobs via workers (route -> map -> adapter call -> update lifecycle)
  - Support retry/redelivery of failed jobs (basic; full resiliency deferred)
  - Poll ERPs for status and/or receive webhook callbacks
- **Interface**: `enqueue(job)`, worker handlers (`processSubmission`, `processCorrectiveAction`, `processStatusSync`), `receiveWebhook(payload)`

---

## Module Group: Admin/Config

### C9. Admin Configuration
- **Purpose**: Minimal internal UI/API to configure the platform.
- **Responsibilities**:
  - Register/manage ERP instances (type, connection details reference)
  - Manage content-based routing rules (ordered, with fallback)
  - Manage mapping DSL definitions per instance/data type
  - Provide a read/verify view of current configuration and connectivity checks
- **Interface**: `registerInstance`, `updateInstance`, `defineRoutingRule`, `orderRoutingRules`, `defineMapping`, `getConfiguration`, `checkInstanceConnectivity`

---

## Cross-Cutting: Persistence

### C10. Persistence / Data Store
- **Purpose**: Tenant-scoped storage for orders, status history, configuration, and mappings.
- **Responsibilities**:
  - Persist orders, status history, ERP instances, routing rules, mapping definitions
  - Enforce row-level tenant isolation on tenant-owned data
  - Provide repositories to other components
- **Interface**: repository interfaces per aggregate (`OrderRepository`, `StatusHistoryRepository`, `InstanceRepository`, `RoutingRuleRepository`, `MappingRepository`), all tenant-aware where applicable

---

## Component Summary Table

| ID | Component | Module Group | Primary Consumers |
|---|---|---|---|
| C1 | Identity & Access | Identity | C2, C9 |
| C2 | Order Intake API | Portal/Order | Client users |
| C3 | Canonical Model | Portal/Order | C2, C4, C5, C6 |
| C4 | Order Lifecycle Manager | Portal/Order | C2, C8 |
| C5 | Routing Engine | Integration | C8 |
| C6 | Mapping / Translation | Integration | C8 |
| C7 | ERP Adapter Layer | Integration | C8 |
| C8 | Async Work Queue & Workers | Integration | C2, C4 |
| C9 | Admin Configuration | Admin/Config | Administrators |
| C10 | Persistence / Data Store | Cross-cutting | C2, C4, C5, C6, C9 |
