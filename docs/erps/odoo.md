# Odoo

Status: **live, real adapter** (`src/modules/integration/infrastructure/odoo_adapter.py`).
The only ERP actually registered today (`ErpType.ODOO`).

## What it is, as far as this platform is concerned

Odoo's **Sales** app (`sale.order`) is the only part we talk to. We drive it over its
**JSON-RPC 2.0** API at `<base_url>/jsonrpc` — not the REST API, not XML-RPC. Every call
goes through two Odoo services: `common` (authentication) and `object`
(`execute_kw`, which calls any model method by name — this is how Odoo's JSON-RPC works
for everything beyond login).

## How a connection is configured

One `ErpConnection` row = one Odoo database. The fields that matter for Odoo specifically:

| `ErpConnection` field | What it is for Odoo |
|---|---|
| `base_url` | e.g. `http://localhost:8069` — no trailing `/jsonrpc`, the adapter appends that itself. |
| `credentials["database"]` | The Odoo database name (Odoo can host several databases behind one URL). Generic bag, not a fixed field — see ADR-0012. |
| `credentials["username"]` | An Odoo user's login. |
| `secret_ref` | Resolves to that user's **password** — Odoo's `common.authenticate` takes a password, not an API key, in the flow this adapter uses. |
| `webhook_secret_ref` | Unrelated to login — see [Inbound webhooks](#inbound-webhooks-status-pushed-back-to-us) below. |

`credentials` is a generic `dict[str, str]` (ADR-0012) — Odoo happens to need exactly these
two keys; an OAuth-token ERP might need different keys entirely, or none at all.

Two Odoo databases (e.g. an EU instance and a US instance) are just two `ErpConnection`
rows with `erp_type: ODOO` — the adapter is stateless and reused across both, see
`docs/erp-integration-patterns.md` §2 for how routing keeps them apart.

## Authentication

`common.authenticate(database, username, password, {})` returns a numeric `uid` on
success, or a falsy value on failure (mapped to a **terminal** error — wrong credentials
won't fix themselves on retry). That `uid` is then passed on every subsequent
`execute_kw` call alongside the password again (Odoo's JSON-RPC doesn't issue a session
token for this flow — every call re-authenticates implicitly).

## What the adapter actually does

### `submit` — place an order

1. Authenticate.
2. **Idempotency check**: search for an existing `sale.order` with `client_order_ref`
   matching this order's `client_reference`. If found, return it immediately — a retried
   `submit` (e.g. after a timeout where the first attempt actually succeeded) returns the
   same Odoo order instead of creating a duplicate.
3. Look up (by exact name match) or create a `res.partner` using the order's
   `client_reference` as the partner name — **there is no separate customer-name field in
   the canonical model yet**, so the reseller's own reference doubles as the Odoo customer
   name. This means two orders with different `client_reference` values become two
   different Odoo partners, even from the same reseller.
4. For each order line, look up a `product.product` by `default_code` (Odoo's "Internal
   Reference" field). **Fails closed, not silent auto-create**: if no match exists, the
   whole submit fails with a terminal error naming the missing SKU, rather than inventing
   a new Odoo product with no price/category/setup. By the time this runs, `routing.py`
   has already confirmed the SKU is real in *our* catalog — a miss here means catalog
   drift between our system and Odoo, worth a human fixing in Odoo, not auto-healing.
5. Create the `sale.order` with `client_order_ref` set to the reseller's reference and one
   `order_line` per canonical line (`product_uom_qty` = quantity).
6. Read back `sale.order.name` (Odoo's own auto-numbered reference, e.g. `S00042`) — that
   becomes our `erp_order_id`. Our own `order_id` is never sent to Odoo at all.

### `fetch_status` — used by the reconciliation sweeper

`search_read` on `sale.order` by `name`, reading **both `state` and `invoice_status`**,
returned as `{"state": ..., "invoice_status": ...}` — the same field-bag shape the status
mapper reads from a webhook payload. (Previously only `state` was fetched, which meant
`CLOSED` — which depends on `invoice_status == "invoiced"` — could never be reached via
polling. Fixed.)

### `cancel`

Looks the order up by `name`, then calls Odoo's `action_cancel` method on it.

## Status values → canonical status

The full mapping table lives in **[`docs/mapping/odoo.md`](../mapping/odoo.md)** — don't
duplicate it here. Short version: Odoo's `sale.order.state` (`draft`/`sent`/`sale`/`done`/
`cancel`) and `invoice_status` (`invoiced`/etc.) together decide `CONFIRMED` /
`FULFILLED` / `CLOSED` / `CANCELLED`.

## Inbound webhooks (status pushed back to us)

Odoo Community has **no native "call a webhook" automation action** — Automation Rules
can run server-action Python code, which is what we use to POST to our own endpoint. Full
setup steps, the payload shape, and the security tradeoff (shared-secret-in-path, since
Automation Rule code can't compute an HMAC) are in
**[`docs/odoo-webhook-setup.md`](../odoo-webhook-setup.md)**.

## Local dev

`docker-compose.yml`'s `odoo` service runs `odoo:17` with `base,contacts,sale_management`
installed, backed by its own `odoo-db` Postgres (separate from the platform's own
database — don't confuse the two). First boot takes a minute or two for module install.
Odoo's own web UI is at **http://localhost:8069** (`admin`/`admin`) — useful for
eyeballing what the adapter actually created. `scripts/seed_demo.py` wires up a demo
connection + binding pointed at this local instance. Full steps:
`docs/local-setup.md` §2–§4.

`ERP_ADAPTER_MODE=stub` bypasses this entirely with a deterministic fake — no live Odoo
needed for most local dev/tests. `ERP_ODOO_TIMEOUT_SECONDS` (default `10`) controls the
real adapter's HTTP timeout.

## Known gaps

Real limitations discovered while building/running this, not hidden:

- **`unit_of_measure` isn't sent at all.** Every Odoo order line is created using the
  product's *default* UoM, regardless of what the reseller specified. A real gap if a
  reseller's unit differs from the product's Odoo default. Still open.
- **No price/currency handling.** Price now exists on the canonical model (ADR-0011) but
  `submit` still doesn't send it to Odoo — every created order line has whatever price
  the matched product already has in Odoo. Still open; next step is sending `price_unit`
  on each `order_line`.
- ~~`invoice_status` is never fetched~~ **Fixed** — see `fetch_status` above.
- ~~Product auto-creation is silent~~ **Fixed** — see step 4 above (fails closed instead).
  `res.partner` (customer) auto-creation is unchanged/still silent — judged lower risk
  than a phantom product polluting the shared catalog, since a new partner record per
  reseller reference is a reasonable default, not catalog corruption.
- ~~No idempotency key sent to Odoo~~ **Fixed** — see step 2 above (search-before-create
  on `client_order_ref`). Covers the case this was actually written for (a redelivered
  `submit` after a timeout where the first attempt succeeded server-side).
