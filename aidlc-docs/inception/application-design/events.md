# Event Catalog — ERP & Supply Chain Order Portal

Every asynchronous message in the platform, with proper names, payloads, and where it travels. There are **four families**:

1. **Commands** — an intent to change state (handled in-process by the `api`).
2. **Internal domain events** — facts about what happened, published via the transactional outbox → SNS → SQS. `PascalCase`. May carry internal fields like `owningConnectionId`.
3. **Integration events** — facts from ERP synchronization/ingestion. `PascalCase`.
4. **Public webhook events** — reseller-facing notifications. `dot.case`, canonical payload, **never** any ERP identity (FR-19). Names are *proposed* (O-08).

Sample values are illustrative.

---

## 0. Event envelope (all internal/integration events)

```java
record EventEnvelope<T>(
    String eventId,          // UUID, dedup key for idempotent consumers
    String eventType,        // e.g. "OrderValidated"
    Instant occurredAt,
    TenantId tenantId,
    String aggregateId,      // e.g. orderId — used as SQS MessageGroupId (per-order ordering)
    long version,            // aggregate version
    String correlationId,    // ties back to the originating request
    T payload
) {}
```

**Transport**: outbox row → SNS topic `platform-domain-events` → SQS FIFO queues (fan-out). `MessageGroupId = aggregateId` (order id) guarantees per-order ordering.

**Queues (consumers)**
| SQS FIFO queue | Consumer | Purpose |
|---|---|---|
| `order-processing.fifo` | `OrderProcessingListener` | validate + route submitted orders |
| `order-delivery.fifo` | `OrderDeliveryListener` | deliver ready orders to the owning ERP |
| `webhook-dispatch.fifo` | `WebhookDispatchListener` | send reseller webhooks |
| `order-processing-dlq.fifo`, `order-delivery-dlq.fifo` | (operator triage) | dead-lettered after retries exhausted |

---

## 1. Commands (in-process, `api`)

| Command | Handler | Result |
|---|---|---|
| `CreateSalesOrderCommand` | `OrderCommandService.create` | persists `SalesOrder(SUBMITTED)` + outbox `OrderSubmitted` |
| `UpdateSalesOrderCommand` | `OrderCommandService.update` | allowed by lifecycle state (O-09) |
| `CancelSalesOrderCommand` | `OrderCommandService.cancel` | outbox `OrderCancelled` |
| `RegisterWebhookEndpointCommand` | `WebhookEndpointService.register` | returns one-time signing secret |
| `OnboardResellerCommand` | `ResellerOnboardingService.onboard` | tenant + Cognito app client |
| `CreateCustomerBindingCommand` | `CustomerBindingService.create` | verified, unique binding |

---

## 2. Internal domain events (order lifecycle)

Produced by `OrderCommandService` (api) and the worker services `OrderValidationService`, `OrderRoutingService`, `OrderDeliveryListener`, `OrderLifecycleService`.

| Event | Emitted when | Key payload fields | Consumed by |
|---|---|---|---|
| `OrderSubmitted` | reseller creates an order | `orderId, externalReference` | `OrderProcessingListener` |
| `OrderValidated` | input+business validation pass | `orderId, owningConnectionId`* | `OrderProcessingListener` → emits ready |
| `OrderRejected` | validation fails / mixed-ERP | `orderId, reasonCode, resellerSafeMessage` | `WebhookDispatchListener` |
| `OrderReadyForDelivery` | routing resolved + binding ok | `orderId, owningConnectionId`* | `OrderDeliveryListener` |
| `OrderSentToErp` | adapter accepted the order | `orderId` | `WebhookDispatchListener` |
| `OrderConfirmed` | ERP confirmed | `orderId` (`erpConfirmationRef`* internal) | webhook dispatch |
| `OrderFulfilled` | ERP reports fulfilled | `orderId` | webhook dispatch |
| `OrderClosed` | order completed | `orderId` | webhook dispatch |
| `OrderRetrying` | delivery failed, will retry | `orderId, attempt, nextRetryAt` | webhook dispatch |
| `OrderCancelled` | reseller cancelled | `orderId, reason` | delivery (compensate), webhook |

`*` internal-only field; stripped before any reseller-facing projection or webhook.

### Example
```json
{
  "eventId": "evt_5b2c…", "eventType": "OrderValidated",
  "occurredAt": "2026-09-21T09:14:05Z",
  "tenantId": "tnt_acme", "aggregateId": "ord_9c1e77a2", "version": 2,
  "correlationId": "req_774…",
  "payload": { "orderId": "ord_9c1e77a2", "owningConnectionId": "conn_odoo_eu1" }
}
```

---

## 3. Integration events (ERP sync/ingestion)

Produced by `ErpStatusIngestionScheduler` / `ItemSynchronizationService`.

| Event | Emitted when | Key payload | Consumed by |
|---|---|---|---|
| `ErpOrderStatusChanged` | ingestion sees a native status change | `orderId, newStatus (canonical)` | `OrderLifecycleService` |
| `ItemSynced` | an item is (re)synced from an ERP | `sku, connectionId` | `ItemOwnershipService` |
| `ItemOwnershipConflictDetected` | same sku from two ERPs | `sku, conflictingConnectionIds[]` | operator alert (AdminItemOwnership) |
| `CustomerBindingVerified` | binding verified against ERP | `tenantId, connectionId, customerId` | audit |

---

## 4. Public webhook events (reseller-facing) — proposed (O-08)

Delivered by `WebhookDispatchListener` → `WebhookSender` (signed). Payload is the canonical `SalesOrderView` (Section 4 of `canonical-model.md`); **no ERP identity**.

| Public event name | Triggered by internal event | Payload |
|---|---|---|
| `order.created` | `OrderSubmitted` | `SalesOrderView` |
| `order.status_changed` | `OrderSentToErp`, `OrderConfirmed`, `OrderFulfilled`, `OrderClosed` | `SalesOrderView` |
| `order.retrying` | `OrderRetrying` | `SalesOrderView` (status RETRYING) |
| `order.rejected` | `OrderRejected` | `SalesOrderView` (status REJECTED, reseller-safe note) |

### Webhook envelope (reseller-facing)
```json
{
  "id": "whm_3f…",
  "type": "order.status_changed",
  "createdAt": "2026-09-21T09:14:07Z",
  "data": { "…": "SalesOrderView (no ERP identity)" }
}
```
Signature: an HMAC signature header over the raw body (exact header name and replay window are O-08). The signing secret is shown once at endpoint creation and stored hashed.

### Webhook delivery lifecycle (internal, per attempt)
| Event | Meaning |
|---|---|
| `WebhookDeliveryAttempted` | an attempt was made (recorded in delivery log) |
| `WebhookDeliverySucceeded` | endpoint returned 2xx |
| `WebhookDeliveryFailed` | non-2xx / timeout; will retry per policy |

---

## 5. Naming conventions
- Internal events: `PascalCase` past-tense facts (`OrderValidated`), one aggregate per event, `aggregateId` = SQS MessageGroupId.
- Public webhook events: lowercase `noun.verb_past` (`order.status_changed`), reseller-safe payloads only.
- Commands: `VerbNounCommand` (`CreateSalesOrderCommand`).
- Every internal/integration event carries `eventId` (dedup), `correlationId` (tracing), and `occurredAt`.
