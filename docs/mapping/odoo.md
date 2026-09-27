# Field mapping: Odoo

What the platform's canonical order model maps to in Odoo, and back. Sourced directly
from the adapter code — if this ever disagrees with `src/modules/integration/infrastructure/odoo_adapter.py`
or `src/modules/integration/domain/status_mapping.py`, the code is right and this is stale.

## Outbound: canonical order → Odoo `sale.order`

| Canonical field | Odoo field | Notes |
|---|---|---|
| `client_reference` | `sale.order.client_order_ref` | The reseller's own order reference. |
| `client_reference` | `res.partner.name` (lookup/create) | Reused as the customer name — there is no separate canonical customer-name field yet, so the reseller's reference doubles as the Odoo partner's display name. |
| `lines[].product_key` | `product.product.default_code` (lookup/create) | Looked up by internal reference code; a new product is created if none matches. |
| `lines[].quantity` | `sale.order.line.product_uom_qty` | |
| `lines[].unit_of_measure` | *(not mapped)* | Not sent to Odoo at all — every line is created using the product's default UoM. A real gap if a reseller's unit differs from the product's default. |
| *(our internal order id)* | *(not sent)* | Odoo never sees our `order_id` — only `client_reference`, via `client_order_ref`. |
| *(erp_order_id, returned)* | `sale.order.name` | Odoo's own auto-generated order reference (e.g. `S00021`), read back after creation and stored as our `erp_order_id`. |

## Inbound: Odoo status → canonical status

`status_mapping.py`'s `_map_odoo(native, invoice)`, checked in this order:

| Odoo `state` | Odoo `invoice_status` | Canonical status |
|---|---|---|
| `cancel` | *(any)* | `CANCELLED` |
| *(any)* | `invoiced` | `CLOSED` |
| `done` | *(any, not invoiced)* | `FULFILLED` |
| `sale` | *(any, not invoiced)* | `CONFIRMED` |
| `draft`, `sent`, or anything else | *(any)* | *(no transition — status unchanged)* |

**Known gap, not hidden**: the reconcile sweeper (`reconcile.py`) only calls
`adapter.fetch_status()`, which reads Odoo's `state` field — it never fetches
`invoice_status`. So in the live reconciliation path, `invoice_status` is always empty
and the `CLOSED` row above can never actually fire; an order can reach `FULFILLED` but
not `CLOSED` through today's polling. Fixing it means fetching `invoice_status` alongside
`state` in `OdooAdapter.fetch_status`.

## Not mapped at all

- Prices / currency — the canonical order model has no price field yet, so nothing is
  sent or read back for it.
- Shipping address, notes, multi-currency — out of scope for the current canonical model.
