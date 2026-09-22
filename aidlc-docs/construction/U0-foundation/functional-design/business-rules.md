# Business Rules — U0 Platform Foundation

Technology-agnostic rules the foundation enforces for all units.

---

## BR-1: Canonical Validation Rules

### BR-1.1 CanonicalSalesOrder
- `tenantId` is required and must reference an active Tenant.
- `clientReference` is required and non-empty.
- At least one `lineItem` is required.
- `currency` must be a valid ISO currency code.
- `shipTo` must include at least name, one address line, city, and country.

### BR-1.2 CanonicalOrderLine
- `productKey` required and must resolve to a known CanonicalProduct.
- `quantity` must be > 0.
- `unitOfMeasure` required.
- `requestedDate`, if present, must not be in the past.

### BR-1.3 CanonicalOrderStatus
- `state` must be one of the allowed lifecycle states.
- `occurredAt` required.
- `erpReference` required once state is Accepted or later (Processing/Shipped/Invoiced).

## BR-2: Tenant Isolation Rules (Q3=C)
- **BR-2.1 Automatic filter**: Every query against a tenant-owned repository is automatically constrained by the current `SecurityContext.tenantId`. Developers cannot issue an unfiltered tenant-owned query through the standard repository API.
- **BR-2.2 Fail-closed**: If no `SecurityContext` (or no tenantId) is present when accessing a tenant-owned repository, the operation is rejected with an authorization error — never defaults to "all tenants".
- **BR-2.3 Cross-tenant access**: A request for a record whose `tenantId` differs from the context is treated as not found (no existence leak).
- **BR-2.4 Config data**: ErpInstance, RoutingRule, MappingDefinition are platform config (not tenant-owned); access is governed by admin authorization (U1/U4), not tenant filtering.

## BR-3: Async Job Rules (Q4=A — at-least-once + idempotency)
- **BR-3.1 Delivery**: Jobs are delivered at least once. A job may be processed more than once on retry.
- **BR-3.2 Bounded retry**: A failed job is retried up to `maxAttempts`. After exhaustion, it is marked FAILED (no infinite retry).
- **BR-3.3 Idempotency**: Handlers must be idempotent, keyed by `dedupeKey`. Re-processing a job with the same dedupeKey must not create duplicate side effects (e.g., duplicate ERP submissions).
- **BR-3.4 Context propagation**: A job carries `tenantId`; workers reconstruct a `SecurityContext` from it so tenant isolation (BR-2) holds during async processing.

## BR-4: Configuration Rules
- **BR-4.1 RoutingRule precedence**: Rules are evaluated in ascending `orderIndex`; the first rule whose conditions all match (AND) selects `targetInstanceId`. (First-match-wins.)
- **BR-4.2 No match**: If no enabled rule matches, routing returns NoMatch (caller rejects the order — see U2/U3).
- **BR-4.3 Target validity**: A RoutingRule's `targetInstanceId` must reference an active ErpInstance.
- **BR-4.4 Mapping completeness**: For a given (instanceId, dataType, direction), required canonical fields should have a MappingEntry or MappingExpression; unmapped required fields are reported (warning surfaced to admin in U4).
- **BR-4.5 Value maps**: A MappingEntry.valueMap, if present, must define a translation for every discrete source value expected; unknown values are flagged at runtime.

## BR-5: Referential Integrity
- Deleting/deactivating an ErpInstance that is referenced by enabled RoutingRules is blocked or warned (prevents orphaned routing targets).
- MappingDefinition must reference an existing ErpInstance.
