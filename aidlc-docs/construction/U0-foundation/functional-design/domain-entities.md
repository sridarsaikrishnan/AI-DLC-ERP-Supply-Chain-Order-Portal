# Domain Entities — U0 Platform Foundation

Technology-agnostic domain entities shared across all units. No DB/framework specifics (those come in NFR Requirements). Types are conceptual.

---

## Canonical Domain

### CanonicalSalesOrder (Q1=A)
- `orderId` (portal-generated) — identity
- `tenantId` — owning tenant (required)
- `clientReference` — client's own order reference
- `orderDate`
- `shipTo` — address value object (name, lines, city, region, postalCode, country)
- `currency` — ISO currency code
- `notes` — free-form text (optional)
- `lineItems[]` — one or more `CanonicalOrderLine`
- `lifecycleState` — current state (see CanonicalOrderStatus)
- **Relationships**: belongs to Tenant; has many CanonicalOrderLine; references CanonicalProduct via productKey.

### CanonicalOrderLine
- `lineId`
- `productKey` — portal-side product key (Q2=A)
- `quantity`
- `unitOfMeasure`
- `requestedDate` (optional)

### CanonicalOrderStatus
- `orderId`
- `state` — one of: Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled, Amended
- `erpReference` (optional) — ERP-side id once accepted
- `reason` (optional) — failure/rejection reason
- `occurredAt` — timestamp
- **Relationships**: a sequence of these forms the order's status history.

### CanonicalProduct (Q2=A)
- `productKey` — portal-side canonical key (identity)
- `name`
- `description` (optional)
- `attributes` — key/value bag (optional)
- **Note**: native ERP product IDs live in mapping, not here.

### CanonicalInventory
- `productKey`
- `availableQuantity`
- `unitOfMeasure`
- `asOf` — timestamp of the availability snapshot
- `instanceId` (optional) — which ERP instance sourced it

---

## Tenant & Security

### Tenant
- `tenantId` — identity
- `name`
- `status` (active/suspended)

### SecurityContext (value object, propagated per request/job)
- `userId`
- `tenantId`
- `roles[]`
- **Rule**: required to access tenant-owned repositories (see business-rules.md).

---

## Configuration Domain (owned by U0; authored by U4, consumed by U3)

### ErpInstance
- `instanceId` — identity
- `erpType` — enum: ERP_NEXT, ODOO
- `displayName`
- `connectionRef` — reference/handle to connection details & credentials (actual secrets not stored in domain model)
- `status` (active/inactive)

### RoutingRule (Q6=A)
- `ruleId` — identity
- `orderIndex` — integer; lower evaluated first (deterministic precedence)
- `conditions[]` — list of `RoutingCondition`, all ANDed
- `targetInstanceId` — ERP instance selected when all conditions match
- `enabled` — boolean

### RoutingCondition
- `field` — canonical order field path (e.g., `shipTo.region`, `lineItems.productKey`)
- `operator` — enum: EQUALS, NOT_EQUALS, IN, CONTAINS, GT, LT
- `value` — comparison value(s)

### MappingDefinition (Q5=C hybrid)
- `mappingId` — identity
- `instanceId` — ERP instance this mapping applies to
- `dataType` — enum: SALES_ORDER, ORDER_STATUS, PRODUCT, INVENTORY
- `direction` — enum: TO_ERP, FROM_ERP (or BIDIRECTIONAL with per-entry direction)
- `fieldEntries[]` — list of `MappingEntry` (structured field maps for the common case)
- `expressions[]` — optional list of `MappingExpression` (text expressions for complex transforms)

### MappingEntry
- `sourcePath` — path in source object
- `targetPath` — path in target object
- `valueMap` (optional) — discrete value translations (e.g., status code A -> "Accepted")

### MappingExpression
- `targetPath`
- `expression` — text expression evaluated by U3's mapping engine

---

## Async Job Domain

### Job (Q4=A)
- `jobId` — identity
- `type` — enum: SUBMISSION, CORRECTIVE_ACTION, STATUS_SYNC
- `payloadRef` — reference to the work payload (e.g., orderId + action)
- `tenantId` — carried for context propagation
- `attemptCount` — integer (bounded retry)
- `maxAttempts` — integer
- `status` — enum: PENDING, IN_PROGRESS, SUCCEEDED, FAILED
- `dedupeKey` — key used for idempotent handling (e.g., orderId + action + version)
- `createdAt`, `updatedAt`

---

## Entity Relationship Overview (text)
```
Tenant 1---* CanonicalSalesOrder 1---* CanonicalOrderLine
CanonicalSalesOrder 1---* CanonicalOrderStatus (history)
CanonicalProduct 1---* CanonicalInventory (by productKey)
ErpInstance 1---* RoutingRule (targetInstanceId)
RoutingRule 1---* RoutingCondition
ErpInstance 1---* MappingDefinition
MappingDefinition 1---* MappingEntry
MappingDefinition 1---* MappingExpression (optional)
Job references CanonicalSalesOrder via payloadRef; carries tenantId
```
