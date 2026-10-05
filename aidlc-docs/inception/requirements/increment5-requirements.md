# Increment 5 — Requirements Analysis

Quote-before-order, named parties, box/license fulfillment, vendor dates, and order-truth fixes.

## Intent analysis

- **User request**: Five grouped changes (quoted verbatim in `audit.md`), to be done "in this order", following AI-DLC.
- **Request type**: Enhancement + partial refactor of accepted decisions (brownfield).
- **Scope**: Multiple components — `ordering`, `catalog`, `fulfillment`, `integration`, `tenancy`, plus a new `quoting` concept, projections, GraphQL (reseller + operator), migrations, Odoo adapter, docs. UI scope is a gated question (Q6).
- **Complexity**: Complex. It reverses two accepted ADRs (0011, 0013), demotes/renames persisted lifecycle states in an event-sourced store (needs event-versioning care), and introduces the first new top-level domain concept (Quote) since Increment 4.

## How the request decodes (plain reading of the five groups)

### Group A — "Make the order tell the truth" (order integrity)
- **FR-A1 — Customer identity to the ERP.** The order sent to the ERP must identify the customer by the reseller's `erp_customer_id` from the verified tenant↔connection binding (ADR-0005), not by a name-based auto-created partner. Today `OrderReaderAdapter.read_payload` sends `partner_name = client_reference` and `OdooAdapter._resolve_partner` searches/creates a partner **by name** — that is the untruth to fix.
- **FR-A2 — Idempotency key = platform order id.** ERP submission idempotency must key on the platform order id (`ord_…`), not the reseller's `client_reference`. The platform order id is the stable, globally-unique key; it is what gets written to the ERP (`client_order_ref`) and searched on retry. `client_reference` is a reseller's own PO text and is not guaranteed unique.
- **FR-A3 — Each line has its own id.** Every order line carries a stable `line_id`, generated at placement, surviving event replay, and used as the key for fulfillment/invoice quantity records (today they key on `product_key`, which collapses two lines of the same SKU).
- **FR-A4 — Shipment + quantities in one transaction.** Recording a shipment (`Fulfillment`) and the resulting order fulfilled-quantity update must commit atomically. Today `FulfillmentService.record` does two separate `repository.save` calls — a crash between them leaves a shipment with no quantity bump, or the reverse.
- **FR-A5 — Both scores on the reseller's order.** The reseller order view shows **both** the fulfillment score and the invoice score. Today neither the reseller nor the operator view carries them, and the projector ignores `OrderLineFulfilled`/`OrderLineInvoiced` entirely.
- **FR-A6 — Rename `READY_FOR_DELIVERY`; `FULFILLED` becomes a score only.** Remove `FULFILLED` from the order **lifecycle** enum (`OrderState`); keep `FULFILLED` only as a value of the quantity score (`FulfillmentStatus.FULFILLED`). Rename the internal `READY_FOR_DELIVERY` state, which is about readiness to send to the ERP and now collides with the new, literal meaning of "delivery" in Group D.

### Group B — "Put a quote in front of the order" (the distributor-tool change)
- **FR-B1 — Quote entity.** A Quote precedes an Order and records: the reseller it is for, the quoted items, their prices, a validity window ("how long the prices hold"), and a ship-to destination ("where the goods should go").
- **FR-B2 — Order replies to a quote.** An Order references the Quote it answers; placing an order is a reply to a quote.
- **FR-B3 — No price without a quote.** Price is sourced from the quote. An order line whose price is not covered by an on-file, in-window quote is **refused**.
- **FR-B4 — Catalog is product-only.** The catalog `Item` answers only "what the product is" (identity/description/kind). It no longer carries `unit_price`/`tax_rate`/`line_discount`. **This reverses ADR-0011 and ADR-0013.**

### Group C — "Name the parties"
- **FR-C1 — Three named parties.** Reseller, end customer, and the subsidiary ("the company you are") are named on the two papers (quote and order).
- **FR-C2 — End customer.** The end customer is a **name + ship-to address** recorded on the quote (not a managed account/entity — just those fields).
- **FR-C3 — Subsidiary "subsidiary record".** A simple subsidiary record carries **country** and **language** columns, so document numbers and email locale have a home. Implemented as columns / a small table — explicitly **not** a separate "subsidiary profile" service.

### Group D — "Box or a license"
- **FR-D1 — Item kind.** Each catalog item is marked **physical ("box")** or **license**.
- **FR-D2 — Arrival semantics.** A box counts as *arrived/delivered* only once a **carrier or proof-of-delivery** is recorded. A license counts as *arrived/delivered* **when it ships**.
- **FR-D3 — Shipped and delivered are different facts.** The reseller order status distinguishes **shipped** from **delivered** as separate facts.

### Group E — "Vendor date / scheduled"
- **FR-E1 — Vendor date on the line.** When purchasing actually buys from the maker, a **vendor date** is recorded on the line; that date is the meaning of "scheduled".
- **FR-E2 — Vendor Order deferred.** No separate Vendor Order document is built in this increment; it waits until that purchase is its own paper with its own number.

## Non-functional requirements (inherited unless Q7 changes them)
- **Security Baseline** (Increment 3/4: Yes). New reseller surfaces must honor **FR-19 / AC-02**: no ERP name, instance, or ERP record id (including `erp_customer_id`) ever reaches a reseller view. Quote/end-customer/subsidiary data is reseller-safe; `erp_customer_id` stays operator-only, exactly like the binding today.
- **Resiliency Baseline** (Yes). The new atomic shipment+quantity write (FR-A4) and the ERP idempotency change (FR-A2) are reliability requirements, not nice-to-haves.
- **Property-Based Testing** (Partial). Extend PBT to the new pure functions: quote price/validity resolution and the box/license delivered-fact derivation.
- **Event-sourcing versioning.** Renaming/removing `OrderState` members must not break replay of events already in the store. Persisted event *type names* (`OrderReadyForDelivery`, `OrderFulfilled`) are historical facts; the chosen approach must keep old streams replayable (see Q2/Q3 and the design stage).

## ADRs this increment changes or adds
- **Reverses**: ADR-0011 (price from catalog), ADR-0013 (flat item tax/discount from catalog).
- **Amends**: ADR-0005 (binding is now the ERP customer actually sent), ADR-0014 (lifecycle vs. fulfillment status — `FULFILLED` leaves the lifecycle; shipped/delivered become fulfillment-derived facts).
- **New (to be written at design time)**: Quote-before-order & price-from-quote; subsidiary subsidiary record; item kind + delivered-fact derivation; vendor/scheduled date without a Vendor Order.

## Open questions
See `increment5-questions.md`. Each question carries a recommended answer; the forks are real because they reverse accepted ADRs, rename persisted lifecycle states, and (Q6) would touch undesigned UI governed by the `design/` source of truth.
