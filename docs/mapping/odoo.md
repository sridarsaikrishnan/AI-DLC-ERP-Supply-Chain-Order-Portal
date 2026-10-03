# Field mapping: Odoo

What the platform's canonical order model maps to in Odoo, and back. Sourced directly
from the adapter code — if this ever disagrees with `src/modules/integration/infrastructure/odoo_adapter.py`
or `src/modules/integration/domain/status_mapping.py`, the code is right and this is stale.

## Outbound: canonical order → Odoo `sale.order`

| Canonical field | Odoo field | Notes |
|---|---|---|
| `client_reference` | `sale.order.client_order_ref` | The reseller's own order reference. |
| `client_reference` | `res.partner.name` (lookup/create) | Reused as the customer name — there is no separate canonical customer-name field yet, so the reseller's reference doubles as the Odoo partner's display name. |
| `lines[].product_key` | `product.product.default_code` (lookup only, fails closed) | No match → `submit` fails with a terminal error naming the SKU, rather than auto-creating a phantom product. |
| `lines[].quantity` | `sale.order.line.product_uom_qty` | |
| `lines[].unit_of_measure` | *(not mapped)* | Not sent to Odoo at all — every line is created using the product's default UoM. A real gap if a reseller's unit differs from the product's default. |
| *(our internal order id)* | *(not sent)* | Odoo never sees our `order_id` — only `client_reference`, via `client_order_ref`. |
| *(erp_order_id, returned)* | `sale.order.name` | Odoo's own auto-generated order reference (e.g. `S00021`), read back after creation and stored as our `erp_order_id`. |

## Inbound: Odoo status → canonical status

`status_mapping.py`'s `_map_odoo(fields: dict[str, str])`, reading `fields["state"]` and
`fields["invoice_status"]`, checked in this order:

| Odoo `state` | Odoo `invoice_status` | Canonical status |
|---|---|---|
| `cancel` | *(any)* | `CANCELLED` |
| *(any)* | `invoiced` | `CLOSED` |
| `done` | *(any, not invoiced)* | `FULFILLED` |
| `sale` | *(any, not invoiced)* | `CONFIRMED` |
| `draft`, `sent`, or anything else | *(any)* | *(no transition — status unchanged)* |

Both the inbound webhook path and the reconcile sweeper now supply both fields —
`OdooAdapter.fetch_status` fetches `state` *and* `invoice_status` in the same
`search_read` call, so `CLOSED` is reachable through polling, not just a webhook.

## Not mapped at all

- Price exists on the canonical model now (ADR-0011, resolved from the catalog at
  submission time) but still isn't sent to Odoo — `submit` doesn't set `price_unit` on
  order lines yet. Next step, not yet done.
- Shipping address, notes, multi-currency — out of scope for the current canonical model.
