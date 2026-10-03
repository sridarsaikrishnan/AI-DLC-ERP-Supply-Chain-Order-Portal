# Clarifying Questions — Increment 4: Rich Canonical Model (multi-domain, multi-ERP)

## Context already established (not re-asking these)
From design work already done this session (`docs/canonical-model-v2.md`, `docs/erp-compatibility` discussion):
- Canonical model needs: `Money`/`Quantity` as `Decimal` (not `float`), tax/discount/line-total
  calculations, derived (not linear) fulfillment/invoice status, and Fulfillment/Invoice/
  Payment/Return data.
- **Phase 1 is already implemented** (ad hoc, before this formal gate): `src/shared/money.py`
  (`Money` + `round_money`), `OrderLine.quantity: Decimal` with safe JSONB (de)serialization
  in `aggregate.py`, tests in `src/shared/tests/test_money.py` + `test_order_aggregate.py`.
  104 unit tests + 2 integration tests pass. This increment formalizes that work under
  AI-DLC and decides what happens next.
- Odoo itself (the only registered ERP) can represent nearly all of this natively
  (`sale.order.line.tax_id`, `discount` %, `stock.picking` partial delivery, `account.move`
  multi-invoice) — the gap is in our adapter code, not Odoo's capabilities.

## Q1 — Scope of this increment
Which phases of the build order (`docs/canonical-model-v2.md` §8) does this increment cover?

A) Phase 1 only — formalize what's already built, stop here
B) Phases 1–2 — add tax/discount/line-total/order-total calculations on top of Phase 1
C) Phases 1–3 — B, plus `fulfilled_qty`/`invoiced_qty` and derived `fulfillment_status`/`invoice_status`
D) All 5 phases — C, plus `Fulfillment`/`Invoice`/`Payment`/`Return` as plain-CRUD lists on `Order`, plus `ErpCapabilities`
E) Other (describe)

[Answer]: B — tax/discount/line-total/order-total calculations on top of Phase 1. C/D need new Order-level events (set shipping, record fulfillment) — save those for a later increment.

## Q2 — Proving multi-ERP readiness
The whole point is "strong enough for upcoming ERPs," but every design decision has been
validated against exactly one ERP (Odoo). Should this increment register a second adapter
(e.g. ERPNext, via the existing 4-step checklist in `docs/adding-an-erp.md`) — even a
minimal one — to prove the richer model isn't accidentally Odoo-shaped?

A) Yes — add a second ERP (ERPNext recommended — it was previously registered, then removed, and its removal is already documented) this increment, minimal adapter (`submit`/`fetch_status`/`cancel` + status mapper), to prove the model against something other than Odoo
B) No — stay Odoo-only this increment; defer a second ERP to its own future increment
C) Other (describe)

[Answer]: B — stay Odoo-only this increment; a second ERP is its own increment.

## Q3 — GraphQL/API surface
Should the reseller/operator GraphQL schemas expose the new fields (price, tax, totals,
fulfillment/invoice data) this increment, or stay backend-only for now?

A) Backend only this increment (domain model, events, projections) — GraphQL exposure is a follow-up increment
B) Extend GraphQL now too (reseller/operator schemas gain the new fields in this increment)
C) Other (describe)

[Answer]: A — backend only this increment; GraphQL exposure is a follow-up once there's a real price source wired through the catalog.

## Q4 — `ErpCapabilities` (per-adapter opt-in)
Build the capability-declaration mechanism (so an adapter can say "I don't support tax")
now, or wait until a second adapter actually exists and needs to differ from Odoo?

A) Defer — one adapter has nothing to differ from yet; build it only once Q2 adds a second ERP (or in a future increment)
B) Build it now as a seam, even with only Odoo registered
C) Other (describe)

[Answer]: A — defer; build it once Q2 (second ERP) is in scope.

## Q5 — Testing posture for the new calculation code
`round_money`, line-total/tax computation, and the derived-status rules are pure functions
— the same shape already covered by Property-Based Testing elsewhere in this codebase
(status mapping, routing resolution).

A) Add PBT (Hypothesis) for the new pure functions, consistent with existing partial-PBT posture — recommended
B) Ordinary unit tests only, no new PBT coverage
C) Other (describe)

[Answer]: A — add PBT (Hypothesis) for the new pure functions.

## Q6 — Confirm ADR-0002 stays locked
Design discussion already concluded Fulfillment/Invoice/Payment/Return should be plain-CRUD
lists on `Order`, not separate event-sourced aggregates, per ADR-0002 ("event-source Order
only"). Confirming before code is generated against it:

A) Keep ADR-0002 as-is — these stay plain data — recommended, no new requirement for independent audit/idempotent-retry guarantees has emerged
B) Reopen ADR-0002 — make one or more of these event-sourced too
C) Other (describe)

[Answer]: A — keep ADR-0002 as-is.
