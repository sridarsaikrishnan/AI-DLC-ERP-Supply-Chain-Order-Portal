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
| `database` | The Odoo database name (Odoo can host several databases behind one URL). |
| `username` | An Odoo user's login. |
| `secret_ref` | Resolves to that user's **password** — Odoo's `common.authenticate` takes a password, not an API key, in the flow this adapter uses. |
| `webhook_secret_ref` | Unrelated to login — see [Inbound webhooks](#inbound-webhooks-status-pushed-back-to-us) below. |

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
2. Look up (by exact name match) or create a `res.partner` using the order's
   `client_reference` as the partner name — **there is no separate customer-name field in
   the canonical model yet**, so the reseller's own reference doubles as the Odoo customer
   name. This means two orders with different `client_reference` values become two
   different Odoo partners, even from the same reseller.
3. For each order line, look up (by `default_code`, Odoo's "Internal Reference" field) or
   **create** a `product.product` if none matches. This is silent auto-creation, not a
   lookup that fails closed — a typo'd product key becomes a brand-new Odoo product, not
   an error. Worth knowing before trusting Odoo's product catalog is the source of truth.
4. Create the `sale.order` with `client_order_ref` set to the reseller's reference and one
   `order_line` per canonical line (`product_uom_qty` = quantity).
5. Read back `sale.order.name` (Odoo's own auto-numbered reference, e.g. `S00042`) — that
   becomes our `erp_order_id`. Our own `order_id` is never sent to Odoo at all.

### `fetch_status` — used by the reconciliation sweeper

`search_read` on `sale.order` by `name`, reading only the **`state`** field. See
[Known gaps](#known-gaps) — `invoice_status` is never fetched, which matters.

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
  reseller's unit differs from the product's Odoo default.
- **`invoice_status` is never fetched**, so the `CLOSED` status can never actually be
  reached through reconciliation today — only `fetch_status`'s `state` field is read, and
  `CLOSED` in the mapping table depends on `invoice_status == "invoiced"`. An order can
  reach `FULFILLED` but not `CLOSED` via polling. Fixing it means fetching
  `invoice_status` alongside `state` in `OdooAdapter.fetch_status`.
- **Product/partner auto-creation is silent.** See step 2–3 above — there's no "reject
  unknown product" mode. If catalog accuracy matters, this needs a stricter lookup path.
- **No price/currency handling.** The canonical order model has no price field, so
  nothing is sent to or read back from Odoo for pricing — every created order line has
  whatever price the matched (or newly-created) product already has in Odoo.
- **No idempotency key sent to Odoo.** If `submit` is called twice for the same order
  (e.g. a retry after a timeout where the first attempt actually succeeded server-side),
  Odoo will happily create a second `sale.order` — nothing on the Odoo side de-duplicates.
  The platform's own retry logic (`DeliveryHandler`) doesn't currently guard against this
  either; a real risk under network partition during `submit`, not yet mitigated.
