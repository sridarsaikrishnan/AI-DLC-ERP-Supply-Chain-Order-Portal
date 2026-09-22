# Component Methods — ERP & Supply Chain Order Portal

Method signatures with high-level purpose and I/O types. **Detailed business rules are deferred to Functional Design (per-unit, CONSTRUCTION phase).** Types are language-agnostic; concrete types decided at NFR/Construction.

---

## C1. Identity & Access

| Method | Purpose | Input | Output |
|---|---|---|---|
| `authenticate(username, password)` | Verify credentials, begin session | credentials | `AuthChallenge` (MFA required) or `AuthResult` |
| `verifyMfa(challengeId, code)` | Complete MFA step | challenge id, code | `AuthResult` (token) or error |
| `resolveContext(token)` | Resolve caller identity/tenant/roles | token | `SecurityContext{userId, tenantId, roles}` |
| `authorize(context, action, resource)` | Authorization check | context, action, resource ref | `boolean` / decision |

## C2. Order Intake API

| Method | Purpose | Input | Output |
|---|---|---|---|
| `submitOrder(ctx, canonicalOrder)` | Validate + enqueue submission | context, `CanonicalSalesOrder` | `OrderAck{orderId, status=Submitted}` or `ValidationResult` |
| `getOrder(ctx, orderId)` | Fetch one order (tenant-scoped) | context, id | `OrderView` |
| `listOrders(ctx, filter)` | List tenant's orders | context, filter | `OrderView[]` |
| `browseCatalog(ctx, query)` | Search/browse catalog | context, query | `CanonicalProduct[]` |
| `checkAvailability(ctx, productRef)` | Inventory availability | context, product ref | `CanonicalInventory` or unavailable indicator |
| `resubmitOrder(ctx, orderId)` | Trigger resubmit | context, id | `ActionAck` |
| `cancelOrder(ctx, orderId)` | Trigger cancel | context, id | `ActionAck` |
| `amendOrder(ctx, orderId, amendedOrder)` | Trigger amend | context, id, `CanonicalSalesOrder` | `ActionAck` or `ValidationResult` |

## C3. Canonical Model

| Method | Purpose | Input | Output |
|---|---|---|---|
| `validate(canonicalObject)` | Structural + rule validation of canonical object | canonical object | `ValidationResult{valid, errors[]}` |

Schema definitions: `CanonicalSalesOrder`, `CanonicalOrderStatus`, `CanonicalProduct`, `CanonicalInventory`.

## C4. Order Lifecycle Manager

| Method | Purpose | Input | Output |
|---|---|---|---|
| `recordSubmission(orderId, routingResult)` | Set initial state, persist | order id, routing result | `void` |
| `applyStatusUpdate(orderId, canonicalStatus)` | Apply transition from ERP update | order id, `CanonicalOrderStatus` | updated `LifecycleState` |
| `getStatus(orderId)` | Current status | order id | `LifecycleState` |
| `getHistory(orderId)` | Status history | order id | `StatusTransition[]` |
| `initiateCorrectiveAction(orderId, action, payload?)` | Orchestrate resubmit/cancel/amend | order id, action, optional payload | `ActionAck` |

Lifecycle states: Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled, Amended.

## C5. Routing Engine

| Method | Purpose | Input | Output |
|---|---|---|---|
| `route(canonicalOrder, tenantContext)` | Select target ERP instance | canonical order, tenant context | `RoutingResult{instanceId}` or `NoMatch` |
| `evaluateRule(rule, canonicalOrder)` | Evaluate single rule (internal) | rule, order | `boolean` |

Precedence: ordered rules, first-match-wins; `NoMatch` -> caller rejects order (FR-3.4).

## C6. Mapping / Translation Engine

| Method | Purpose | Input | Output |
|---|---|---|---|
| `toErp(canonicalObject, instanceId)` | Canonical -> ERP-native | canonical object, instance id | `ErpPayload` |
| `fromErp(erpPayload, instanceId)` | ERP-native -> canonical | erp payload, instance id | canonical object |
| `validateMapping(instanceId)` | Detect unmapped required fields | instance id | `MappingReport{unmapped[], warnings[]}` |

Mapping represented as a small DSL, loaded per instance + data type.

## C7. ERP Adapter Layer (common `ErpAdapter` interface)

| Method | Purpose | Input | Output |
|---|---|---|---|
| `submit(erpPayload, instanceConn)` | Submit order to ERP | payload, connection | `ErpRef` / ack or error |
| `fetchStatus(erpRef, instanceConn)` | Fetch current ERP status | erp ref, connection | native status payload |
| `sendCorrectiveAction(action, erpRef, instanceConn)` | Cancel/amend/resubmit to ERP | action, erp ref, connection | ack or error |
| `checkConnectivity(instanceConn)` | Health/connectivity probe | connection | `reachable: boolean` |

Implementations for MVP: `ErpNextAdapter`, `OdooAdapter`.

## C8. Async Work Queue & Workers

| Method | Purpose | Input | Output |
|---|---|---|---|
| `enqueue(job)` | Enqueue a unit of work | `Job` | `jobId` |
| `processSubmission(job)` | route -> map -> submit -> record | submission job | `void` (updates lifecycle) |
| `processCorrectiveAction(job)` | map -> adapter action -> record | corrective job | `void` |
| `processStatusSync(job)` | poll/fetch -> map -> applyStatusUpdate | status-sync job | `void` |
| `receiveWebhook(payload)` | Ingest ERP callback -> status update | webhook payload | `void` |

## C9. Admin Configuration

| Method | Purpose | Input | Output |
|---|---|---|---|
| `registerInstance(erpType, connectionRef, meta)` | Register ERP instance | type, connection ref, metadata | `instanceId` or `ValidationResult` |
| `updateInstance(instanceId, changes)` | Update instance | id, changes | `void` |
| `defineRoutingRule(rule)` | Create/update routing rule | rule | `ruleId` |
| `orderRoutingRules(orderedRuleIds)` | Set rule precedence | ordered ids | `void` |
| `defineMapping(instanceId, dataType, mappingDsl)` | Save mapping DSL | id, data type, DSL | `MappingReport` |
| `getConfiguration()` | Read current config | — | `ConfigurationView` |
| `checkInstanceConnectivity(instanceId)` | Connectivity check | id | `reachable: boolean` |

## C10. Persistence / Data Store (repositories)

| Repository | Key Methods | Tenant-Aware |
|---|---|---|
| `OrderRepository` | `save`, `findById`, `findByTenant` | Yes |
| `StatusHistoryRepository` | `append`, `findByOrder` | Yes |
| `InstanceRepository` | `save`, `findById`, `findAll` | No (platform config) |
| `RoutingRuleRepository` | `save`, `findOrdered`, `reorder` | No (platform config) |
| `MappingRepository` | `save`, `findByInstanceAndType` | No (platform config) |
