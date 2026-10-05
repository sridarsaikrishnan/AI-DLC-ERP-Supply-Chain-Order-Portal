# Increment 5 — Requirements Clarification Questions

Please answer each question by filling the letter after the `[Answer]:` tag. If none fit, pick the last option (Other) and describe. Each question lists my **recommended** answer so you can reply "all recommended" if you agree.

> **RESOLVED 2026-10-03**: User replied "Start the implementation" against the offer to build with all recommended answers. All questions resolved to the recommended option: **Q1=A, Q2=A, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A**.

## Question 1
Catalog pricing moves to the quote. This reverses ADR-0011 and ADR-0013 (price/tax/discount currently live on the catalog `Item`). How far does the move go?

A) **Full move (recommended).** `Item` keeps only identity (sku, name, kind). Price, tax, and discount live on the Quote. An order line with no on-file, in-window quoted price is refused.

B) Partial. Keep the catalog price/tax/discount as a fallback default; the Quote overrides when present (an order can still price straight off the catalog with no quote).

C) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 2
Rename the internal `READY_FOR_DELIVERY` lifecycle state (it means "routed, ready to send to the ERP" and now collides with the literal "delivery" of Group D). What should it become, and how do we treat the already-persisted `OrderReadyForDelivery` event?

A) **`ACCEPTED` + keep the persisted event type name (recommended).** Rename the `OrderState` enum value and the internal references to `ACCEPTED`; leave the stored event type `OrderReadyForDelivery` as-is (a historical fact), so no event-store rewrite is needed. Reseller-facing label is unchanged (still "Validated").

B) `ROUTED` + keep the persisted event type name.

C) `READY_TO_SEND` + keep the persisted event type name.

D) Rename the persisted event type too (requires an event upcaster / stream migration).

E) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 3
`FULFILLED` leaves the lifecycle and becomes a score only; the reseller status must show "shipped" and "delivered" as separate facts. How should that read on the order?

A) **Derived facts (recommended).** The order lifecycle keeps Submitted → Validated → Sent to ERP → Confirmed → Closed (no "Fulfilled"). "Shipped" and "Delivered" are separate booleans/facts derived from fulfillment records + item kind (box: delivered needs carrier or proof-of-delivery; license: delivered when shipped), shown alongside the two scores.

B) Two new lifecycle states. Replace "Fulfilled" with explicit `SHIPPED` and `DELIVERED` lifecycle states in `OrderState`.

C) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 4
Quote persistence and authorship. ADR-0002 says event-source the `Order` only; everything else is CRUD.

A) **CRUD quote, operator-authored (recommended).** The Quote is a normal (non-event-sourced) record the operator/distributor issues to a reseller; the reseller places an order against it. Consistent with ADR-0002.

B) Event-source the Quote like the Order.

C) Reseller self-creates quotes (self-service pricing) rather than the operator issuing them.

D) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 5
The subsidiary "subsidiary record" (country + language, for document numbers and email locale).

A) **Single subsidiary (recommended).** One subsidiary record per deployment, referenced by quotes/orders for numbering + email locale. Smallest thing that satisfies "document numbers and emails have a home."

B) Multiple subsidiaries (multi-entity); each quote/order points to one.

C) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 6
UI scope this increment. The `design/` folder is the UI source of truth, and the quote screens, the new-order-from-quote flow, item kind, shipped/delivered, and vendor/scheduled date are **not designed yet**. The steering says design new screens first and ask before changing existing ones.

A) **Backend + GraphQL only this increment (recommended).** Implement the domain, services, projections, Odoo adapter, migrations, and both GraphQL schemas. Defer the new/changed screens to a follow-up increment where they're designed first in the existing style. (Matches how several prior increments shipped backend-first.)

B) Include UI now. Design the new screens in the existing design-system style this increment and implement them end to end.

C) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 7
Extensions configuration for this increment.

A) **Inherit Increment 4 (recommended).** Security Baseline = Yes, Resiliency Baseline = Yes, Property-Based Testing = Partial (extended to the new pure functions: quote price/validity resolution and the box/license delivered-fact derivation).

B) Change the configuration (please describe after [Answer]: tag below).

C) Other (please describe after [Answer]: tag below)

[Answer]: 
