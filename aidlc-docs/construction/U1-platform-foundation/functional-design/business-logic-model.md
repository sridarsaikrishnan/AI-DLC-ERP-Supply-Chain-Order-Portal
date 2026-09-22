# Business Logic Model — U1 Platform Foundation

The foundational, technology-agnostic flows every unit reuses: **command → event → projection** (event sourcing + CQRS), tenant-context resolution, canonical error mapping, the audit path, and the integration relay. Concrete order business rules live in U3; U1 establishes the machinery and contracts.

---

## 1. Event sourcing + CQRS — the core loop (Order)

```
Command (e.g. CreateSalesOrderCommand)
   -> Order aggregate @CommandHandler          # validates invariants, decides
   -> applies Event(s) (OrderSubmitted, ...)   # facts
   -> Axon appends events to the event store   # PostgreSQL = source of truth
   -> @EventSourcingHandler mutates in-memory aggregate state (for the next command)
   -> @EventHandler projectors update read models (order_summary/detail/timeline)   # CQRS
   -> selected events relayed to SNS -> SQS FIFO (outbox / Axon processor)           # event-driven integration
```

- **Write side**: commands never mutate a table directly; they append events. Aggregate state is a fold over its event stream (rebuilt on load; no snapshot for MVP, Q6).
- **Read side**: queries never touch the event store; they read projections (eventual consistency, NFR-13). Command responses echo the resulting state+version so the submitter gets read-your-writes.
- **Evolution**: upcasters transform old event versions on read (Q6).
- **Ordering/idempotency**: integration events use `MessageGroupId = orderId` (per-order order) and `eventId` for consumer dedup.

## 2. Tenant-context resolution (every request/message)
```
inbound request/message
  -> TokenValidator validates JWT (JWKS, issuer, audience, expiry)     # C-04
  -> extract tenant claim -> build immutable TenantContext             # C-05 (Q7=A)
  -> all repositories/queries apply the tenant filter from TenantContext
  -> RLS on projection/reference tables enforces the same at the DB     # Q2 backstop
```
Operator requests carry an `OPERATOR` principal (Q3) and use the admin surface; they are not tenant-scoped but are role-checked and audited.

## 3. Canonical error mapping (reseller-safe)
```
any failure (validation | not-found | conflict | ERP error | authz | rate limit | unexpected)
  -> mapped to a CanonicalError (closed/sealed set, Q5)
  -> reseller-facing message carries the code + safe text, NEVER raw ERP text or ERP identity (FR-19)
  -> operator surfaces may additionally see the raw cause (operator-only)
```
The sealed error type makes the compiler force every new error path to choose an existing reseller-safe code — FR-19/AC-02 enforced structurally, not by convention.

## 4. Audit path
```
any operator mutation (onboarding, binding, connection, mapping view, ownership resolve, ...)
  -> AuditService.record(actor, action, before, after, occurredAt)     # append-only
  -> stored where application roles cannot delete/modify (SECURITY-13/14)
```

## 5. Integration relay (event-driven boundary)
```
committed domain event  -> transactional outbox (same tx)  -> OutboxRelay -> SNS(platform-domain-events)
                        -> SQS FIFO per consumer (order-processing / order-delivery / webhook-dispatch)
```
Guarantees no dual-write: the event and its outbox record commit atomically; the relay publishes afterward.

## 6. SOLID adherence (how the foundation stays clean)
- **SRP**: each capability module owns one concern; `api`/`worker` are thin hosts. Command handling, event application, projection, and integration relay are separate collaborators.
- **OCP**: adding an ERP = a new adapter + config + mappings, no change to the routing/ordering core (FR-27); new canonical errors extend the sealed set at defined points.
- **LSP**: all ERP transports honor the `ErpAdapter` contract; the generic engine treats Odoo and ERPNext interchangeably.
- **ISP**: narrow ports — `ErpAdapter`, `OrderRepository`, `TenantContextProvider`, `TokenValidator`, `CredentialCipher`, `DomainEventPublisher` — consumers depend only on what they use.
- **DIP**: `domain/*` defines ports and depends only on `canonical-model`; `platform-infrastructure` provides the implementations (Axon, JPA, SQS/SNS, Cognito). Domain never imports infrastructure.

## 7. Foundational happy path (illustrative, order create)
```
ResellerGraphQlController.createSalesOrder(input)
  -> validate input (types/lengths/formats)                             # SECURITY-05
  -> OrderCommandService.dispatch(CreateSalesOrderCommand)
       -> Order @CommandHandler: apply OrderSubmitted
       -> event store append (tx) + outbox row (tx)
  -> OrderProjector: upsert order_summary/order_detail (status=SUBMITTED)
  -> return SalesOrderView(orderId, status=SUBMITTED)                    # FR-07, read-your-writes
  (async) OutboxRelay -> SNS -> SQS(order-processing.fifo, group=orderId)  # picked up by U3
```
