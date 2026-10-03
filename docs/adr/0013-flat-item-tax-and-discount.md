# ADR-0013: Tax and discount are flat per-item catalog fields, same source as price

| | |
|---|---|
| Status | Accepted — implemented |
| Affects | `catalog`, `ordering`, `integration` modules |

## In one sentence
`Item` gains `tax_rate` (a flat per-item rate) and `line_discount` (a flat per-unit
amount) — resolved onto order lines exactly like price (ADR-0011), never a reseller
input, and now actually sent to Odoo as `tax_id`/an adjusted `price_unit`.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Tax/discount math existed, nothing populated it | `calculations.py` (Phase 2) could compute `line_tax_total`/`line_total_with_tax` correctly — but `OrderLine.tax_rates`/`line_discount` had no data source, same gap `unit_price` had before ADR-0011 |
| "Tax/discount" could mean a lot of things | A full tax engine (jurisdiction, product category, nexus rules) or a promotion engine (codes, volume tiers, time-boxed sales) are real systems with real requirements neither this platform nor its users have specified |

## The decision
Mirror ADR-0011 exactly: `Item.tax_rate: TaxRate | None` and `Item.line_discount: Money |
None` are flat, operator-entered values (via `syncItem`), resolved onto an order's lines
at submission time (`OrderService._priced`) — not reseller input, not computed from any
jurisdiction/promotion logic. `OdooAdapter.submit` then: looks up `account.tax` by name
for the tax code (adds `tax_id` if found), and sends a `price_unit` already net of the
flat discount (Odoo's own `discount` field is a percentage, which doesn't fit a flat
amount cleanly, so the subtraction happens before the price is sent rather than mapping
onto that field).

## Alternatives considered

| Option | Rejected because |
|---|---|
| A real tax-jurisdiction/rate-lookup service | No requirement for multi-jurisdiction tax exists yet; this is the same unjustified-complexity trap as `ErpCapabilities` with one adapter — building generality nobody asked for |
| A promotion/discount-code engine | Genuinely a different, bigger feature (time-boxed codes, volume tiers, stacking rules) with no stated requirement — flagged, not built |
| Map the flat discount onto Odoo's percentage `discount` field | Would need `(discount_amount / unit_price) * 100`, a derived value that drifts from "the discount is $X" the moment the price changes — subtracting before sending is simpler and exact |

## Consequences

| | |
|---|---|
| ✅ | Tax and price now reach Odoo through the same, already-trusted path (catalog → `_priced` → canonical payload → adapter) |
| ✅ | `account.tax`/`uom.uom` lookups degrade gracefully (no match = line goes out with no tax / Odoo's default unit) rather than blocking the order — a tax-naming mismatch isn't catalog drift the way an unknown product is |
| ⚠️ | One flat rate per item — a product taxed differently by region/customer isn't representable. Acceptable until a real multi-jurisdiction requirement exists. |

## Revisit when
Multi-jurisdiction tax or a real promotion/discount-code system is an actual, stated
requirement — not before.
