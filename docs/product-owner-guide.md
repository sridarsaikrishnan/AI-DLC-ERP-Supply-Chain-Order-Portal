# Product owner guide

What the platform does today, in business terms — every capability it supports, the rules
that govern them, and what it deliberately does **not** do yet. If you want to see how any
of this is implemented, the [developer guide](developer-guide.md) traces it end to end.

## What it is

A portal that lets a distributor's **resellers** place orders and track them, while the
distributor's **operators** run the catalog, pricing, customer links and ERP connections.
Orders are forwarded to the distributor's **ERP** (Odoo today) as the system of record, and
the ERP's status changes flow back to the reseller. The portal is the one front door in
front of (eventually) several ERPs, so a reseller never needs to know which ERP a product
actually lives in.

## Who uses it

- **Reseller** — a customer of the distributor. Places orders against quotes, tracks their
  status, and (optionally) receives webhook notifications. Sees only their own data, and
  never sees any ERP identity (which ERP, which instance, the ERP's own order/customer IDs).
- **Operator** (distributor admin) — issues quotes, manages the catalog and the
  subsidiaries, links resellers to their ERP customer records, registers ERP connections, and
  records shipments/invoices. Sees across all resellers, including ERP identity.

## The core workflow

```
operator issues a QUOTE  ──▶  reseller places an ORDER against it  ──▶  routed to the owning ERP
                                                                              │
reseller sees status + scores  ◀──  ERP status flows back (webhook / polling) ◀┘
ERP deliveries and invoices  ──▶  reseller sees shipped / delivered / invoiced
```

An order is always a reply to a quote. The quote carries the prices, how long they hold,
the end customer and where the goods go. The catalog only says *what a product is*.

## Features supported today

### Quoting (the price list a reseller orders against)
- An operator issues a quote to a specific reseller: the subsidiary issuing it, the
  end customer (name + ship-to), currency, a validity window (`valid_from`/`valid_until`),
  and priced lines (unit price, unit of measure, optional tax rate and per-unit discount).
- Prices live **only** on the quote. A reseller can never set or override a price.

### Ordering
- A reseller places an order by referencing a quote and listing SKUs + quantities only — no
  price, no unit of measure (both come from the quote).
- The order is **refused** if: a line isn't on the quote, or the quote is missing, not in
  `ISSUED` status, or outside its validity window. (No price on file → no order.)
- Each order line gets its own stable ID, so two lines of the same SKU are tracked
  separately through shipping and invoicing.
- A reseller can cancel an order before it has been confirmed/closed by the ERP.

### Routing to the right ERP
- Which ERP an order goes to is decided by **which connection owns the items**, not by the
  reseller. Every line in one order must be owned by the same connection (an order spanning
  two ERPs is refused — one order, one ERP).
- The reseller must have a **verified binding** to that connection, else the order is
  refused. The order is sent to the ERP as the reseller's own customer record in that ERP
  (never a name-based guess).
- One reseller can be bound to several connections; several connections can be the same ERP
  type (e.g. an EU Odoo and a US Odoo) or different types — all at once.

### Order lifecycle (what the reseller sees as "status")
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
When purchasing actually buys a line from the maker, an operator records a vendor date on
that line. That date is what "scheduled" means to the reseller.

### Status feedback from the ERP
- **Primary**: the ERP calls an inbound webhook when an order's status changes
  (near-real-time). Odoo uses a shared-secret URL; other ERPs can use a signed webhook.
- **Fallback**: a reconciliation sweep polls each ERP on a schedule for open orders, so
  status still converges even if a webhook is missed or an ERP can't send one.

### Outbound notifications (optional, per reseller)
- A reseller can register one or more webhook endpoints to be notified of order status
  changes. Deliveries are HMAC-signed, retried on failure, and tracked in a delivery log
  the reseller can inspect.
- Notifications fire for **lifecycle** changes (sent to ERP, confirmed, closed, rejected,
  retrying). Shipment/invoice score changes are read via the API, not pushed.

### Operator administration
- Register / pause / resume ERP connections (with generic, per-ERP credential parameters).
- Link a reseller to their ERP customer id (the binding), and verify it.
- Manage the catalog: each SKU is owned by one connection and marked as a **box** or a
  **license**.
- Create subsidiaries (name, country, language).
- View every reseller's orders, the full timeline, and a cross-tenant failed-messages view.

## Rules & assumptions worth knowing

- **No price without a quote.** This is the rule that makes the product a distributor tool.
- **Resellers never see ERP identity** (which ERP/instance, ERP order/customer IDs). This is
  a hard boundary, not a display preference.
- **Status is eventually consistent.** After the ERP changes a delivery or an invoice, the
  reseller's view updates within the time it takes a background worker to
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
