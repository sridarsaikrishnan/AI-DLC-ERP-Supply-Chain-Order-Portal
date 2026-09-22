# Business Logic Model — U0 Platform Foundation

Technology-agnostic description of the foundation's core processes. These are consumed by U1–U4.

---

## Process 1: Canonical Validation
- **Input**: a canonical object (order/line/status/product/inventory)
- **Logic**: apply the relevant BR-1 rules; collect all violations (do not stop at first).
- **Output**: `ValidationResult { valid: boolean, errors: [{ path, message }] }`
- **Consumers**: U2 (order submission/amend), U4 (mapping validation uses product/field awareness).

## Process 2: Tenant-Scoped Data Access
- **Input**: repository operation + ambient `SecurityContext`
- **Logic** (BR-2):
  1. If tenant-owned repository and no context/tenantId -> reject (fail-closed).
  2. Apply automatic tenantId filter to the query/write.
  3. On single-record fetch, if record.tenantId != context.tenantId -> return not-found.
- **Output**: tenant-safe data or authorization error.
- **Consumers**: all units touching tenant data (primarily U2).

## Process 3: Enqueue Work
- **Input**: a `Job` request (type, payloadRef, tenantId, dedupeKey)
- **Logic**: 
  1. Assign jobId, set status=PENDING, attemptCount=0, maxAttempts=configured default.
  2. Persist and publish to the queue.
- **Output**: jobId.
- **Consumers**: U2 (submission, corrective actions), U3 (status-sync scheduling).

## Process 4: Consume Work (worker host contract)
- **Input**: a delivered `Job`
- **Logic** (BR-3):
  1. Reconstruct `SecurityContext` from job.tenantId.
  2. Mark IN_PROGRESS, increment attemptCount.
  3. Invoke the registered handler for job.type (handler is idempotent by dedupeKey).
  4. On success -> SUCCEEDED. On failure -> if attemptCount < maxAttempts, requeue; else FAILED.
- **Output**: terminal job status; side effects performed by the handler (in U3).
- **Consumers**: U3 workers register handlers (processSubmission, processCorrectiveAction, processStatusSync).

## Process 5: Configuration Resolution
- **Input**: a request for routing rules / mapping definitions / instances
- **Logic**:
  - Routing: return enabled RoutingRules ordered by `orderIndex` (BR-4.1).
  - Mapping: return MappingDefinition for (instanceId, dataType, direction).
  - Instances: return active ErpInstance by id.
- **Output**: config objects for U3 runtime and U4 views.
- **Consumers**: U3 (runtime routing/mapping), U4 (authoring/views).

---

## Cross-Cutting Behaviors
- **No infrastructure choices here**: persistence, queue technology, and framework are decided in NFR Requirements / Infrastructure Design.
- **Determinism**: routing resolution and validation are pure/deterministic given inputs — strong candidates for the partial property-based testing scope (pure functions).
- **Serialization round-trips**: canonical objects and mapping application are serialization-sensitive — also in scope for partial PBT (round-trip properties).

## Data Flow (text)
```
U2 submit -> [Process 1 validate] -> [Process 2 persist order] -> [Process 3 enqueue SUBMISSION]
U3 worker <- [Process 4 consume] -> [Process 5 resolve routing+mapping] -> (U3 executes ERP call) -> [Process 2 persist status]
U4 authoring -> [Process 5 read/write config via admin repos]
```
