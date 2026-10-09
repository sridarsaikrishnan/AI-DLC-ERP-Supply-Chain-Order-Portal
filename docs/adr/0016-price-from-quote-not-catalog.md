# ADR-0016 — Price lives on the quote, not the catalog

**Status**: Accepted for the unused quote model — superseded on the live path by [ADR-0019](0019-order-routing.md). Supersedes ADR-0011 and ADR-0013.

> **Amendment (ADR-0019):** AdminOps no longer issues a quote or places an order against
> one. A followed sales order takes its lines and prices from the ERP document at adopt
> time. `QuoteService.issue_quote` is still in the tree and nothing in the API calls it.

## In one sentence
An order is a reply to a quote, and the quote is the only price source; the catalog item
now says only *what the product is*, so a line with no quoted price is refused.

## Why this needed a decision
| Problem | Detail |
|---|---|
| A catalog price is context-free | ADR-0011/0013 put `unit_price`/`tax`/`discount` on the catalog `Item`. But a distributor's price is per-reseller, time-bounded, and tied to an end customer and a ship-to — none of which a standing catalog attribute can express. |
| "Distributor tool" needs a quote | The product only becomes a distributor tool when a quote precedes the order: it names the reseller, the items, the prices, how long the prices hold, and where the goods go. |

## The decision
- New `quoting` module (CRUD, operator-authored — consistent with ADR-0002: event-source
  the `Order` only). A `Quote` carries the reseller (tenant), the subsidiary, the
  end customer (name + ship-to), a currency, a validity window, and priced lines.
- `OrderService.place_order` takes a `quote_id` + line quantities. It resolves each line's
  price/tax/discount from the quote, copies the parties onto the order, and **refuses** a
  line that has no matching priced quote line, or a quote that is missing / not ISSUED /
  out of window (`QuoteNotFound` / `QuoteNotValid` / `PriceNotQuoted`).
- The catalog `Item` keeps only `item_id, sku, name, owning_connection_id, kind`.
  `unit_price`/`tax_rate`/`line_discount` columns are dropped.

## Alternatives considered
- **Keep a catalog price as a fallback (quote overrides).** Rejected: it keeps two price
  sources and lets an order price itself with no quote on file, which is exactly the thing
  this increment removes. "A price with no quote on file is refused."
- **Event-source the Quote.** Rejected: a quote is reference data an operator authors and
  revises; it has no replay-worthy transactional history (ADR-0002's reasoning holds).

## Consequences
| | |
|---|---|
| ✅ | One price source; a price always has a reseller, a window, and a destination behind it. |
| ✅ | The reseller never sends a price; `OrderLineInput` has no price field at all. |
| ✅ | Catalog is small and ERP-neutral again — "what the product is", nothing more. |
| ⚠️ | Placing an order now requires a quote to exist first — a real workflow step, not just a form. |
| ⚠️ | Reverses two accepted ADRs; the item price columns and their data are dropped (acceptable: pre-production tooling, no real catalog-price data to preserve). |

## Revisit when
A reseller needs self-service pricing (quote-less ordering against a standing price list),
or quotes need their own revision history — either would reopen the CRUD-vs-event-sourced
and catalog-fallback questions.
