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
| `unit_price` | What this SKU costs | System (operator enters) | `19.99` |
| `currency` | Paired with `unit_price` | System (operator enters) | `USD` |

One SKU → one connection, enforced in code. This is where "which ERP" for a product gets decided — ahead of time, not from the order. It's also the price source (ADR-0011) — nullable, since not every item has a price set yet.

---

## Direction 1: Reseller PO → ERP

### Wire payload: GraphQL `OrderLineInput` — what the reseller sends (not a table — a request shape, defined in `src/api/graphql/reseller/types.py`; its values get copied into the `events`/`orders` tables below)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `client_reference` | Reseller's own order number | Reseller | `PO-2024-1182` |
| `lines[].product_key` | SKU ordered | Reseller | `ANVIL-100` |
| `lines[].quantity` | Qty ordered | Reseller | `2` |
| `lines[].unit_of_measure` | Unit | Reseller | `EA` |

### Code mapping: price resolution (`OrderService._priced` — no table, just a catalog lookup, see ADR-0011)

Runs *before* the event below is even created. For each line, looks up `product_key`
against the `items` table from Setup; if that item has a price, stamps it onto the line.
The reseller's input above never carries a price — this is the only place one gets added.

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `lines[].unit_price` | Resolved from `items.unit_price` | System (catalog lookup) | `{"amount": "19.99", "currency": "USD"}` |

### DB table: `events` — the fact gets recorded (append-only)

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `stream_id` | = order_id | System | `ord_8f3c1a90` |
| `event_type` | What happened | System | `OrderSubmitted` |
| `payload` | Reseller's input + resolved price, stored | System | `{tenant_id, client_reference, lines: [{product_key, quantity, unit_of_measure, unit_price}], product_keys}` |

### DB table: `orders` — read-model, kept in sync with `events`

| Field | Meaning | Provided by | Example |
|---|---|---|---|
| `state` | Lifecycle stage | System | `SUBMITTED` → `VALIDATED` → `READY_FOR_DELIVERY` |
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
| `client_reference` | Reseller | `sale.order.client_order_ref` | `PO-2024-1182` |
| `client_reference` | Reseller | `res.partner.name` | `PO-2024-1182` |
| `lines[].product_key` | Reseller (value) + System (lookup) | `product.product.default_code` | `ANVIL-100` |
| `lines[].quantity` | Reseller | `sale.order.line.product_uom_qty` | `2` |
| *(price, currency, UoM)* | — | *(not mapped — known gap)* | `unit_price` now exists on the canonical line (ADR-0011) but `OdooAdapter.submit` still doesn't send it — that's the next adapter-side step, not yet built |

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
| `done` | not `invoiced` | `FULFILLED` | ERP gives inputs; System maps |
| any | `invoiced` | `CLOSED` | ERP gives inputs; System maps |
| `cancel` | any | `CANCELLED` | ERP gives inputs; System maps |

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
