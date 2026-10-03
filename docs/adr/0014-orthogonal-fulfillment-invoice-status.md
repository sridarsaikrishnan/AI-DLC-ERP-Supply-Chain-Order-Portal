# ADR-0014: Fulfillment/invoice status is derived and orthogonal to order lifecycle state

| | |
|---|---|
| Status | Accepted — implemented |
| Affects | `ordering`, new `fulfillment` module |

## In one sentence
`Order` gains `fulfillment_status`/`invoice_status` as **derived properties**, computed
from per-line shipped/invoiced quantities recorded by new event-sourced `Fulfillment`/
`Invoice` aggregates — without touching the existing `OrderState` lifecycle machine at all.

## Why this needed a decision

| Problem | Detail |
|---|---|
| "Partial fulfillment" doesn't fit a linear state machine | `OrderState` is `SUBMITTED → … → FULFILLED → CLOSED` — a straight line. "3 of 5 units shipped" has no slot in a single linear enum without branching logic that fights the existing, working transition guards. |
| Fulfillment/invoicing are real operational records | Per ADR-0002's own revisit condition ("another aggregate needs the same guarantees Order needs — full audit history") — a shipment or invoice is a fact worth a permanent, replayable record, unlike `catalog`/`connections`/`tenancy`. |

## The decision
- New module `fulfillment`: `Fulfillment`, `Invoice`, `Payment`, `Return` — each a minimal
  event-sourced aggregate (one `record` command, one event, replay-only, no amendment
  yet). Proves the event-sourcing kernel is genuinely generic (`EventSourcedRepository`
  takes any `Aggregate` subclass) rather than secretly `Order`-specific.
- `Order` gains `fulfilled_qty_by_line`/`invoiced_qty_by_line` (dicts, updated by new
  `OrderLineFulfilled`/`OrderLineInvoiced` events) and **derived** `fulfillment_status`/
  `invoice_status` properties computed from them vs. ordered quantities. `OrderState`
  (`state`) is completely untouched — `record_fulfillment`/`record_invoice` never call
  `confirm()`/`fulfill()`/`close()`.
- `FulfillmentService`/`InvoiceService` coordinate both aggregates in one call: save the
  `Fulfillment`/`Invoice` record, then update `Order`'s derived state. `PaymentService`/
  `ReturnService` are standalone — deliberately not yet wired into `invoice_status`/
  `fulfillment_status` (see their own docstrings for the open business-policy questions).

## Alternatives considered

| Option | Rejected because |
|---|---|
| Add `PARTIALLY_FULFILLED` etc. as new `OrderState` values | Forces branching logic into an enum designed to be a straight line; `_require(expected_state, ...)` guards would need rewriting throughout |
| `fulfilled_qty` as a plain field on `OrderLine`, set directly | Loses the audit trail of *which* shipment contributed what — exactly the guarantee ADR-0002 says justifies event-sourcing in the first place |
| Make Fulfillment/Invoice/Payment/Return publish events that `Order` reacts to asynchronously | More machinery than today's need justifies — nothing else currently needs to react to these independently; the event types already exist, so this split is available later without new events |

## Consequences

| | |
|---|---|
| ✅ | A real ERP's partial shipments are representable without touching the already-correct, already-tested `OrderState` machine |
| ✅ | Event-sourcing is proven generic — a second and third aggregate type reuse the same kernel with zero kernel changes |
| ⚠️ | `fulfillment_status`/`invoice_status` require loading the `Order` aggregate directly (not the projection) to read — `OperatorOrder`'s GraphQL resolver does one extra aggregate load per order today; acceptable at current volume, a projection field would avoid it if this becomes a hot path |
| ⚠️ | `Payment`/`Return` don't yet feed back into `Order`'s status — a real, open gap, not hidden (each aggregate's docstring says so) |

## Revisit when
`Payment` needs to drive `invoice_status` to `PAID` (needs a partial-payment/overpayment
policy decision first), or `Return` needs to reopen `fulfillment_status` (needs a
business-policy decision about whether a return undoes "fulfilled").
