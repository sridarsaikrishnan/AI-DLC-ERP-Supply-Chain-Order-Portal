# High-Level Design — ERP & Supply Chain Order Portal

C4 **container-level** view. Diagram source: [`hld.drawio`](hld.drawio) (open in
diagrams.net or the VS Code Draw.io extension). It has **two pages**: *(1) Container view*
and *(2) Modules → tables (data ownership)*.

Scope: major components, their responsibilities, external dependencies, data stores,
communication paths, and the significant flows and boundaries. It deliberately omits
classes, methods, tables/columns, API schemas, and low-level config. Anything not
established by the product is marked **TBD** rather than assumed.

## System context

The portal lets **resellers** place orders with a distributor and track them, while the
distributor's **operator** administers the catalog, pricing (quotes), reseller↔ERP
customer links, and ERP connections. Orders are forwarded to the distributor's **ERP**
(Odoo today) as the system of record; the ERP's status changes flow back to resellers.
An order is always a reply to an **operator-issued quote** (prices, validity window,
end customer, ship-to); the catalog says only *what a product is*.

Interacting parties and systems:
- **Reseller** (human) — via the Reseller SPA.
- **Operator / distributor admin** (human) — via the Operator SPA.
- **ERP (Odoo)** — external; receives orders and pushes status back. Additional ERP
  types: **TBD** (only Odoo is implemented and registered today).
- **Reseller webhook endpoints** — external receivers the portal pushes status to.
- **AWS Cognito** (identity) and **AWS Secrets Manager** (credentials) — managed deps.

## Container / component overview

| Component | Purpose / responsibility | Key dependencies |
|---|---|---|
| **Reseller portal (SPA)** | Browser app: browse quotes, place orders, track status/scores, manage webhook endpoints. Never shows ERP identity (FR-19). | API host (GraphQL /reseller); Cognito (login) |
| **Operator admin (SPA)** | Browser app: manage ERP connections, resellers/bindings, items, quotes, operating companies; view all orders and failures. | API host (GraphQL /operator); Cognito |
| **API host** *(Python/FastAPI — the only HTTP server)* | Synchronous interface: GraphQL for both audiences, the inbound ERP-webhook HTTP route, request authentication/authorization, and reads/writes via the domain. | Domain modules; PostgreSQL; Cognito; Secrets Manager |
| **Worker host** *(Python process — not HTTP, not FastAPI)* | Asynchronous processing: order routing, ERP delivery, read-model projection, outbound webhook dispatch, outbox relay, and the reconciliation scheduler (polling fallback). Same codebase/composition root as the API, different entrypoint. | Message bus; Domain modules; PostgreSQL; ERP; Secrets Manager |
| **Domain modules** (shared) | The business logic shared by API + Worker, grouped by subdomain (ADR-0017): **`sales/`** (`ordering` — the event-sourced core — plus `quoting`, `shipment`, `invoicing`, `payments`, `returns`), **`reference/`** (`catalog`, `connections`, `tenancy`), **`integration/`** (`erp` adapters + registry, inbound/outbound `webhooks`). | PostgreSQL (via hosts) |
| **PostgreSQL (Aurora)** | Single datastore: event store + outbox + snapshots, order projections (read models), and reference/CRUD data. | — (owned by the domain) |
| **Message bus** | Async transport: SNS FIFO topic → SQS FIFO queues (+ DLQ). floci locally, AWS in prod. | — |
| **AWS Cognito** | Identity provider (JWT); header-stub provider for local dev. | — |
| **AWS Secrets Manager** | Stores ERP login and webhook signing secrets (never persisted in the DB). | — |
| **ERP — Odoo** (external) | System of record for orders; accepts orders over JSON-RPC and emits status webhooks. | — |
| **Reseller webhook endpoints** (external) | Reseller-operated receivers for signed status notifications. | — |

## Key flows

1. **Place an order (reply to a quote) → ERP** *(sync entry, async fulfilment)*
   Reseller SPA → API `placeOrder(quoteId, …)` → the Order aggregate's events + outbox
   row are written to PostgreSQL in one transaction → outbox relay publishes to the bus →
   `order-processing` routes by item ownership + verified binding → `order-delivery`
   submits to the ERP adapter (customer = the binding's ERP customer id; idempotency key =
   the platform order id).

2. **ERP status → reseller** *(async in, async out)*
   Odoo → API inbound webhook (authenticated, deduplicated) → status applied to the Order
   → projections rebuild the reseller/operator read models → `webhook-dispatch` delivers a
   signed notification to the reseller's endpoint.

3. **Operator administration** *(sync)*
   Operator SPA → API `/operator` → issue quotes, create operating companies ("office
   cards"), register ERP connections, link resellers to ERP customers, manage the catalog
   (including box-vs-license item kind).

4. **Reconciliation fallback** *(async, scheduled)*
   The Worker's reconciliation scheduler periodically polls the ERP for orders whose
   webhook was missed, and applies status the same way as flow 2 — the safety net for
   at-least-once/missed events.

5. **Authentication** *(sync)*
   SPAs obtain a JWT from Cognito; the API verifies it per request and scopes every
   resolver to the caller's tenant/role (reseller data is tenant-isolated; operator role
   required for the operator schema).

## Data ownership

- **The domain (via API + Worker) owns PostgreSQL** — the single store holding the Order
  event stream + outbox + snapshots, the order read models (projections), and reference
  data (catalog items, ERP connections, reseller bindings, quotes, operating companies,
  webhook endpoints/deliveries). The `ordering` aggregate is the only event-sourced one;
  everything else is CRUD/reference data.
- **API** publishes order events (writes events + outbox); **Worker** consumes events and
  owns projection writes. **ERP (Odoo)** owns the authoritative order record on its side;
  the portal mirrors status back via projections. Secrets are owned by **Secrets
  Manager**, identities by **Cognito**.

### Module → table ownership (see diagram page 2)

Modules are grouped by subdomain (ADR-0017): `sales/`, `reference/`, `integration/`.

| Group | Module | Owns (writes) | Reads |
|---|---|---|---|
| — | shared event-sourcing kernel | `events`, `outbox`, `snapshots` | — |
| `sales` | `ordering` *(event-sourced)* | `orders`, `order_status_history` (projections) | persists Order events via the kernel |
| `sales` | `shipment` *(event-sourced)* | — | persists Shipment events via the kernel; `ShipmentRecorded` drives the `orders` fulfilled-quantity score asynchronously via the `order-fulfillment` saga consumer (ADR-0018) |
| `sales` | `invoicing` *(event-sourced)* | — | persists Invoice events via the kernel; `InvoiceRecorded` drives the `orders` invoiced-quantity score asynchronously via the `order-fulfillment` saga consumer (ADR-0018) |
| `sales` | `payments` *(event-sourced)* | — | persists Payment events via the kernel (standalone; not yet wired to the order) |
| `sales` | `returns` *(event-sourced)* | — | persists Return events via the kernel (standalone; not yet wired to the order) |
| `sales` | `quoting` | `quotes`, `operating_companies` | — |
| `reference` | `catalog` | `items` | — |
| `reference` | `tenancy` | `tenant_connection_bindings` | — |
| `reference` | `connections` | `erp_connections` | — |
| `integration` | `erp` (ERP adapters) | — | `erp_connections`, order payload from `orders` |
| `integration` | `webhooks_inbound` | `processed_events` (dedupe) | `orders` (reverse-routing locator) |
| `integration` | `webhooks_outbound` | `webhook_endpoints`, `webhook_deliveries` | — |

`processed_events` is also used by the Worker consumers to dedupe on `event_id`.
`audit_log` exists in a migration but is **not written by any module yet** — reserved / **TBD**.

## Boundaries

- **Browser (untrusted) vs. trusted server zone** — SPAs run on user devices; all
  authority lives server-side (API/Worker/DB). Every request is authenticated and
  tenant/role-scoped.
- **Reseller vs. operator data boundary** — reseller surfaces must never expose ERP
  identity (name, instance, ERP record id); only operator surfaces may (FR-19).
- **Product boundary** — the SPAs, API, Worker, and domain.
- **Cloud (AWS) boundary** — Cognito, Secrets Manager, SNS/SQS, Aurora, and the Fargate
  runtimes are AWS-managed.
- **External boundary** — the ERP and reseller webhook endpoints are third-party controlled.

## Deployment / runtime boundaries

- **API host** and **Worker host** are separate deployables (containers, ECS Fargate in
  the target architecture) so the synchronous and asynchronous workloads scale
  independently; the Worker is further role-splittable (routing / delivery / projections /
  dispatch / relay / reconcile).
- **Local/dev** runs the same code with an in-memory bus and (optionally) floci standing
  in for AWS; **prod** uses the AWS services above.

## Non-functional considerations (architecturally significant)

- **Security** — JWT auth (Cognito) + per-request tenant/role scoping; secrets only in
  Secrets Manager (never the DB); inbound webhooks authenticated (shared-secret/HMAC);
  outbound webhooks HMAC-signed; FR-19 reseller/ERP data isolation; RLS available in the
  DB for defense in depth.
- **Reliability / consistency** — each aggregate's events + outbox rows are written in one
  DB transaction (no dual-write); at-least-once delivery with per-consumer dedupe; DLQ for
  poison messages; ERP submit is idempotent (keyed on the platform order id); reconciliation
  sweeper as the missed-event safety net. Cross-aggregate links (shipment/invoice → order
  score) are **event-driven sagas** (ADR-0018), eventually consistent — not a shared
  transaction — which is what keeps the modules independently extractable.
- **Scalability** — stateless API/Worker scale horizontally; async work absorbs ERP
  latency/outages via the queue; single Postgres today (read-model/replica scaling: TBD).
- **Observability** — structured logging across API/Worker; delivery log + failed-message
  views for operators. Metrics/tracing stack: **TBD**.
- **Availability / DR** — managed AWS services (Aurora, SQS, Cognito). Multi-AZ/region
  topology, RPO/RTO targets, and backup/restore policy: **TBD**.
- **Performance** — reads served from projections (CQRS) rather than replaying events;
  specific latency/throughput targets: **TBD**.
