# Developer guide — the data flow, traced end to end

One order, followed hop by hop with the **actual payloads**, the **events** emitted, what
each event **changes**, the **intermediate records** written, how statuses are **converted**,
and the **notifications** sent out. No step is skipped. If you only read one doc to
understand how this system behaves at runtime, read this one.

New to event sourcing? Read [event-sourcing-explained.md](event-sourcing-explained.md) first
(the "why"), then come back here (the "what happens"). Every table/column mentioned is in
[database-schema.md](database-schema.md).

---

## 0. The shape of the system in one minute

- Two processes run the same code (`src/composition.py` wires both):
  - **api** (`src/api/app.py`) — FastAPI; serves the reseller + operator GraphQL schemas
    and the inbound ERP webhook. It *writes events* and *reads projections*. It does no ERP
    I/O itself.
  - **worker** (`src/worker/main.py`) — no HTTP; runs the async consumers, the outbox relay,
    and the reconciliation scheduler. It does the ERP I/O and builds the read models.
- **The transactional aggregates are event-sourced** — `Order`, and the fulfillment family
  (`Shipment`, `Invoice`), all on one shared `events`/`outbox`/`snapshots`
  store keyed by `aggregate_type` + `stream_id` (ADR-0002, amended by ADR-0014). Their state
  is the replay of their events. Reference/config data (connections, items, bindings, quotes,
  subsidiaries, webhook endpoints) is ordinary rows.
- **Writes go through events; reads go through projections** (CQRS). A GraphQL query never
  replays the event store — it reads the `orders` projection table.
- **Nothing is dual-written.** An aggregate's events and their **outbox** rows commit in one
  DB transaction. A relay publishes the outbox to an SNS FIFO topic; SQS FIFO queues fan it
  out to consumers. Cross-aggregate effects are **event-driven sagas**, not shared
  transactions (ADR-0018).

```
GraphQL mutation ─▶ Order aggregate ─▶ events + outbox (one tx) ─▶ relay ─▶ SNS topic
                                                                              │ fan-out
                      ┌───────────────────────────┬───────────────────────────┼───────────────┐
             order-processing.fifo        order-delivery.fifo         order-fulfillment.fifo   projections.fifo
             (validate + route)           (submit to the ERP)         (apply shipment/invoice) (build read models)
```

---

## 1. Setup data (must exist before any order)

These are reference/config rows an operator creates; none are event-sourced (unlike the
`Order` and the shipment/invoice/payment/return aggregates below). IDs below are reused
throughout the walkthrough.

| Table | Row (example) | Who provides it |
|---|---|---|
| `erp_connections` | `conn_odoo_eu` — `erp_type=ODOO`, `base_url=https://eu.odoo.example.com`, `credentials={"database":"odoo_eu","username":"admin"}`, `secret_ref=prod:odoo-eu-login`, `webhook_secret_ref=prod:odoo-eu-webhook`, `status=ACTIVE` | Operator |
| `tenant_connection_bindings` | `bnd_771` — `tenant_id=tnt_acme`, `connection_id=conn_odoo_eu`, `erp_customer_id=CUST-9`, `status=VERIFIED` | Operator (customer id comes from the ERP) |
| `items` | `item_anvil` — `sku=ANVIL-100`, `owning_connection_id=conn_odoo_eu`, `kind=PHYSICAL` | Operator |
| `subsidiaries` | `sub_eu` — `name=Acme Distribution EU`, `country=DE`, `language=de` | Operator |
| `quotes` | `qot_55` — `tenant_id=tnt_acme`, `subsidiary_id=sub_eu`, end customer `Downstream GmbH`/`Berlin`, `currency=USD`, valid `2026-01-01..2026-12-31`, `status=ISSUED`, lines `[{ANVIL-100, 19.99 USD, EA, tax VAT 0.20}]` | Operator |

Secrets are **pointers** (`secret_ref`), resolved from Secrets Manager at call time — the
raw credential is never stored in Postgres. The inbound-webhook secret is a *different*
secret from the login one on purpose (leaking the webhook URL can't log into the ERP).

---

## 2. Direction 1 — reseller places an order → it reaches the ERP

### 2.1 The request (GraphQL, reseller schema)

```graphql
mutation {
  placeOrder(
    quoteId: "qot_55",
    clientReference: "PO-2024-1182",
    lines: [{ productKey: "ANVIL-100", quantity: 2 }]
  )
}
```

The reseller sends **only** SKU + quantity + the quote to reply to. No price, no unit of
measure, no customer id — all of that is resolved server-side.

### 2.2 Price resolution from the quote (no storage — pure logic)

Before any event is written, `OrderService.place_order` resolves each line against
`qot_55`: unit price, unit of measure, tax and discount are copied from the quote line; the
line's `kind` is copied from the `items` catalog; a stable `line_id` is generated. A line
not on the quote, or a quote that's missing / not `ISSUED` / out of its window, raises
`PriceNotQuoted` / `QuoteNotFound` / `QuoteNotValid` and **no order is created**.

Resolved line: `{line_id: "ol_3f2a", product_key: "ANVIL-100", quantity: "2", unit_of_measure: "EA", kind: "PHYSICAL", unit_price: {amount:"19.99", currency:"USD"}, tax_rates:[{code:"VAT", rate:"0.20", inclusive:false}], line_discount: null}`.

### 2.3 Event: `OrderSubmitted` → state `SUBMITTED`

The aggregate emits one event; it and its outbox row commit together.

```json
// events row (stream_id = order_id = "ord_8f3c1a90", version 1), payload:
{
  "order_id": "ord_8f3c1a90",
  "tenant_id": "tnt_acme",
  "client_reference": "PO-2024-1182",
  "lines": [{ "line_id": "ol_3f2a", "product_key": "ANVIL-100", "quantity": "2",
              "unit_of_measure": "EA", "kind": "PHYSICAL",
              "unit_price": {"amount": "19.99", "currency": "USD"},
              "tax_rates": [{"code": "VAT", "rate": "0.20", "inclusive": false}],
              "line_discount": null }],
  "product_keys": ["ANVIL-100"],
  "quote_id": "qot_55", "subsidiary_id": "sub_eu",
  "end_customer_name": "Downstream GmbH", "ship_to": "Berlin"
}
```

**Intermediate records written now:** one `events` row + one `outbox` row (same tx). The
GraphQL call returns `ord_8f3c1a90` here — everything below is asynchronous.

### 2.4 The relay publishes, and `order-processing` routes

The outbox relay publishes the event to the SNS FIFO topic (`MessageGroupId = order_id`,
`MessageDeduplicationId = event_id`). The `order-processing.fifo` queue (filter:
`OrderSubmitted`, `OrderAmended`) delivers it to `OrderProcessor.handle`, which:

1. **Routes** (`resolve_owning_connection`, pure): every line's `owning_connection_id` from
   `items` must agree (else reject `mixed_erp`), and the tenant must have a `VERIFIED`
   binding to it (else reject `no_binding`). Routing is a *lookup* of data that already
   exists, not a new decision.
2. On success it drives the aggregate `validate(conn) → accept()`; on failure `reject(...)`.

| Event | State after | What it changes |
|---|---|---|
| `OrderValidated` `{owning_connection_id: "conn_odoo_eu"}` | `VALIDATED` | records which connection owns the order |
| `OrderReadyForDelivery` `{owning_connection_id: "conn_odoo_eu"}` | `ACCEPTED` | "routed, ready to send". *(The event type keeps its old name even though the state was renamed `ACCEPTED` — renaming a persisted event type would rewrite stored history.)* |
| *or* `OrderRejected` `{reason_code, reseller_message}` | `REJECTED` | terminal; reseller sees why |

### 2.5 `order-delivery` submits to the ERP

`OrderReadyForDelivery` is also filtered to the `order-delivery.fifo` queue →
`DeliveryHandler.handle`. It reads the order's payload from the projection, resolves the
`ErpTarget` (base_url + credentials + resolved secret) for `conn_odoo_eu`, and calls the
adapter. The **canonical → Odoo** mapping (`odoo_adapter.py`, pure translation, no storage):

| Canonical | Odoo field | Example / rule |
|---|---|---|
| `order_id` (the idempotency key) | `sale.order.client_order_ref` | `ord_8f3c1a90` — searched before create, so a retry never double-creates |
| binding `erp_customer_id` | `sale.order.partner_id` | `CUST-9` — used directly; no name-based auto-create |
| `line.product_key` | `product.product.default_code` | `ANVIL-100` |
| `line.quantity` | `order.line.product_uom_qty` | `2` |
| `line.unit_price` net of `line_discount` | `order.line.price_unit` | `19.99` |
| `line.unit_of_measure` | `order.line.product_uom` | looked up by name in `uom.uom`; omitted (Odoo default) if no match |
| `line.tax_rates[].code` | `order.line.tax_id` | looked up by name in `account.tax`; omitted if no match |

On success the handler drives `send_to_erp(erp_order_id)`:

| Event | State after | What it changes |
|---|---|---|
| `OrderSentToErp` `{erp_order_id: "S00042"}` | `SENT_TO_ERP` | stores Odoo's own order number; `(owning_connection_id, erp_order_id)` is how Direction 2 finds this order again |

On a **transient** failure it drives `mark_retrying(attempt, next_retry_at)` →
`OrderRetrying` → state `RETRYING`; SQS redrive/backoff retries, and a poison message
lands in `order-delivery-dlq.fifo` after `maxReceiveCount` (5).

### 2.6 Projection catches up (every event)

The `projections.fifo` queue receives **all** events → `OrderProjector`, which maintains the
read models the GraphQL API serves:
- `orders` — one row per order: `state`, `owning_connection_id`, `erp_order_id`, the lines
  with `line_total` (`quantity × unit_price`, computed here), `subtotal`, and the three
  scores.
- `order_status_history` — the reseller-visible timeline (one row per lifecycle step),
  which *is* the formatted event list.

Consumers dedupe on `event_id` via `processed_events(consumer, event_id)` before applying,
so at-least-once redelivery is safe.

---

## 3. The fulfillment saga — recording a shipment or invoice (ADR-0018)

This is the newest piece and the one most worth understanding. Recording a shipment does
**not** touch the order in the same call — it's an event-driven saga across two aggregates.

### 3.1 Where a shipment comes from

The reconciliation sweeper asks the ERP adapter for done deliveries and posted customer
invoices, and records each one once, keyed by the ERP's own id. Odoo reads `stock.picking`
and `account.move`. An adapter for an ERP that has neither returns an empty list. The
portal does not record shipments or invoices.

### 3.2 What recording a shipment does — and does *not* do

`ShipmentService.record_once` saves a **`Shipment`** aggregate (its own event stream) and
nothing else. A later poll of the same picking or invoice does not append another event.
A shipment emits:

```json
// ShipmentRecorded (stream = shipment id "shp_7"), payload:
{ "shipment_id": "shp_7", "order_id": "ord_8f3c1a90",
  "lines": [{"line_id": "ol_3f2a", "quantity": "2"}],
  "carrier": "UPS", "tracking_number": null, "proof_of_delivery": null }
```

The order is **not** loaded or modified here. `InvoiceService.record_once` does the same
for `InvoiceRecorded`.

### 3.3 The ordering side reacts (the saga consumer)

`ShipmentRecorded`/`InvoiceRecorded` are published to the topic and filtered to the
`order-fulfillment.fifo` queue → `OrderFulfillmentConsumer` (in the `ordering` module). It
depends only on the **event-type string and payload shape** — it does not import the
shipment/invoice modules at all (that decoupling is what lets those modules be extracted).
It loads the `Order` and applies, per line:

| Event consumed | Order command | Event emitted | What it changes |
|---|---|---|---|
| `ShipmentRecorded` | `order.record_fulfillment(line_id, qty, carrier, proof_of_delivery)` | `OrderLineFulfilled` | **additive** shipped quantity for the line; also derives the *delivered* fact |
| `InvoiceRecorded` | `order.record_invoice(line_id, qty)` | `OrderLineInvoiced` | **additive** invoiced quantity for the line |

The order must already be `CONFIRMED` (or `CLOSED`) to accept these — recording against an
unconfirmed order makes the consumer raise, the message retries, and (if it never confirms)
dead-letters. Record shipments only after the ERP has confirmed the order.

The **delivered** rule (`line_is_delivered`, the single source of truth shared by aggregate
and projection): a `LICENSE` line is delivered the instant it ships; a `PHYSICAL` (box) line
is delivered only once a `carrier` **or** `proof_of_delivery` is present.

`OrderLineFulfilled`/`OrderLineInvoiced` then flow to the `projections` queue like any other
event, so the reseller's `fulfillmentStatus` / `deliveryStatus` / `invoiceStatus` update.

### 3.4 Why it's a hop, not an instant

Between the shipment being saved and the order's score updating there is one bus/queue
hop. Locally (`APP_PROFILE=memory`) the API drains the in-memory bus inline so it looks
synchronous in tests; on Postgres/AWS the worker consumes it (sub-second to queue-speed).
A failure after the shipment is saved but before the order consumer succeeds is self-healed
by at-least-once redelivery + the `processed_events` dedupe; a persistent failure dead-letters
to `order-fulfillment-dlq.fifo`. This is the deliberate eventual-consistency trade that lets
`shipment`/`invoicing` be independent of `ordering` (see ADR-0018).

### 3.5 The scores, derived (never set directly)

Given the order line `ol_3f2a` ordered `2`:

| Recorded so far | `fulfillmentStatus` | `deliveryStatus` (box, carrier=UPS) | `invoiceStatus` |
|---|---|---|---|
| nothing | UNFULFILLED | NOT_DELIVERED | NOT_INVOICED |
| shipment qty 1 | PARTIALLY_FULFILLED | PARTIALLY_DELIVERED | NOT_INVOICED |
| shipment qty 2 total | FULFILLED | DELIVERED | NOT_INVOICED |
| invoice qty 2 | FULFILLED | DELIVERED | INVOICED |

The order's **lifecycle `state` never changes** through any of this — the scores are an
orthogonal axis (ADR-0014).

---

## 4. Direction 2 — ERP status change → reseller notified

### 4.1 Inbound (webhook preferred, polling as fallback)

The ERP calls `POST /erp/webhook/{connection_id}/{webhook_secret}` (Odoo's shared-secret
route; ERPNQ-style ERPs use the HMAC-signed route). Body:

```json
{ "erp_order_id": "S00042", "state": "sale", "invoice_status": "to invoice", "event_id": "4821_17" }
```

`InboundWebhookService` authenticates the secret, dedupes on `event_id`, finds the order by
`(connection_id, erp_order_id)`, and applies the mapped status. If a connection has no
webhook configured, the **reconciliation sweeper** polls `adapter.fetch_status` for every
open order on a schedule (`RECONCILE_INTERVAL_SECONDS`) and applies status the same way — so
status converges either way; the webhook only lowers latency.

### 4.2 Status conversion (native → canonical, pure — `status_mapping.py`)

`CanonicalStatus` (now in `src/shared/canonical_status.py`, so `sales` doesn't depend on
`integration`) has exactly three values an ERP poll/webhook can drive:

| Odoo `state` | Odoo `invoice_status` | Canonical | Order command | Event |
|---|---|---|---|---|
| `sale` or `done` | not `invoiced` | `CONFIRMED` | `order.confirm()` | `OrderConfirmed` → `CONFIRMED` |
| any | `invoiced` | `CLOSED` | `order.close()` | `OrderClosed` → `CLOSED` |
| `cancel` | any | `CANCELLED` | `order.cancel(...)` | `OrderCancelled` → `CANCELLED` |
| anything else | | *(none)* | — | no transition (acknowledged, no-op) |

`StatusApplier` advances through valid intermediate transitions and **ignores stale /
backward** updates (the lifecycle is monotonic), so out-of-order or duplicate webhooks are
safe. Note `done` maps to `CONFIRMED`, not a "fulfilled" lifecycle state — delivery is a
score/fact now, not a lifecycle step (FR-A6).

### 4.3 Order lifecycle — every transition and its guard

`OrderState` moves forward through a fixed sequence, with two exits (`REJECTED`,
`CANCELLED`) that can interrupt it from most points. Every transition is guarded on the
aggregate (`Order` methods in `ordering/domain/aggregate.py`) — calling one from the wrong
state raises `OrderInvalidTransition`, it never silently does nothing (except the two
documented idempotent no-ops below).

```
SUBMITTED ──validate()──▶ VALIDATED ──accept()──▶ ACCEPTED ──send_to_erp()──▶ SENT_TO_ERP ──confirm()──▶ CONFIRMED ──close()──▶ CLOSED
    │                         │                       │                           │
    │                         │                       └──mark_retrying()──▶ RETRYING ──send_to_erp()──▶ SENT_TO_ERP
    │                         │                                                   (send_to_erp() also re-enters from RETRYING)
    └──reject()────────▶ REJECTED (terminal)                        cancel() reaches CANCELLED from any non-terminal state
```

| Transition | Command | Guard (valid only from) | What actually triggers it |
|---|---|---|---|
| → `SUBMITTED` | `Order.submit(...)` | *(genesis)* | `placeOrder` mutation |
| `SUBMITTED` → `VALIDATED` | `validate(owning_connection_id)` | `SUBMITTED` | `OrderProcessor` resolved routing successfully (one connection owns every line, tenant has a verified binding) |
| `VALIDATED` → `ACCEPTED` | `accept()` | `VALIDATED` | same `OrderProcessor` pass, immediately after `validate()` |
| `SUBMITTED` or `VALIDATED` → `REJECTED` | `reject(reason_code, message)` | `SUBMITTED`, `VALIDATED` | `OrderProcessor` routing failed — `reason_code` is one of `empty_order`, `unknown_item`, `mixed_erp`, `no_binding` |
| `ACCEPTED` or `RETRYING` → `SENT_TO_ERP` | `send_to_erp(erp_order_id)` | `ACCEPTED`, `RETRYING` | `DeliveryHandler`: the ERP adapter's `submit()` returned success |
| `ACCEPTED`, `RETRYING`, or `SENT_TO_ERP` → `RETRYING` | `mark_retrying(attempt, next_retry_at)` | `ACCEPTED`, `RETRYING`, `SENT_TO_ERP` | `DeliveryHandler`: `submit()` failed with a transient (`terminal=False`) error — the message is also re-raised so the queue redrives it |
| *(any)* → `REJECTED` | `reject("erp_rejected"/"connection_unavailable"/"order_not_found", ...)` | not already terminal | `DeliveryHandler`: `submit()` failed with `terminal=True`, or the target connection/order payload couldn't be resolved at all |
| `SENT_TO_ERP` → `CONFIRMED` | `confirm()` | `SENT_TO_ERP` (idempotent no-op if already `CONFIRMED`) | inbound ERP webhook/reconcile reports a native status that maps to `CanonicalStatus.CONFIRMED` |
| `CONFIRMED` → `CLOSED` | `close()` | `CONFIRMED` (idempotent no-op if already `CLOSED`) | inbound ERP webhook/reconcile reports `CanonicalStatus.CLOSED` |
| *(any non-terminal)* → `CANCELLED` | `cancel(reason)` | not already terminal (`CLOSED`/`CANCELLED`/`REJECTED`) | the reseller's `cancelOrder` mutation, **or** the ERP reports `CanonicalStatus.CANCELLED` (`reason="cancelled in ERP"`) |

**Orthogonal to all of the above** (gated only by `state in {CONFIRMED, CLOSED}`, never
changes `state` itself): `record_fulfillment(...)` and `record_invoice(...)` — these drive
the three independent scores (§3.5), not the lifecycle.

### 4.4 Outbound notification to the reseller (optional) — every dispatchable event

Eight event types are filtered to `webhook-dispatch.fifo` → `WebhookDispatchService`
(`DISPATCHABLE_EVENT_TYPES`), which POSTs to each active reseller endpoint registered for
that event. **The body shape is identical for all eight** — `WebhookDispatchService`
never includes an event's own extra fields (no `reason_code`, no `carrier`, no `attempt`);
it only ever sends the event's name/id plus the order's current id/number/status. A
reseller who needs an event's specific detail (why it was rejected, which carrier shipped
it) has to follow up with a GraphQL query — the webhook is a "something changed, go look"
nudge, not a full payload.

```http
POST https://acme.example.com/hooks/orders
X-Signature: t=1735689600,v1=9f86d08...   # HMAC-SHA256 over "t.body" with the endpoint secret
Content-Type: application/json

{ "event": "<name below>", "eventId": "evt_a9f3", "occurredAt": "2026-10-05T09:12:03Z",
  "order": { "id": "ord_8f3c1a90", "number": "PO-2024-1182", "status": "<see §4.3>" } }
```

| Event | Sent when | `order.status` at that moment |
|---|---|---|
| `OrderSentToErp` | the ERP adapter accepted the order (`send_to_erp`, §4.3) | `SENT_TO_ERP` |
| `OrderConfirmed` | the ERP reported `CanonicalStatus.CONFIRMED` | `CONFIRMED` |
| `OrderClosed` | the ERP reported `CanonicalStatus.CLOSED` | `CLOSED` |
| `OrderRejected` | routing failed at submission, **or** the ERP adapter failed terminally | `REJECTED` |
| `OrderRetrying` | the ERP adapter failed transiently; will be retried automatically | `RETRYING` |
| `OrderCancelled` | the reseller's `cancelOrder` mutation, or the ERP reported `CanonicalStatus.CANCELLED` | `CANCELLED` |
| `ShipmentRecorded` | the sweeper recorded a done ERP delivery | whatever the order's lifecycle status already was — this event never changes it |
| `InvoiceRecorded` | the sweeper recorded a posted ERP customer invoice | same — lifecycle status unaffected |

Each delivery attempt is tracked in `webhook_deliveries` (`DELIVERED` / `RETRYING` /
`FAILED`, with an attempt count); transient failures raise for SQS redrive, and the
delivery is marked `FAILED` after `MAX_ATTEMPTS` (5). The reseller reads these via the
`deliveryLog` query.

---

## 5. The event catalog (every Order event, plus the two cross-aggregate events resellers get notified about)

"Dispatched" means it's one of the eight in `DISPATCHABLE_EVENT_TYPES` (§4.4) — the
reseller's webhook endpoint hears about it. Everything else is visible only by reading the
order back over GraphQL.

| Event | Emitted by | Payload (beyond `order_id`) | Effect when applied | Dispatched to reseller? |
|---|---|---|---|---|
| `OrderSubmitted` | `placeOrder` | tenant, client_reference, lines, product_keys, quote/party fields | creates the order, `SUBMITTED` | No |
| `OrderValidated` | routing | `owning_connection_id` | `VALIDATED`, records owner | No |
| `OrderReadyForDelivery` | routing | `owning_connection_id` | `ACCEPTED` | No |
| `OrderRejected` | routing or delivery | `reason_code`, `reseller_message` | `REJECTED` (terminal) | **Yes** |
| `OrderSentToErp` | delivery | `erp_order_id` | `SENT_TO_ERP` | **Yes** |
| `OrderRetrying` | delivery | `attempt`, `next_retry_at` | `RETRYING` | **Yes** |
| `OrderConfirmed` | status in | — | `CONFIRMED` | **Yes** |
| `OrderClosed` | status in | — | `CLOSED` | **Yes** |
| `OrderCancelled` | reseller / status in | `reason` | `CANCELLED` | **Yes** |
| `OrderLineFulfilled` | fulfillment saga | `line_id`, `quantity`, `carrier?`, `proof_of_delivery?` | adds shipped qty; derives delivered | No (the sibling `ShipmentRecorded` is, see below) |
| `OrderLineInvoiced` | fulfillment saga | `line_id`, `quantity` | adds invoiced qty | No (the sibling `InvoiceRecorded` is) |
| `OrderLineVendorDateSet` | `setVendorDate` | `line_id`, `vendor_date` | sets the line's "scheduled" date | No |
| `OrderFulfilled` | — (legacy) | — | **no-op**; retained only so pre-Increment-5 streams still replay | No |
| `ShipmentRecorded` *(Shipment aggregate, not Order)* | ERP delivery poll | `order_id`, lines, `carrier?`, `tracking_number?`, `proof_of_delivery?`, `tenant_id` | triggers the saga that applies `OrderLineFulfilled` to the order | **Yes** |
| `InvoiceRecorded` *(Invoice aggregate, not Order)* | ERP invoice poll | `order_id`, lines, `erp_invoice_id?`, `tenant_id` | triggers the saga that applies `OrderLineInvoiced` to the order | **Yes** |

---

## 6. Where to go deeper

- The exact tables/columns these events land in: [database-schema.md](database-schema.md).
- Which aggregates are event-sourced (and why reference data isn't), and what CQRS means
  here: [event-sourcing-explained.md](event-sourcing-explained.md).
- Rich-vs-thin webhooks and multi-instance/tenant routing:
  [erp-integration-patterns.md](erp-integration-patterns.md).
- Adding a new ERP (the adapter + registry + the four touch points):
  [adding-an-erp.md](adding-an-erp.md); Odoo specifics in [erps/odoo.md](erps/odoo.md).
- The reasoning behind the big moving parts: the [ADR log](adr/README.md) — especially
  0002 (event-source Order only), 0014 (orthogonal scores), 0016 (price from quote),
  0017 (module grouping), 0018 (the fulfillment saga).
- Run it yourself: [local-setup.md](local-setup.md).
