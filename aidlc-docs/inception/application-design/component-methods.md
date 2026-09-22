# Component Methods — ERP & Supply Chain Order Portal

Interface-level method signatures (purpose, inputs, outputs). **Detailed business rules, validation logic, and data schemas are deferred to Functional Design.** Signatures are illustrative (Java/Spring style); names may be refined. All commands/queries receive an immutable `TenantContext` (C-05) except operator/admin operations, which use an operator principal.

Notation: `Type` = canonical model type from Contracts (C-01). Reseller results use reseller DTOs (no ERP identity); operator results may use admin DTOs.

---

## C-05 Security & Tenant Context
```
interface TenantContextProvider {
  TenantContext current();                       // immutable tenant scope for this request/message
}
interface Authorizer {
  void requireTenantAccess(TenantContext ctx, ResourceRef ref);   // object-level (IDOR) check
  void requireOperatorRole(OperatorPrincipal p, Role role);       // function-level check
}
interface CredentialCipher {
  byte[] encrypt(String plaintext, String keyId);
  String decrypt(byte[] ciphertext, String keyId);
}
```

## C-04 Identity Infrastructure
```
interface TokenValidator {
  Claims validate(String jwt);                   // signature/JWKS, issuer, audience, expiry
}
interface CognitoAdminClient {                   // isolated AWS dependency (FR-37)
  AppClient createResellerClient(TenantId tenant, ClientSpec spec);
  void disableClient(ClientId clientId);
}
```

## C-07 Ordering
```
interface OrderCommandService {
  OrderId create(TenantContext ctx, CreateOrderCommand cmd);   // returns id + initial status (FR-07)
  void update(TenantContext ctx, UpdateOrderCommand cmd);      // allowed by lifecycle state (O-09)
  void cancel(TenantContext ctx, OrderId id, CancelReason r);  // allowed by lifecycle state (O-09)
}
interface OrderQueryService {
  OrderView get(TenantContext ctx, OrderId id);                // reseller DTO, no ERP identity
  Page<OrderSummary> list(TenantContext ctx, OrderFilter f, Page p);
  List<StatusHistoryEntry> timeline(TenantContext ctx, OrderId id);
}
interface OrderLifecycle {                        // state machine (worker)
  OrderState transition(OrderId id, LifecycleEvent e);         // guarded transitions + status-history append
}
```

## C-08 Routing
```
interface RoutingService {
  RoutingDecision resolve(OrderId id);            // owning connection from item ownership (FR-14/17)
                                                  // throws MixedErpOrderException -> Rejected (FR-18)
  RoutingDecision current(OrderId id);            // immutable once set (AC-03)
}
```

## C-08b Catalog & Item Ownership
```
interface ItemQueryService {
  Page<ItemView> list(TenantContext ctx, ItemFilter f, Page p);   // read-only (FR-10)
}
interface ItemOwnershipService {                  // operator/worker
  void assignOwner(ItemKey item, ConnectionId owner);
  List<OwnershipConflict> listConflicts();        // same item from two ERPs (FR-22)
  void resolveConflict(ItemKey item, ConnectionId owner);
}
```

## C-09 Customers & Bindings
```
interface BindingService {                        // operator
  BindingId createBinding(TenantId tenant, ConnectionId conn, ErpCustomerRef customer); // verifies + uniqueness (AC-05)
  List<MatchSuggestion> suggestMatches(TenantId tenant, ConnectionId conn);             // FR-21
}
interface CustomerQueryService {
  CustomerView linkedCustomer(TenantContext ctx, ConnectionRef conn);   // reseller DTO, no ERP id
}
```

## C-10 ERP Integration
```
interface ErpAdapter {                            // common seam (Q3=C)
  ErpResult send(ConnectionConfig cfg, NativePayload payload);
  List<NativeStatusChange> pollStatus(ConnectionConfig cfg, Cursor since);
  List<NativeItem> fetchItems(ConnectionConfig cfg, Cursor since);
  Capabilities capabilities();
}
interface MappingEngine {
  NativePayload toNative(ConnectionId conn, CanonicalEntity e);   // declarative field maps + transforms
  CanonicalEntity toCanonical(ConnectionId conn, NativePayload p);
}
interface ConnectionRegistry {
  ConnectionConfig get(ConnectionId id);          // loads version-controlled config + mappings (Q2=B)
  List<ConnectionConfig> all();
  void reload();                                  // on deploy
}
interface ConformanceRunner {
  ConformanceReport run(ConnectionId conn);       // AC-12; entry point for future MCP onboarding (US-F7)
}
```

## C-11 Delivery & Reliability
```
interface DeliveryOrchestrator {                  // SQS FIFO consumer (worker)
  void onOrderReady(OrderReadyEvent e);           // idempotent; drives Sent to ERP/Confirmed/Rejected/Retrying
}
interface OutboxRelay {
  void publishPending();                          // committed outbox rows -> SNS (transactional outbox)
}
```

## C-12 Ingestion
```
interface StatusIngestor {                        // one per adapter, scheduled (Q8=A)
  void ingest(ConnectionId conn);                 // ERP changes -> canonical events -> read model (FR-28)
}
```

## C-13 Webhooks & Delivery Log
```
interface WebhookEndpointService {
  Endpoint register(TenantContext ctx, EndpointSpec spec);   // returns one-time secret (hashed at rest)
  void update(TenantContext ctx, EndpointId id, EndpointSpec spec);
  void setState(TenantContext ctx, EndpointId id, EndpointState s);  // pause/resume/deactivate
}
interface WebhookDispatcher {                     // worker
  void dispatch(CanonicalEvent e);               // signed request; records attempts
}
interface DeliveryLogService {
  Page<DeliveryEntry> list(TenantContext ctx, DeliveryFilter f, Page p);
  void replay(TenantContext ctx, DeliveryId id);  // AC-11
}
```

## C-14 Audit
```
interface AuditService {
  void record(ActorRef actor, String action, Object before, Object after);  // append-only, before/after
  Page<AuditEntry> query(AuditFilter f, Page p);
}
```

## C-16 Operator Admin API (orchestration entry points)
```
interface OnboardingService {                     // operator
  TenantId onboardReseller(OnboardResellerCommand cmd);   // tenant + Cognito client + claim (FR-37)
}
interface AdminOpsService {
  Page<FailedMessageView> failedMessages(FailedFilter f, Page p);  // raw ERP error + safe message
  void retryMessage(MessageId id);
  ConnectionHealth connectionHealth(ConnectionId id);
  MappingView viewMappings(ConnectionId id);      // read-only for MVP (Q2=B)
}
```

## C-19 Developer Enablement (CLI)
```
seed apply   --target <allow-listed>     // idempotent; tags created data (AC-14)
seed reset   --target <allow-listed>     // removes only what it created; refuses non-allow-listed
compose up                               // one-command local stack (AC-13)
```
