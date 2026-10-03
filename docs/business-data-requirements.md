# Business data requirements — request & response, per capability

For each capability completed in this round: **who provides what** (the request — the
business knowledge the system needs, and from whom) and **what comes back** (the
response — what the system computes or returns). Companion to
`docs/data-flow-walkthrough.md` (which traces the order pipeline end to end) and
`docs/canonical-model-v2.md` (the full schema design).

---

## 1. Price/tax/discount reaching Odoo

**Request — what the operator must supply, once per item, via `syncItem`:**

| Field | Business meaning | Required? |
|---|---|---|
| `unitPrice` + `currency` | What this SKU costs | No — unpriced items just don't get a `line_total` |
| `taxCode` + `taxRate` + `taxInclusive` | A flat tax rate for this item (e.g. `VAT`, `0.20`, exclusive) | No |
| `lineDiscount` | A flat per-unit discount | No |

**What the reseller supplies, per order line (`placeOrder`):** `productKey`, `quantity`,
`unitOfMeasure` only — **never** price/tax/discount (ADR-0011, ADR-0013). The server
rejects nothing if these are absent from the input; they're not inputs at all.

**Response — what Odoo actually receives, per line, once the order is submitted:**

| Odoo field | Computed from |
|---|---|
| `price_unit` | catalog `unitPrice` minus `lineDiscount`, net (not Odoo's own percentage `discount` field — ADR-0013) |
| `product_uom` | looked up in Odoo by the canonical `unitOfMeasure` name; omitted (Odoo default used) if no match |
| `tax_id` | looked up in Odoo's `account.tax` by the catalog `taxCode`; omitted (no tax applied) if no match |

**Example:** item `ANVIL-100` synced with `unitPrice=19.99 USD`, `taxCode=VAT`/`taxRate=0.20`,
`lineDiscount=2.00 USD`. Reseller orders `2 × ANVIL-100`. Odoo receives one order line with
`price_unit = 17.99` (19.99 − 2.00) and `tax_id` pointing at Odoo's own `VAT` tax record.

---

## 2. Tax/discount catalog source (ADR-0013)

**Request:** same `syncItem` mutation as price — operator-entered, not derived from any
jurisdiction/tax-engine lookup. **Explicitly not supported**: multi-jurisdiction tax,
promotional/volume discount codes — both are real, different features with no stated
requirement yet (see ADR-0013's "Revisit when").

**Response:** `Item.taxRate`/`Item.lineDiscount`, visible on the operator Items page and
resolved onto every order line for that SKU at submission time — the same mechanism as
price, not a separate pipeline.

---

## 3. Partial fulfillment / invoice status (ADR-0014)

**Request — what must be recorded, and by whom, for status to move at all:**

| Mutation | Who calls it | Business data required |
|---|---|---|
| `recordFulfillment(orderId, lines, carrier?, trackingNumber?)` | Operator (today) — a human or a future ERP-sync job | Which `productKey`s shipped, and how much of each |
| `recordInvoice(orderId, lines, erpInvoiceId?)` | Operator (today) | Which `productKey`s were invoiced, and how much |
| `recordPayment(orderId, amount, currency, method, invoiceId?)` | Operator | A payment amount + method — **standalone, doesn't move `invoiceStatus` yet** |
| `recordReturn(orderId, lines, reasonCode)` | Operator | Which lines, how much, why — **standalone, doesn't move `fulfillmentStatus` yet** |

Nothing populates these automatically from Odoo yet — no adapter code reads Odoo's
`stock.picking`/`account.move` today. Until that's built, these mutations are the only
way fulfillment/invoice data enters the system (manual operator entry, or a future
integration calling the same mutations).

**Response — what's returned/derived:**

| Field | Computed from |
|---|---|
| `OperatorOrder.fulfillmentStatus` | `UNFULFILLED` / `PARTIALLY_FULFILLED` / `FULFILLED` — compares summed `recordFulfillment` quantities per line against ordered quantities |
| `OperatorOrder.invoiceStatus` | Same derivation, for `recordInvoice` |
| `Order.state` (the existing lifecycle: `SUBMITTED → … → CLOSED`) | **Unchanged by any of this** — still driven only by the ERP webhook/reconcile path (ADR-0014 keeps these orthogonal on purpose) |

**Example:** order has `ANVIL-100 × 10` and `SPRING-200 × 5`. `recordFulfillment` is
called twice — once with `ANVIL-100: 10`, once with `SPRING-200: 5`. After the first
call, `fulfillmentStatus = PARTIALLY_FULFILLED` (SPRING not yet shipped); after the
second, `FULFILLED`. The order's own `state` never left `CONFIRMED` through any of this.

---

## 4. `ErpCapabilities` (ADR-0015)

**Request:** nothing from a human — this is a static declaration each adapter's own code
makes (`OdooAdapter.capabilities = frozenset({"tax", "uom", "idempotency", "fail_closed_product"})`).

**Response:** visible via `adapter.capabilities` (logged by `DeliveryHandler` at submit
time) — an inspectable answer to "does this ERP support tax mapping" without reading
that adapter's full source. **Not yet a behavioral response** — nothing changes what gets
sent based on this declaration (ADR-0015's explicit scope boundary, pending a second
adapter to prove real gating against).

---

## 5. ERP connection credentials (ADR-0012) — what an operator must supply per ERP

**Request**, via `registerConnection`:

| Field | Business meaning | Example (Odoo) |
|---|---|---|
| `baseUrl` | The ERP server address | `https://eu.odoo.example.com` |
| `credentials` | Whatever non-secret parameters *this* ERP's login needs — generic, no fixed shape | `{"database": "odoo_eu", "username": "admin"}` |
| `secretRef` | A pointer to the login secret (password/API key), resolved via Secrets Manager — never the raw value | `prod:odoo-eu-login` |

**Response:** a usable `ErpConnection`, immediately routable once a verified
`tenant_connection_binding` also exists (unchanged from the original onboarding flow in
`docs/data-flow-walkthrough.md`). Nothing about `credentials` being a generic bag changes
what the operator sees for Odoo today — only what a *future* ERP's registration form
would need to send.


---

# Increment 5 — quote-before-order, named parties, box/license, vendor date

## 1. Quote before the order (FR-B)
**Data in (operator):** issue a quote for a reseller — `operating_company_id`, end
customer `name` + `ship_to`, `currency`, `valid_from`/`valid_until`, and priced lines
(`product_key`, `unit_price`, UoM, optional tax/discount). GraphQL `issueQuote`.
**Data in (reseller):** `placeOrder(quoteId, clientReference, lines[{productKey, quantity}])`
— no price, no UoM.
**System response:** price/UoM/tax/discount copied from the quote; a line not on the quote,
or a quote that is missing / not ISSUED / out of window, is refused
(`PriceNotQuoted` / `QuoteNotFound` / `QuoteNotValid`). Catalog `syncItem` no longer takes
price — only `kind` (ADR-0016).

## 2. Named parties (FR-C)
**Data in (operator):** the operating company "office card" (`name`, `country`,
`language`) via `createOperatingCompany`; the end customer (name + ship-to) on the quote.
**System response:** the order copies `quote_id`, `operating_company_id`,
`end_customer_name`, `ship_to` onto itself; all are reseller-safe (shown on the reseller
order). `erp_customer_id` stays operator-only (the binding), never on a reseller view.

## 3. Order truth to the ERP (FR-A)
**System response (no new input):** the order is sent to the ERP as the binding's
`erp_customer_id` (not a name-based auto-created partner); the platform `order_id` is the
idempotency key (written to/searched on `client_order_ref`); each line has its own
`line_id`. The reseller order shows both scores (`fulfillmentStatus`, `invoiceStatus`).
`READY_FOR_DELIVERY` is now `ACCEPTED`; `FULFILLED` is only a fulfillment-score value.

## 4. Box vs. license + shipped/delivered (FR-D)
**Data in (operator):** `recordFulfillment(orderId, lines[{lineId, quantity}], carrier?,
trackingNumber?, proofOfDelivery?)`.
**System response:** per line, `shipped` increases; `delivered` increases iff the line is a
LICENSE (delivered on ship) or a carrier/proof-of-delivery is present (a box). The reseller
order exposes `deliveryStatus` distinct from the shipped `fulfillmentStatus`. The shipment
record and the order's quantity update commit in one transaction (FR-A4).

## 5. Vendor date = "scheduled" (FR-E)
**Data in (operator/purchasing):** `setVendorDate(orderId, lineId, vendorDate)`.
**System response:** the date appears as the line's `scheduledDate`. No Vendor Order
document is created yet (deferred, FR-E2).
