# Components — ERP & Supply Chain Order Portal

High-level component identification and responsibilities. Based on the approved application-design-plan answers: one `api` process with two GraphQL schemas (Q1=A), mapping definitions as version-controlled files (Q2=B), common adapter interface + generic REST engine + per-ERP quirks (Q3=C), routing + lifecycle state machine in the `worker` (Q4=A), read model = same PostgreSQL tables queried directly (Q5=B), hybrid Gradle modules (Q6=C), a dedicated tenant-context component (Q7=A), a distinct ingestion component per adapter (Q8=A), and two separate React apps (Q9=A).

**Deployables**: `api` (Spring Boot), `worker` (Spring Boot), `ui` (two React apps in one container). Detailed business rules and schemas are deferred to Functional Design.

**Legend** — Deployable: which runtime hosts the component. Reqs: satisfied requirements/stories.

---

## A. Shared / platform modules

### C-01 Contracts
- **Deployable**: shared library (api, worker)
- **Purpose**: The canonical model and cross-module contracts.
- **Responsibilities**: Canonical entity types (Sales Order, Purchase Order, Item, Customer); canonical domain events; canonical error codes; **separate reseller-facing DTOs vs operator/admin DTOs** so reseller types structurally cannot carry ERP identity (FR-19). No business logic.
- **Reqs**: FR-06, FR-08, FR-19, FR-25.

### C-02 Persistence Infrastructure
- **Deployable**: shared (api, worker)
- **Purpose**: Relational persistence for all platform state.
- **Responsibilities**: Spring Data JPA repositories, Flyway migrations, row-level tenant scoping helpers, transactional outbox table access. Single source of truth; reseller reads hit these tables directly (Q5=B).
- **Reqs**: FR-31, NFR-05, SECURITY-01, SECURITY-05.

### C-03 Messaging Infrastructure
- **Deployable**: shared (api, worker)
- **Purpose**: Reliable asynchronous messaging over AWS SQS/SNS.
- **Responsibilities**: Outbox relay (publishes committed outbox rows to SNS), SNS topic + per-consumer SQS FIFO queues (MessageGroupId = order id), consumer plumbing, dead-letter queue + redrive, idempotent-consumer support. Isolated behind interfaces (AWS SDK not exposed to domain).
- **Reqs**: FR-29, FR-30, NFR-01, RESILIENCY-10.

### C-04 Identity Infrastructure
- **Deployable**: shared (api primarily)
- **Purpose**: OIDC/JWT validation and Cognito administration behind interfaces.
- **Responsibilities**: Validate JWTs (signature/JWKS, issuer, audience, expiry); a `CognitoAdminClient` interface for creating/managing reseller app clients (FR-37); token-claim extraction. Emulated by Floci locally; real Cognito authoritative for the token path.
- **Reqs**: FR-03, FR-37, SECURITY-08, SECURITY-12.

### C-05 Security & Tenant Context
- **Deployable**: shared (api, worker)
- **Purpose**: Enforce tenant isolation and authorization uniformly (Q7=A).
- **Responsibilities**: Build an immutable `TenantContext` from the validated token claim once per request/message; expose it to all queries/commands; deny-by-default authorization guards; object-level ownership checks; CORS allow-list; crypto helper (AES-GCM) for ERP credential encryption.
- **Reqs**: FR-01, FR-04, AC-01, AC-15, SECURITY-06, SECURITY-08, SECURITY-11.

### C-06 Observability
- **Deployable**: shared (api, worker)
- **Purpose**: Structured logging, metrics, tracing.
- **Responsibilities**: OpenTelemetry wiring, correlation id on every request/message, health endpoints (DB, SQS reachability, Cognito JWKS), no secrets/PII/ERP-identity in logs.
- **Reqs**: NFR-07, SECURITY-03, RESILIENCY-05, RESILIENCY-06.

---

## B. Domain / feature modules

### C-07 Ordering
- **Deployable**: api (command intake, queries) + worker (lifecycle transitions)
- **Purpose**: The order aggregate and its lifecycle.
- **Responsibilities**: Create/update/cancel order commands; the lifecycle state machine (Draft → Submitted → Validated → Sent to ERP → Confirmed → Fulfilled → Closed, plus Retrying/Rejected); append-only order status-history (feeds the timeline; no event sourcing); order queries for the read model.
- **Reqs**: FR-05, FR-07, FR-09, FR-12..FR-15; US-006..US-010, US-020, US-021.

### C-08 Routing
- **Deployable**: worker
- **Purpose**: Decide the single owning ERP connection for an order (Q4=A).
- **Responsibilities**: At Validated, resolve the owning connection from item ownership; reject mixed-ERP orders with a reseller-safe message (FR-18); persist the routing decision immutably for the order's life; tenant-default routing only for item-less drafts.
- **Reqs**: FR-14, FR-16, FR-17, FR-18; AC-03, AC-04; US-013, US-014.

### C-08b Catalog & Item Ownership
- **Deployable**: api (read) + worker (sync/ownership)
- **Purpose**: Items and their single-owner rule.
- **Responsibilities**: Read-only item catalog for tenants (FR-10); maintain one owning connection per tenant-visible item; detect the same item reported by two ERPs, flag to the operator, withhold from tenants until resolved.
- **Reqs**: FR-10, FR-22; AC-06; US-011, US-033.

### C-09 Customers & Bindings
- **Deployable**: api (queries) + worker/api (verification)
- **Purpose**: Link tenants to their existing ERP customer records.
- **Responsibilities**: Create/verify a binding per (tenant, connection); enforce uniqueness (one binding per (tenant, connection); an ERP customer belongs to at most one tenant); one-time onboarding match suggestions; read-only linked-customer view for tenants; never publish unbound-customer data.
- **Reqs**: FR-11, FR-20, FR-21; AC-05; US-002, US-005, US-012.

### C-10 ERP Integration
- **Deployable**: worker (delivery, ingestion) + api (admin config/conformance triggers)
- **Purpose**: Talk to each ERP without per-ERP connector code (Q3=C).
- **Responsibilities**: `ErpAdapter` interface + a **transport-agnostic** request engine with per-ERP **transport adapters** — an **Odoo** XML-RPC/JSON-RPC transport (ORM calls `create`/`write`/`search_read` on models `sale.order`, `res.partner`, `product.product`) and an **ERPNext** REST transport (`/api/resource/{DocType}` CRUD); per-ERP handling of auth, pagination, and status vocabulary; Mapping Engine applying declarative field maps + named transforms (canonical↔native); Connection Registry loading version-controlled connection config + mappings (Q2=B); ERP credential decryption; conformance-suite entry points. **API-first, machine-drivable onboarding surface** (design principle for future US-F7). *(ERP protocols verified 2026-09-21; see O-12/O-13.)*
- **Reqs**: FR-23..FR-28; AC-12; US-027..US-031.

### C-11 Delivery & Reliability
- **Deployable**: worker
- **Purpose**: Guaranteed, idempotent delivery of orders to the owning ERP.
- **Responsibilities**: Consume order-ready events from SQS FIFO; call the ERP adapter; drive Sent to ERP / Confirmed / Rejected / Retrying transitions; idempotency keys; retry with backoff via visibility timeout; dead-letter on exhaustion (operator-visible).
- **Reqs**: FR-29, FR-30; AC-07, AC-08, AC-16; US-017, US-018, US-034.

### C-12 Ingestion
- **Deployable**: worker
- **Purpose**: Bring ERP-side status changes into the platform (Q8=A).
- **Responsibilities**: A distinct ingestion component per adapter; in-app scheduler polls (or receives events), translates ERP changes to canonical events, maps ERP status vocab to the lifecycle, updates the read model.
- **Reqs**: FR-15, FR-28, FR-31; AC-09, AC-10; US-019, US-020, US-030.

### C-13 Webhooks & Delivery Log
- **Deployable**: api (endpoint mgmt, log queries) + worker (dispatch)
- **Purpose**: Notify resellers and record deliveries.
- **Responsibilities**: Manage endpoints (create/update/pause/resume/deactivate); one-time signing secret (stored hashed); dispatch signed webhooks on canonical events; delivery log with attempts/payload/timestamps; replay; no ERP identity. *Proposed items (signature format, replay window, event names, secret rotation) tagged O-08.*
- **Reqs**: FR-32, FR-33; AC-11; US-022..US-026.

### C-14 Audit
- **Deployable**: shared (api, worker)
- **Purpose**: Accountable record of administrative changes.
- **Responsibilities**: Append-only audit entries with actor, timestamp, before/after values; tamper-evident; not deletable by application roles.
- **Reqs**: FR-38; SECURITY-13, SECURITY-14; US-035.

---

## C. Interface / edge modules

### C-15 Reseller API
- **Deployable**: api (`/graphql`)
- **Purpose**: The reseller-facing GraphQL surface (Q1=A).
- **Responsibilities**: Reseller schema — queries (orders, items, linked customer, delivery log) and mutations (create/update/cancel order, manage webhook endpoints); reseller DTOs only; input validation, depth/complexity limits, rate limiting; every operation scoped by TenantContext.
- **Reqs**: FR-05, FR-07, FR-19; SECURITY-05, SECURITY-08, SECURITY-11; US-006..US-012, US-022, US-024.

### C-16 Operator Admin API
- **Deployable**: api (`/admin/graphql`)
- **Purpose**: The operator-facing GraphQL surface, separate schema.
- **Responsibilities**: Admin schema — reseller onboarding, connections health, **mapping viewer (read-only for MVP; runtime editing deferred per Q2=B)**, item-ownership conflicts, customer bindings, failed/retrying/dead-lettered messages (raw ERP error beside reseller-safe message), audit trail. Function-level authorization; may show ERP identity.
- **Reqs**: FR-04, FR-35, FR-37, FR-38; US-001, US-002, US-032..US-036.

### C-17 Reseller Web App
- **Deployable**: ui (React app #1)
- **Purpose**: Reseller human UI (Q9=A).
- **Responsibilities**: Screens `Main` (/orders), `OrderDetail`, `DeliveryLog`, `WebhookEndpoints`; design-system components/tokens; OIDC auth-code sign-in (screen not yet designed); never renders ERP identity.
- **Reqs**: FR-34, FR-19, NFR-08; US-007, US-008, US-022, US-024.

### C-18 Operator Web App
- **Deployable**: ui (React app #2)
- **Purpose**: Operator admin UI (Q9=A).
- **Responsibilities**: Screens `AdminTenants`, `AdminTenantDetail`, `AdminConnections`, `AdminItemOwnership`, `AdminFailedMessages`, `AdminAudit`; may show ERP identity; hits `/admin/graphql`.
- **Reqs**: FR-35; US-001, US-002, US-032..US-035.

### C-19 Developer Enablement
- **Deployable**: tooling (compose, seed CLI)
- **Purpose**: Local environment and safe seeding (Platform Engineer, P4).
- **Responsibilities**: One-command Docker Compose (real PostgreSQL, Floci for Cognito/SQS/SNS, mock ERP, optional Odoo/ERPNext); allow-listed, reversible, idempotent seed tool for fictional non-prod data.
- **Reqs**: FR-39, FR-40; AC-13, AC-14; US-037, US-038.

---

## Not-yet-designed UI surfaces (flag for later UI design)
Sign in, new-order form + line editor, item catalog, and the mapping viewer/editor are referenced by components (C-15/C-17/C-16) but not in the current `design/` screen set. They must be designed in the existing style before Code Generation of those units; do not deviate from existing screens without asking.
