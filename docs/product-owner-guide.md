# Product owner guide

What the platform does today, in business terms — every capability it supports, the rules
that govern them, and what it deliberately does **not** do yet. If you want to see how any
of this is implemented, the [developer guide](developer-guide.md) traces it end to end.

## What it is

**AdminOps** is the distributor's application. Sales writes the quotation in the **ERP**
(Odoo today). AdminOps reads that sales order, then confirmation, delivery, and invoice,
and lists every order and every notification sent to a reseller. There is no reseller
screen. The reseller receives the webhook on their own system. Odoo itself is sometimes
called a portal. This product is not that.

## Who uses it

- **Distributor** — signs in to AdminOps. Sees every reseller's orders, every ERP id, and
  every notification that was sent, including which reseller it went to.
- **Reseller** — a customer of the distributor. Not a user of AdminOps. Their own system
  receives the signed webhook.

## The core workflow

```
ERP sales order for a bound customer  ──▶  AdminOps adopts it
                                              │
AdminOps shows status + scores  ◀──  ERP status flows back (webhook / polling) ◀┘
ERP deliveries and invoices  ──▶  AdminOps shows shipped / delivered / invoiced
                                      and lists the notification sent to the reseller
```

An order is always a reply to a quote. The quote carries the prices, how long they hold,
the end customer and where the goods go. The catalog only says *what a product is*.

## Features supported today

### Quoting
Sales writes the quotation in the ERP. In Odoo that quotation and the sales order are the
same `sale.order`. AdminOps does not issue the quotation.

### Ordering
The worker reads each verified reseller's sales orders from that ERP. A line needs an
Internal Reference, a quantity above zero, and a price. The order is kept only when the
quotation's company id matches the subsidiary registered on that connection. Each line
keeps its own id through shipping and invoicing.

### Routing
One ERP instance is one connection, and one connection belongs to one subsidiary. A
reseller who buys from two instances has two bindings, each with that instance's own
customer id. The same records are what a later purchase order would use, in the other
direction. That create call is not built yet.

### Order lifecycle (what AdminOps shows as "status")
`Submitted → Validated → Accepted → Sent to ERP → Confirmed → Closed`, plus `Rejected`,
`Retrying`, and `Cancelled`. See the [glossary](#glossary-statuses) for what each means.

### Shipment, delivery and invoicing (three independent "scores")
Separate from the lifecycle status, each order carries three progress scores derived from
what's been recorded against its lines:
- **Fulfillment (shipped)**: `Unfulfilled → Partially fulfilled → Fulfilled`.
- **Delivery**: `Not delivered → Partially delivered → Delivered`. A **box** (physical
  item) counts as delivered only once a carrier or proof-of-delivery is recorded; a
  **license** counts as delivered the moment it ships.
- **Invoicing**: `Not invoiced → Partially invoiced → Invoiced`.

A done delivery in the ERP becomes a shipment, and a posted customer invoice becomes an
invoice (partial quantities included). The scores move accordingly and are additive. A
repeat poll of the same ERP document does not add the quantity again.

### Vendor date ("scheduled")
When purchasing buys a line from the maker, the distributor records a vendor date on
that line in AdminOps. That date is what "scheduled" means.

### Status feedback from the ERP
- **How an order arrives**: a reconciliation sweep polls each ERP. That is the live path.
- **Status after that**: the same sweep reads confirmation, done deliveries, and posted
  customer invoices. An inbound webhook can apply a status change as well. Odoo uses a
  shared-secret URL.

### Outbound notifications (optional, per reseller)
- A reseller can register one or more webhook endpoints to be notified of order status
  changes. A notification is recorded, with its order, only once that delivery succeeds.
  AdminOps lists those, for every reseller. A status change with no endpoint is not a notification.
- Those deliveries cover lifecycle changes (sent to ERP, confirmed, closed, rejected,
  retrying, cancelled) and a recorded shipment or invoice.

### What AdminOps shows
- **Notifications** — every webhook sent to a reseller, with that reseller's id. Open a row to see the order.
- **Orders** — every reseller's orders, ERP ids included, and the timeline on each order.
- **Subsidiaries** — name, country, language, the one connection that subsidiary uses, and the ERP company id.
- **ERP connections** — register, pause, and resume an instance.
- **Resellers** — the binding to a connection and that instance's customer id, and whether it is verified.
- **Failed messages** — deliveries and other work that did not succeed, across every reseller.

## Rules & assumptions worth knowing

- **No price without a quote.** This is the rule that makes the product a distributor tool.
- **AdminOps shows ERP identity** (which instance, which order, which customer). The
  reseller's own webhook receiver is a different surface and does not get that identity.
- **Status is eventually consistent.** After the ERP changes a delivery or an invoice,
  AdminOps updates within the time it takes a background worker to
  process the event (sub-second locally; as fast as the queue in production) — not in the
  same instant. This is a deliberate design trade for reliability and scale.
- **Money is exact** (no floating-point drift) and single-currency per order/quote.
- **One ERP is live today: Odoo.** The system is built so adding the next one is a small,
  contained change, but only Odoo is implemented and verified.

## Not supported yet (deliberately deferred, not forgotten)

Each of these is a real, scoped future increment — called out so it's a decision, not a
surprise:

- **A second ERP** (SAP, ERPNext, NetSuite, …). The design supports it; no second adapter
  is written yet.
- **Credit notes.** A posted customer invoice is pulled from the ERP. A refund is not
  applied back onto the invoiced quantity.
- **A standalone Vendor Order document.** The vendor date exists; a separate purchase-order
  document with its own number does not.
- **Richer tax/pricing**: multi-jurisdiction tax, promotional/volume discount codes.
- **Richer logistics**: multi-warehouse inventory, lot/serial tracking, kitting/bills of
  material, recurring billing/subscriptions.
- **Self-service onboarding**: resellers and connections are set up by an operator; there is
  no reseller self-signup.

## Glossary (statuses)

### Lifecycle status
| Status | Meaning |
|---|---|
| **Submitted** | The reseller placed the order; nothing has been routed yet. |
| **Validated** | The owning ERP connection was resolved and the reseller is allowed to use it. |
| **Accepted** | Routed and ready to send to the ERP. (Was "Ready for delivery".) |
| **Sent to ERP** | The order was handed to the ERP, which returned its own order number. |
| **Confirmed** | The ERP confirmed the order. |
| **Closed** | The ERP reported the order fully invoiced/finished. |
| **Rejected** | Couldn't be routed (no owning connection, mixed ERPs, or no verified binding). |
| **Retrying** | A transient failure talking to the ERP; the system is retrying. |
| **Cancelled** | Cancelled by the reseller (before confirmation) or in the ERP. |

### The three scores (independent of lifecycle status)
| Score | Values | Driven by |
|---|---|---|
| **Fulfillment** | Unfulfilled / Partially fulfilled / Fulfilled | Recorded shipments (quantity shipped vs ordered). |
| **Delivery** | Not delivered / Partially delivered / Delivered | A box needs carrier/proof-of-delivery; a license is delivered on ship. |
| **Invoicing** | Not invoiced / Partially invoiced / Invoiced | Recorded invoices (quantity invoiced vs ordered). |

### Other terms
- **Quote** — operator-issued, time-bound price list a reseller orders against.
- **Binding** — the verified link between a reseller and their customer record in one ERP.
- **Connection** — one configured ERP instance (one Odoo database, say).
- **Subsidiary** — the distributor's own entity issuing a quote: a name, country and
  language so documents and emails have a home.
- **Box vs. license** — a physical item that ships and must be delivered, vs. a digital item
  delivered the moment it ships.
