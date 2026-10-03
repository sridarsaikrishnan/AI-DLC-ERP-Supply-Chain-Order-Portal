# Data flow walkthrough: reseller ↔ platform ↔ ERP

One example, traced hop-by-hop. "Provided by" = who the value originates from:
**Reseller**, **ERP**, or **System** (us — generated, looked up, or operator-entered).

Example used throughout: tenant `tnt_acme`, connection `conn_odoo_eu`, order `ord_8f3c1a90`.

**Not everything below is a database table.** Three different kinds of thing show up,
labeled accordingly:
- **DB table** — a real Postgres table (`migrations/versions/`), rows actually persist.
- **Wire payload** — raw JSON over HTTP (a webhook body, an API request/response). Not
  stored as its own row anywhere; its *contents* get copied into a DB table's columns.
- **Code mapping** — a plain Python function/dict (e.g. `status_mapping.py`,
  `odoo_adapter.py`). No storage at all — it's translation logic, re-run every time.

---

## Setup (must exist before any order or webhook)

### DB table: `erp_connections` — one row per ERP instance

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `connection_id` | Unique ID for this ERP instance | System | `conn_odoo_eu` |
| `erp_type` | Which adapter handles it | System | `ODOO` |
| `base_url` | ERP server address | System (operator enters, from ERP) | `https://eu.odoo.example.com` |
| `database` | Odoo DB name — Odoo's own API requires it on every call (one Odoo server hosts many DBs) | System (operator enters, from ERP) | `odoo_eu` |
| `secret_ref` | **Pointer** to the login credential, not the credential itself — resolved via Secrets Manager/env at call time, never stored raw | System (operator runs `aws secretsmanager create-secret`, pastes the ref) | `prod:odoo-eu-login` |
| `webhook_secret_ref` | Same, for inbound webhook auth — a *different* secret from `secret_ref` on purpose (leaking it can't be used to log into the ERP) | System (operator-provisioned) | `prod:odoo-eu-webhook` |
| `status` | Is this connection usable | System | `ACTIVE` |

### DB table: `tenant_connection_bindings` — which reseller can use which connection

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `binding_id` | Unique ID | System | `bnd_771` |
| `tenant_id` | Which reseller | Reseller (identity) | `tnt_acme` |
| `connection_id` | Which ERP instance | System | `conn_odoo_eu` |
| `erp_customer_id` | Reseller's customer ID inside that ERP | ERP (their customer record) | `CUST-9` |
| `status` | `TO_VERIFY` or `VERIFIED` | System (set after verification) | `VERIFIED` |

### DB table: `items` — which connection owns each SKU

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `item_id` | Unique ID | System | `item_anvil` |
| `sku` / `product_key` | Product code | System (operator, from catalog) | `ANVIL-100` |
| `owning_connection_id` | Which ERP instance owns this SKU | System (operator decision) | `conn_odoo_eu` |
| `kind` | `PHYSICAL` (a box) or `LICENSE` — drives the delivered fact (FR-D2) | System (operator enters) | `PHYSICAL` |

One SKU → one connection, enforced in code. This is where "which ERP" for a product gets decided — ahead of time, not from the order. **Price is no longer here (Increment 5, ADR-0016):** the catalog says only *what the product is*; price lives on the quote (below).

### DB table: `operating_companies` — the "office card" (Increment 5, FR-C3)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `operating_company_id` | Unique ID | System | `oc_eu` |
| `name` | The company you are | System (operator enters) | `Acme Distribution EU` |
| `country` | So document numbers have a home | System (operator enters) | `DE` |
| `language` | So emails have a locale | System (operator enters) | `de` |

### DB table: `quotes` — the price list a reseller orders against (Increment 5, FR-B)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `quote_id` | Unique ID | System | `qot_55` |
| `tenant_id` | Which reseller the quote is for | System (operator enters) | `tnt_acme` |
| `operating_company_id` | Which office issued it | System | `oc_eu` |
| `end_customer_name` / `ship_to` | Who the goods are for, and where | System (operator enters) | `Downstream GmbH` / `Berlin` |
| `valid_from` / `valid_until` | How long the prices hold | System (operator enters) | `2026-01-01` … `2026-12-31` |
| `status` | `DRAFT` / `ISSUED` / `EXPIRED` / `ACCEPTED` | System | `ISSUED` |
| `lines[]` | Priced lines: `product_key`, `unit_price`, UoM, tax, discount | System (operator enters) | `[{ANVIL-100, 19.99 USD, EA}]` |

---

## Direction 1: Reseller PO → ERP

### Wire payload: GraphQL `OrderLineInput` — what the reseller sends (not a table — a request shape, defined in `src/api/graphql/reseller/types.py`; its values get copied into the `events`/`orders` tables below)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `quote_id` | The quote this order replies to (Increment 5, FR-B2) | Reseller (picks a quote) | `qot_55` |
| `client_reference` | Reseller's own order number | Reseller | `PO-2024-1182` |
| `lines[].product_key` | SKU ordered | Reseller | `ANVIL-100` |
| `lines[].quantity` | Qty ordered | Reseller | `2` |

No price and no unit of measure in the reseller's input — both come from the quote.

### Code mapping: price resolution from the quote (`OrderService._line_from_quote` — no table, see ADR-0016)

Runs *before* the event below is created. For each line it finds the matching priced line
on `quote_id`; the price, UoM, tax and discount are copied from the quote, and the line's
`kind` is copied from the `items` catalog. A line with no matching quote line, or a quote
that is missing / not ISSUED / out of its validity window, is **refused** (FR-B3).

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `lines[].unit_price` | From the quote line | System (quote lookup) | `{"amount": "19.99", "currency": "USD"}` |
| `lines[].line_id` | Each line's own id (FR-A3) | System (generated) | `ol_3f2a` |
| `lines[].kind` | From `items.kind` | System (catalog lookup) | `PHYSICAL` |

### DB table: `events` — the fact gets recorded (append-only)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `stream_id` | = order_id | System | `ord_8f3c1a90` |
| `event_type` | What happened | System | `OrderSubmitted` |
| `payload` | Reseller's input + resolved price, stored | System | `{tenant_id, client_reference, lines: [{product_key, quantity, unit_of_measure, unit_price}], product_keys}` |

### DB table: `orders` — read-model, kept in sync with `events`

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `state` | Lifecycle stage | System | `SUBMITTED` → `VALIDATED` → `ACCEPTED` (was `READY_FOR_DELIVERY`, FR-A6) |
| `owning_connection_id` | Routing result | System (looked up, see below) | `conn_odoo_eu` |
| `erp_order_id` | ERP's own order number | ERP (filled in once sent) | *(null until Step 5)* |
| `lines[].line_total` | `quantity * unit_price`, computed at projection time | System (`calculations.line_total`) | `39.98` |
| `subtotal` | Sum of priced lines' `line_total` | System (`calculations.sum_money`) | `39.98` |

**Routing = a lookup, not a decision made here.** Each line's `product_key` is checked
against the `items` table above; all lines must agree on `owning_connection_id`
(else rejected `mixed_erp`), and the tenant must have a `VERIFIED` binding to it (else
`no_binding`). Nothing new is computed — both answers already existed from Setup.

### Code mapping: canonical → Odoo fields (`odoo_adapter.py` — no table, just a function)

| Canonical field | Provided by | Odoo field | Example |
|---|---|---|---|
| `order_id` (platform id, the idempotency key — FR-A2) | System | `sale.order.client_order_ref` | `ord_8f3c1a90` |
| `erp_customer_id` from the binding (FR-A1) | ERP (their customer record) | `sale.order.partner_id` | `CUST-9` (used directly; no name-based auto-create) |
| `lines[].product_key` | Reseller (value) + System (lookup) | `product.product.default_code` | `ANVIL-100` |
| `lines[].quantity` | Reseller | `sale.order.line.product_uom_qty` | `2` |
| `lines[].unit_price` net of `line_discount` | System (catalog, ADR-0011/0013) | `sale.order.line.price_unit` | `17.99` (19.99 − 2.00) |
| `lines[].unit_of_measure` | Reseller | `sale.order.line.product_uom` | looked up by name in Odoo's `uom.uom`; omitted (Odoo default used) if no match |
| `lines[].tax_rates[].code` | System (catalog, ADR-0013) | `sale.order.line.tax_id` | looked up by name in Odoo's `account.tax`; omitted (no tax applied) if no match |

### DB table: `orders` — updated after Odoo accepts the order

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `erp_order_id` | Odoo's own order number, read back | ERP | `S00042` |

This `(owning_connection_id, erp_order_id)` pair is the key Direction 2 uses to find this order again.

---

## Direction 2: ERP status change → reseller notified

### Wire payload: Odoo webhook POST body — what the ERP sends (not a table — the raw HTTP body, see `docs/odoo-webhook-setup.md`)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `erp_order_id` | Which Odoo order | ERP | `S00042` |
| `state` | Odoo's native status | ERP | `sale` |
| `invoice_status` | Odoo's invoicing status | ERP | `to invoice` |
| `event_id` | Dedup key | ERP | `4821_...` |

### DB table: `events` + `order_status_history` — the fact gets recorded

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `event_type` | What happened | System | `OrderConfirmed` |
| `order_status_history.state` | Reseller-visible status | System | `CONFIRMED` |

### Code mapping: Odoo status → canonical status (`status_mapping.py` — no table, just a function)

| ERP `state` | ERP `invoice_status` | Canonical status | Provided by |
|---|---|---|---|
| `sale` | not `invoiced` | `CONFIRMED` | ERP gives inputs; System maps |
| `done` | not `invoiced` | `CONFIRMED` | ERP gives inputs; System maps (Increment 5: `done` no longer means `FULFILLED` — delivery is a fact, not a lifecycle status, FR-A6) |
| any | `invoiced` | `CLOSED` | ERP gives inputs; System maps |
| `cancel` | any | `CANCELLED` | ERP gives inputs; System maps |

**Shipped and delivered are separate facts (Increment 5, FR-D).** They are not driven by
the ERP status poll above; an operator records a shipment (`recordFulfillment` with an
optional carrier / proof-of-delivery), and the order derives, per line: shipped (the
fulfillment "score"), delivered (a box needs a carrier or POD; a license is delivered on
ship), and invoiced. The reseller order shows `fulfillmentStatus`, `deliveryStatus` and
`invoiceStatus` alongside the lifecycle status. A per-line vendor date set by purchasing
is what "scheduled" means (FR-E1); a standalone Vendor Order document is deferred (FR-E2).

### Wire payload: outbound webhook POST body — sent to reseller (not a table — the raw HTTP body we send; `WebhookDispatchService._build_body`)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `event` | Event type | System | `OrderConfirmed` |
| `eventId` | Dedup key for receiver | System | `evt_a9f3` |
| `order.id` | Our order ID | System | `ord_8f3c1a90` |
| `order.number` | Reseller's own reference | Reseller (echoed back) | `PO-2024-1182` |
| `order.status` | Current status | System | `CONFIRMED` |
| *(header)* `X-Signature` | HMAC proof it's really us | System | `t=...,v1=...` |

### DB table: `webhook_deliveries` — delivery attempt tracking

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `delivery_id` | Unique ID | System | `whdlv_7a21` |
| `status` | `DELIVERED` / `RETRYING` / `FAILED` | System | `DELIVERED` |
| `attempts` | How many tries | System | `1` |

### DB table: `webhook_endpoints` — where the reseller wants notifications sent

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `endpoint_id` | Unique ID | System | `wh_ep_55` |
| `tenant_id` | Which reseller | Reseller (identity) | `tnt_acme` |
| `url` | Reseller's receiving endpoint | Reseller | `https://acme.example.com/hooks/orders` |
| `event_types` | Which events to send (null = all) | Reseller | `null` |
| `secret_ref` | HMAC signing secret | System (generated once, shown once) | `prod:wh-ep-55-secret` |
| `is_active` | On/off | Reseller | `true` |

---

## Side by side

| | Direction 1: PO → ERP | Direction 2: ERP → reseller |
|---|---|---|
| Who sends the raw input | Reseller | ERP |
| Stored in | `events` + `orders` | `events` + `order_status_history` |
| Code mapping (no storage) | canonical → Odoo fields | Odoo status → canonical status |
| Who receives the final output | ERP | Reseller |
| Delivery tracked in | `erp_order_id` on `orders` | `webhook_deliveries` |
