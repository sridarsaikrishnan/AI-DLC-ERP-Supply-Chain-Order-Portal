# Increment 5 — Functional Design

Decisions resolved: Q1–Q7 = A (see `inception/requirements/increment5-questions.md`). Backend + GraphQL only (Q6=A). Extends existing units (`ordering`, `catalog`, `fulfillment`, `integration`, `tenancy`) + one new reference concept `quoting`; no new deployable unit (no Units Generation).

## New domain concept: `quoting` (CRUD, operator-authored — ADR-0002 keeps event-sourcing to Order)

### Subsidiary ("subsidiary record", FR-C3)
`subsidiary_id, name, country, language`. A plain row; one seeded by default (Q5=A). Referenced by quotes and copied onto orders so document numbers and email locale have a home. No "profile service".

### Quote (FR-B1/B2/B3)
`quote_id, tenant_id (reseller), subsidiary_id, end_customer{name, ship_to}, currency, valid_from, valid_until, status(DRAFT|ISSUED|EXPIRED|ACCEPTED), lines[]`.
- `QuoteLine`: `product_key, unit_price: Money, tax_rate: TaxRate|None, line_discount: Money|None, unit_of_measure`.
- Validity window = "how long the prices hold". `is_valid_at(now)` = `ISSUED` and `valid_from <= now <= valid_until`.
- A quote is reseller-safe: it carries no ERP identity. `erp_customer_id` stays on the binding (operator-only).

### Price resolution (FR-B3, reverses ADR-0011/0013)
`OrderService.place_order(tenant_id, quote_id, line_inputs[])`:
1. Load quote; refuse if missing, wrong tenant, or not valid now (`QuoteNotValid`).
2. For each ordered line, find the quote line by `product_key`; refuse the whole order if any line has no quoted price (`PriceNotQuoted`).
3. Build `OrderLine`s with price/tax/discount **copied from the quote**, `kind` copied from the catalog item, and a freshly generated `line_id`.
4. Copy `end_customer`, `ship_to`, `subsidiary_id`, `quote_id` onto the order (via `OrderSubmitted`).

Catalog `Item` drops `unit_price/tax_rate/line_discount`; keeps `item_id, sku, name, owning_connection_id, kind`. `OrderService` no longer depends on `PriceCatalog`; it depends on a `QuoteDirectory` (read quote) + the item repo (read `kind`).

## `ordering` changes

### OrderLine (FR-A3, D1)
Add `line_id: str` (stable, generated at placement, in to_dict/from_dict) and `kind: ItemKind` (PHYSICAL|LICENSE, copied from catalog at placement). Pricing fields already exist.

### OrderState (FR-A6, Q2=A, Q3=A)
- Rename member `READY_FOR_DELIVERY` → `ACCEPTED` (value `"ACCEPTED"`). Keep the **persisted event type** `OrderReadyForDelivery` unchanged (historical fact); `restore()` tolerates a legacy `"READY_FOR_DELIVERY"` snapshot value → `ACCEPTED`.
- Remove `FULFILLED` from `OrderState`. Lifecycle is now `SUBMITTED → VALIDATED → ACCEPTED → SENT_TO_ERP → CONFIRMED → CLOSED` (+ REJECTED/RETRYING/CANCELLED). `close()` now requires `CONFIRMED`. `OrderFulfilled` event class is retained as a **no-op apply** for replay safety; nothing emits it anymore.
- `FULFILLED` survives only as `FulfillmentStatus.FULFILLED` (the quantity score).

### Scores + shipped/delivered facts (FR-A5, D2/D3)
Order tracks three per-line maps keyed by `line_id`: `shipped_qty_by_line`, `delivered_qty_by_line`, `invoiced_qty_by_line`.
- `fulfillment_status` (the shipped-quantity "score"): UNFULFILLED/PARTIALLY_FULFILLED/FULFILLED from `shipped_qty_by_line`.
- `invoice_status`: NOT_INVOICED/PARTIALLY_INVOICED/INVOICED from `invoiced_qty_by_line`.
- `delivery_status` (new `DeliveryStatus`): NOT_DELIVERED/PARTIALLY_DELIVERED/DELIVERED from `delivered_qty_by_line`.
- Derivation rule (D2): on `record_fulfillment(line_id, qty, carrier, proof_of_delivery)`, shipped += qty; delivered += qty **iff** the line's `kind == LICENSE` **or** `carrier`/`proof_of_delivery` is present. "Shipped" and "delivered" are therefore different facts (D3).
- Both scores + delivery_status are added to `ResellerOrderView` **and** `OperatorOrderView`, projected from `OrderLineFulfilled`/`OrderLineInvoiced` (the projector currently ignores them — fixed).

### Vendor date (FR-E1)
`OrderLine` gains nothing; instead a per-line `vendor_date_by_line: dict[line_id, str]` fed by a new `OrderLineVendorDateSet` event via `set_vendor_date(line_id, date)` (operator/purchasing command). "scheduled" is the presence of that date. No Vendor Order entity (FR-E2).

## `fulfillment` changes (FR-A4)
`FulfillmentRecorded` lines carry `line_id`; `Fulfillment` gains `proof_of_delivery`. `FulfillmentService.record` writes the `Fulfillment` append and the `Order` quantity-update append **in one transaction** via a new `UnitOfWork` port:
- `NullUnitOfWork` (memory/tests): no-op context.
- `PostgresUnitOfWork` (engine thread-local session): `PostgresEventStore.append` joins the ambient session when one is active and defers commit to the UoW; otherwise unchanged (own session + commit).

## `integration` changes (FR-A1/A2)
- Order payload (`OrderReaderAdapter.read_payload`) adds `order_id`, `erp_customer_id` (looked up from the binding via a new `CustomerDirectory` port over tenancy), and drops `partner_name`-as-reference.
- `OdooAdapter.submit`: idempotency search/write keys on `client_order_ref = order_id` (not `client_reference`). Partner = `int(erp_customer_id)` directly (no name-based auto-create); missing `erp_customer_id` is a terminal error.
- `status_mapping`: Odoo `done` no longer maps to a lifecycle state (FULFILLED removed); `sale→CONFIRMED`, `invoice_status=invoiced→CLOSED`, `cancel→CANCELLED`. `CanonicalStatus.FULFILLED` removed; `StatusApplier` progression becomes `CONFIRMED→CLOSED`.

## GraphQL
- Reseller `ResellerOrder`: add `fulfillmentStatus`, `invoiceStatus`, `deliveryStatus`; per line `shipped`/`delivered`/`scheduledDate`. `placeOrder` takes `quoteId` + line inputs (no price). New `quotes`/`quote` queries (reseller-safe). Still no ERP identity (FR-19).
- Operator: `recordFulfillment(orderId, lineId, quantity, carrier, proofOfDelivery)`, `setVendorDate(orderId, lineId, date)`; quote/subsidiary admin mutations (`createSubsidiary`, `issueQuote`); item `kind` on `syncItem`/`ItemType` (no price args anymore).

## Migrations (next: 0008)
`0008_increment5`: `subsidiaries`, `quotes`, `quote_lines`; `items` drop price/tax/discount + add `kind`; `orders.lines` JSONB gains `line_id`/`kind`; order projection columns for scores/delivery/parties/quote_ref/vendor dates. Dev/PoC data stance: no backfill of dropped price columns (consistent with prior increments).
