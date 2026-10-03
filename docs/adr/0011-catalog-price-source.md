# ADR-0011: Order line price comes from the catalog, never from the client

| | |
|---|---|
| Status | Accepted — implemented |
| Affects | `catalog`, `ordering` modules |

## In one sentence
An order line's price is looked up from the catalog the moment the order is submitted —
the reseller never sends one, and the server never trusts one even if it did.

## Why this needed a decision

| Problem | Detail |
|---|---|
| The canonical model has a price field; nothing filled it | `OrderLine.unit_price` existed (`docs/canonical-model-v2.md`) but every line arrived unpriced — the reseller's `OrderLineInput` only ever carries `product_key`/`quantity`/`unit_of_measure` |
| Calculations had nothing to compute from | `line_total`/`subtotal` (`ordering/domain/calculations.py`) return `None` without a price — a real source was needed before they could do anything |

## The decision, step by step

| Step | What happens | Where |
|---|---|---|
| 1 | Operator sets a price on a catalog item | `CatalogService.sync_item()` / `syncItem` mutation → `Item.unit_price: Money \| None` |
| 2 | Reseller places an order — no price in the request | GraphQL `OrderLineInput` (`product_key`, `quantity`, `unit_of_measure` only) |
| 3 | Server looks up that item and stamps its price onto the line | `OrderService._priced()`, run before `Order.submit()` |
| 4 | The price becomes part of the immutable order fact | `OrderSubmitted` event — never re-derived after this point |
| 5 | SKU with no catalog price yet | Line stays unpriced (`unit_price: None`) — not an error |

**One hard rule:** the reseller's input has no price field, full stop — this isn't "client
input, validated against the catalog," it's catalog-only. There's no fallback path where a
submitted price gets used.

**What still rejects an order:** a SKU that isn't a real product at all is caught by
`routing.py`'s `UNKNOWN_ITEM` check — a separate, pre-existing gate. A real SKU that simply
has no price yet is not an error, just an unpriced line.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Reseller submits a price; server validates it against the catalog | The validate-then-reject step buys nothing over just never accepting a client price |
| Price lookup inside the GraphQL resolver, not `OrderService` | Leaks catalog access into the API layer; bypassed for any other caller of `place_order` (worker retries, future non-GraphQL entry points) |
| Backfill a default price onto existing items | Explicitly skipped — pre-production system, no real data to protect; a nullable `unit_price` is enough |

## Consequences

| | |
|---|---|
| ✅ | Price can never be client-controlled — a real trust-boundary gap closed before it ever shipped with one |
| ✅ | Price is a fact of the event, not a live lookup — replaying `OrderSubmitted` later always reproduces the same `line_total`, even if the catalog price changes afterward |
| ⚠️ | No price-change history on the catalog side — only each order's own event remembers what the price was *at that moment* |

## Revisit when
A reseller-facing price preview is wanted before submission — today a reseller sees no
price until after the order already exists, since they have no read access to the
catalog's prices.
