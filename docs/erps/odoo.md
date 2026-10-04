# Odoo

Status: **live, real adapter** (`src/modules/integration/erp/infrastructure/odoo_adapter.py`).
The only ERP actually registered today (`ErpType.ODOO`). This page is sourced from the
adapter code — if it ever disagrees with that file or
`src/modules/integration/erp/domain/status_mapping.py`, the code is right and this is stale.

## What it is, as far as this platform is concerned

Odoo's **Sales** app (`sale.order`) is the only part we talk to. We drive it over its
**JSON-RPC 2.0** API at `<base_url>/jsonrpc` — not the REST API, not XML-RPC. Every call
goes through two Odoo services: `common` (authentication) and `object`
(`execute_kw`, which calls any model method by name — this is how Odoo's JSON-RPC works for
everything beyond login).

## How a connection is configured

One `ErpConnection` row = one Odoo database. The fields that matter for Odoo specifically:

| `ErpConnection` field | What it is for Odoo |
|---|---|
| `base_url` | e.g. `http://localhost:8069` — no trailing `/jsonrpc`, the adapter appends it. |
| `credentials["database"]` | The Odoo database name (one URL can host several). Generic bag, not a fixed field — ADR-0012. |
| `credentials["username"]` | An Odoo user's login. |
| `secret_ref` | Resolves to that user's **password** — `common.authenticate` takes a password, not an API key, in this flow. |
| `webhook_secret_ref` | Unrelated to login — see [Inbound webhooks](#inbound-webhooks-status-pushed-back-to-us). |

Two Odoo databases (e.g. EU and US) are just two `ErpConnection` rows with `erp_type: ODOO`
— the adapter is stateless and reused across both (see
[erp-integration-patterns.md](../erp-integration-patterns.md) §2 for how routing keeps them
apart).

## Authentication

`common.authenticate(database, username, password, {})` returns a numeric `uid` on success,
or a falsy value on failure (mapped to a **terminal** error — wrong credentials won't fix
themselves on retry). That `uid` is passed on every subsequent `execute_kw` call alongside
the password again (this flow issues no session token — every call re-authenticates).

## Outbound: canonical order → Odoo `sale.order`

What `submit` sends, field by field:

| Canonical | Odoo field | Notes |
|---|---|---|
| platform `order_id` (the idempotency key, FR-A2) | `sale.order.client_order_ref` | Searched **before** create; a retried submit returns the existing order instead of duplicating. This is our `order_id`, **not** the reseller's `client_reference`. |
| binding `erp_customer_id` (FR-A1) | `sale.order.partner_id` | Used **directly** as Odoo's own partner id — no name-based lookup/auto-create. A missing/invalid id is a terminal error, not a silent new partner. |
| `line.product_key` | `product.product.default_code` (lookup only) | **Fails closed**: no match → terminal error naming the SKU, never an auto-created phantom product. |
| `line.quantity` | `sale.order.line.product_uom_qty` | |
| `line.unit_price` net of `line_discount` | `sale.order.line.price_unit` | Flat per-unit discount is subtracted here (Odoo's own `discount` is a percentage, which doesn't fit a flat amount). Omitted if the line has no price. |
| `line.unit_of_measure` | `sale.order.line.product_uom` | Looked up by name in `uom.uom`; **omitted (Odoo default used)** if no match — graceful degradation, not a blocked order. |
| `line.tax_rates[].code` | `sale.order.line.tax_id` | Looked up by name in `account.tax`; **omitted (no tax)** if no match. |
| *(our `order_id`)* | — | Only via `client_order_ref` above; Odoo never sees it otherwise. |
| *(returned)* `erp_order_id` | `sale.order.name` | Odoo's auto-numbered reference (e.g. `S00042`), read back after create and stored as our `erp_order_id`. |

### `submit` — step by step

1. Authenticate.
2. **Idempotency**: `search_read` `sale.order` by `client_order_ref == order_id`; if found,
   return its `name` immediately (a retried submit never double-creates).
3. **Customer**: `partner_id = int(erp_customer_id)` from the verified binding — used
   directly. Missing/invalid → terminal error.
4. **Per line**: resolve the product by `default_code` (fail closed); set `product_uom_qty`,
   and optionally `price_unit` (net of discount), `product_uom` (if the UoM name matches),
   and `tax_id` (if the tax code name matches).
5. Create the `sale.order` with `client_order_ref`, `partner_id` and the order lines.
6. Read back `sale.order.name` → our `erp_order_id`.

## Inbound: Odoo status → canonical status

`status_mapping.py`'s `_map_odoo(fields)` reads `fields["state"]` and
`fields["invoice_status"]`, checked in this order. `CanonicalStatus` has three values
(`FULFILLED` left the lifecycle in Increment 5 — delivery is a derived fact now, FR-A6):

| Odoo `state` | Odoo `invoice_status` | Canonical status |
|---|---|---|
| `cancel` | *(any)* | `CANCELLED` |
| *(any)* | `invoiced` | `CLOSED` |
| `sale` **or** `done` | *(not invoiced)* | `CONFIRMED` |
| `draft`, `sent`, or anything else | *(any)* | *(no transition — status unchanged)* |

`fetch_status` (used by the reconcile sweeper) does a `search_read` on `sale.order` by
`name`, reading **both** `state` and `invoice_status` in one call — so `CLOSED` (which
needs `invoice_status == invoiced`) is reachable by polling, not only by webhook.

`cancel` looks the order up by `name` and calls Odoo's `action_cancel`.

## Inbound webhooks (status pushed back to us)

Odoo Community has **no native "call a webhook" automation action** — Automation Rules can
run server-action Python, which is what we use to POST to our endpoint. Full setup, payload
shape, and the security tradeoff (shared-secret-in-path, since Automation Rule code can't
compute an HMAC) are in [odoo-webhook-setup.md](../odoo-webhook-setup.md).

## Local dev

`docker-compose.yml`'s `odoo` service runs `odoo:17` with `base,contacts,sale_management`,
backed by its own `odoo-db` Postgres (separate from the platform DB — don't confuse them).
First boot takes a minute or two. Odoo's web UI is at **http://localhost:8069**
(`admin`/`admin`) — useful for eyeballing what the adapter created. `ERP_ADAPTER_MODE=stub`
bypasses Odoo entirely with a deterministic fake (no live Odoo needed for most dev/tests);
`ERP_ODOO_TIMEOUT_SECONDS` (default `10`) controls the real adapter's HTTP timeout. Full
steps: [local-setup.md](../local-setup.md).

## Known gaps

Real limitations discovered while building/running this, not hidden:

- **`unit_of_measure` falls back to the product default** if the reseller's UoM name doesn't
  match an Odoo `uom.uom` by name — the order still goes through, but in the product's
  default unit. A real gap if those differ.
- **Unmatched tax codes are dropped** (line goes out untaxed) rather than blocking the
  order — a missing tax config is visible in Odoo itself.
- **`res.partner` is never auto-created.** The order is placed as the binding's
  `erp_customer_id` directly; an unlinked reseller is a terminal error, by design (FR-A1).
- **No automatic shipment/invoice capture.** `fetch_status` reads only `sale.order.state`
  and `invoice_status` — nothing reads Odoo's `stock.picking`/`account.move`, so shipments
  and invoices are operator-recorded, not pulled from Odoo. (See the HLD's "known gaps" card.)
