# Services & Orchestration — ERP & Supply Chain Order Portal

The service layer, using proper names. Reading model:
- The **`api`** process handles GraphQL, accepts commands, and serves reads straight from PostgreSQL (Q4=A, Q5=B).
- The **`worker`** process owns the order-processing saga, ERP delivery, ingestion, webhook dispatch, and the outbox relay.
- The two processes never call each other directly — they communicate through the **transactional outbox → SNS → SQS FIFO** pipeline (see `events.md`).
- All ERP access goes through a single facade, **`ErpGateway`**.

Interfaces are listed in `component-methods.md`; canonical types and payloads in `canonical-model.md`; message names in `events.md`.

---

## 1. `api` process — services

| Class / interface | Kind | Responsibility |
|---|---|---|
| `ResellerGraphQlController` | GraphQL entry (`/graphql`) | Reseller queries/mutations; binds `TenantContext`; returns reseller view types only |
| `OperatorGraphQlController` | GraphQL entry (`/admin/graphql`) | Operator queries/mutations; enforces operator roles; may return ERP identity |
| `OrderCommandService` | application service | `createSalesOrder`, `updateSalesOrder`, `cancelSalesOrder`; persists aggregate + outbox row in one transaction; returns `SalesOrderView` |
| `OrderQueryService` | application service | `getOrder`, `listOrders`, `getTimeline`; reads PostgreSQL; maps to `SalesOrderView` (no ERP identity) |
| `ItemCatalogQueryService` | application service | Read-only item catalog for a tenant (FR-10) |
| `LinkedCustomerQueryService` | application service | Read-only linked-customer view (FR-11) |
| `WebhookEndpointService` | application service | Register/update/pause/resume/deactivate endpoints; issues one-time signing secret |
| `DeliveryLogQueryService` | application service | Reads the delivery log; triggers `replayDelivery` |
| `ResellerOnboardingService` | application service | `onboardReseller`: creates tenant + Cognito app client (via `CognitoAdminGateway`) + tenant claim; audited |
| `CustomerBindingService` | application service | `createBinding` (verifies via `ErpGateway`, enforces uniqueness), `suggestMatches` |
| `ItemOwnershipService` | application service | List/resolve item-ownership conflicts |
| `ConnectionAdminService` | application service | Connection health, read-only mapping viewer (Q2=B) |
| `FailedMessageService` | application service | List retrying/rejected/dead-lettered messages (raw ERP error + reseller-safe message); `retryMessage` |
| `AuditQueryService` | application service | Query the audit trail |

## 2. `worker` process — services

| Class / interface | Kind | Trigger → action |
|---|---|---|
| `OrderProcessingListener` | SQS listener (`order-processing.fifo`) | on `OrderSubmitted` → `OrderValidationService` then `OrderRoutingService` → emit `OrderReadyForDelivery` or `OrderRejected` |
| `OrderValidationService` | domain service | Input + business validation at the Validated step (FR-14) |
| `OrderRoutingService` | domain service | Resolve `owningConnectionId` from item ownership; reject mixed-ERP (FR-16..18); persist immutable `RoutingDecision` |
| `OrderDeliveryListener` | SQS listener (`order-delivery.fifo`) | on `OrderReadyForDelivery` → `ErpGateway.send` → `OrderLifecycleService` transitions (Sent to ERP/Confirmed/Rejected/Retrying); idempotent by `eventId` |
| `OrderLifecycleService` | domain service | Guarded state-machine transitions + append `StatusHistoryEntry` |
| `ErpStatusIngestionScheduler` | scheduled job | Periodically runs each `ErpStatusIngestor` (Q8=A) |
| `OdooStatusIngestor`, `ErpNextStatusIngestor` | ingestors | Poll native status → `MappingEngine.toCanonical` → emit `ErpOrderStatusChanged` |
| `ItemSynchronizationService` | domain service | Sync items; emit `ItemSynced` / `ItemOwnershipConflictDetected` |
| `WebhookDispatchListener` | SQS listener (`webhook-dispatch.fifo`) | Map internal event → public webhook event; `WebhookSigner` + `WebhookSender`; record via `DeliveryLogWriter` |
| `OutboxRelayScheduler` | scheduled job | Publish committed outbox rows to SNS (`DomainEventPublisher`) |

## 3. Shared services (both processes)

| Class / interface | Responsibility |
|---|---|
| `TenantContextHolder` | Provides the immutable `TenantContext` for the current request/message (Q7=A) |
| `JwtTokenValidator` | Validates Cognito JWTs (JWKS, issuer, audience, expiry) |
| `CognitoAdminGateway` | Isolated AWS Cognito Identity Provider client for app-client provisioning (FR-37) |
| `AesGcmCredentialCipher` | Encrypts/decrypts ERP credentials (key from Secrets Manager/KMS) |
| `ErpGateway` | Facade over `ConnectionRegistry` + `DeclarativeMappingEngine` + `ErpAdapter` + cipher — the only path to an ERP |
| `FileBackedConnectionRegistry` | Loads version-controlled connection config + mappings on deploy (Q2=B) |
| `DeclarativeMappingEngine` | canonical↔native transformation from declarative field maps |
| `AuditService` | Append-only audit records with before/after values |
| `DomainEventPublisher` / `OutboxRepository` | Transactional outbox write + SNS publish |

---

## 4. Key orchestration flows

### 4.1 Place order → deliver (happy path)
```
Reseller → ResellerGraphQlController.createSalesOrder
  → OrderCommandService.create:
       persist SalesOrder(SUBMITTED) + Outbox(OrderSubmitted) in ONE transaction
       return SalesOrderView (orderId, status=SUBMITTED)          (FR-07)
OutboxRelayScheduler → SNS(platform-domain-events) → SQS(order-processing.fifo, group=orderId)
OrderProcessingListener.onOrderSubmitted
  → OrderValidationService.validate
  → OrderRoutingService.resolve → owningConnectionId            (FR-14/17)
  → emit OrderReadyForDelivery   [or OrderRejected if mixed-ERP/invalid → FR-18]
→ SQS(order-delivery.fifo, group=orderId)
OrderDeliveryListener.onOrderReady
  → ErpGateway.send(owningConnectionId, MappingEngine.toNative(order))
  → OrderLifecycleService: SENT_TO_ERP → (ack) CONFIRMED
  on ERP outage → RETRYING (SQS visibility-timeout backoff; DLQ on exhaustion)   (FR-29, AC-07)
```

### 4.2 ERP status change → reseller visibility
```
ErpStatusIngestionScheduler → OdooStatusIngestor.ingest(conn)
  → ErpGateway.pollStatus → MappingEngine.toCanonical
  → emit ErpOrderStatusChanged → OrderLifecycleService.transition
  → Outbox(OrderConfirmed/…) → SNS → SQS(webhook-dispatch.fifo)
  → WebhookDispatchListener → order.status_changed (signed)      (FR-15/28, AC-09)
```

### 4.3 Reads during an ERP outage
```
Reseller → ResellerGraphQlController → OrderQueryService → PostgreSQL   (no ERP call; AC-10)
```

### 4.4 Operator onboarding
```
Operator → OperatorGraphQlController → ResellerOnboardingService.onboardReseller
  → CognitoAdminGateway.createResellerClient(tenant claim) → persist → AuditService.record  (FR-37/38)
Operator → CustomerBindingService.createBinding → ErpGateway verify → uniqueness → persist   (AC-05)
```

---

## 5. Orchestration principles
- **Command/query split**: `api` writes commands and reads the same PostgreSQL tables (Q5=B); `worker` does all async orchestration.
- **Transactional outbox**: state change + outbox row committed together; `OutboxRelayScheduler` publishes. No dual-write.
- **Saga over the lifecycle**: `OrderProcessingListener` → `OrderDeliveryListener` advance the state machine via events; each listener is idempotent (dedup by `eventId`).
- **Single ERP egress**: everything ERP goes through `ErpGateway`, keeping adapters/mappings/credentials in one place and reseller code free of ERP identity (FR-19).
- **Fan-out**: one publish to SNS fans out to per-consumer SQS FIFO queues (delivery, webhooks), decoupling consumers.
- **Degraded mode**: reads always come from PostgreSQL; ERP outages affect only delivery/ingestion, which retry (RESILIENCY-10).
- **API-first onboarding**: connection/mapping/conformance operations are callable services, enabling the future MCP onboarding (US-F7).
