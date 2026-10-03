# Canonical model v2 — a schema that survives contact with a second ERP

Today's canonical model (`client_reference` + `lines[product_key, quantity, unit_of_measure]`,
4-value `CanonicalStatus`) was sized for Odoo. This is the richer replacement: enough
domains, status branching, and calculation rules that SAP/NetSuite/Dynamics/Zoho can each
map *their* subset onto it without a schema change per ERP.

**Kept as-is, not revisited:** only `Order` is event-sourced (ADR-0002); adding an ERP is
still 4 touch points (ADR-0003). This model fits inside those, it doesn't replace them.

**Deliberately out of scope** (add only when a real ERP forces it): lot/serial tracking,
multi-warehouse inventory, bill-of-materials/kitting, recurring billing/subscriptions,
vendor/AP flows. Adding any of these later is additive, not a rewrite.

---

## 1. Value objects (shared across every domain below)

### `Money` — never a float

| Field | Type | Rule |
|---|---|---|
| `amount` | `Decimal` | Never `float` — binary float can't represent `0.1` exactly, which compounds across tax/discount math |
| `currency` | `str` (ISO 4217) | e.g. `USD`, `JPY` |

Rounding is one function, used everywhere: `round_money(amount, currency)` — rounds to
that currency's minor-unit digits (2 for `USD`, 0 for `JPY`), `ROUND_HALF_UP`. No adapter
rounds independently — one source of truth, same answer regardless of which ERP touches it.

### `Quantity` — never bare, always carries its unit

| Field | Type | Rule |
|---|---|---|
| `value` | `Decimal` | |
| `unit_of_measure` | `str` | e.g. `EA`, `BOX`, `KG` |

Converting between units (reseller orders in `BOX`, ERP tracks in `EA`) uses a conversion
factor **on the item itself**, not invented per-order:

```
items.uom_conversions: dict[str, Decimal]   # {"BOX": 12, "KG": 1}  — factor to the item's base unit
```
This is the fix for today's dropped `unit_of_measure` gap (`docs/mapping/odoo.md:15`) — a
real factor to convert with, instead of silently defaulting to the product's own unit.

### `Address`, `Party`, `TaxLine`

| Type | Fields |
|---|---|
| `Address` | `line1, line2, city, region, postal_code, country_code` |
| `Party` | `party_id, name, tax_id, billing_address, shipping_address, email, phone` — today's `client_reference`-doubles-as-name hack (`docs/mapping/odoo.md:12`) goes away |
| `TaxLine` | `code, rate: Decimal, amount: Money, inclusive: bool` |

---

## 2. Domains and where they live

| Domain | New or extends? | Event-sourced? |
|---|---|---|
| **Order** | Extends existing `Order` aggregate | Yes (unchanged, ADR-0002) |
| **Fulfillment** (shipment) | New — a list *on* `Order`, not its own aggregate | No — plain data, same as ADR-0002's "no business need for full history" reasoning |
| **Invoice** | New — a list *on* `Order` | No |
| **Payment** | New — a list *on* `Order` | No |
| **Return / credit memo** | New — a list *on* `Order` | No |

Keeping these as structured lists on `Order` (not separate event streams) honors ADR-0002
as written. **Revisit only if** one of them needs its own idempotent-retry/audit guarantees
independent of the order — ADR-0002's own "revisit when" clause, not a new decision.

---

## 3. `Order` — extended fields

| Field | Type | Provided by | Calculation |
|---|---|---|---|
| `client_reference` | `str` | Reseller | — |
| `bill_to` / `ship_to` | `Party` | Reseller | — |
| `currency` | `str` | Reseller (or tenant default) | — |
| `fx_rate` | `Decimal \| None` | System | set once, at `VALIDATED`, if `currency` ≠ tenant's settlement currency — never silently re-derived later |
| `lines` | `list[OrderLine]` | Reseller (qty/SKU) + System (pricing) | see below |
| `shipping_amount` | `Money` | ERP (usually) | — |
| `order_discount` | `Money` | System/ERP | — |
| `subtotal` | `Money` | System | `sum(line.line_total for line in lines)` |
| `tax_total` | `Money` | System | `sum(line.tax_amount) + sum(order_level_tax_lines)` |
| `grand_total` | `Money` | System | `subtotal − order_discount + tax_total + shipping_amount` |
| `fulfillment_status` | enum (§5) | System | **derived**, never set directly — see §5 |
| `invoice_status` | enum (§5) | System | **derived**, never set directly |

### `OrderLine` — extended fields

| Field | Type | Provided by | Calculation |
|---|---|---|---|
| `product_key` | `str` | Reseller | — |
| `ordered_qty` | `Quantity` | Reseller | — |
| `unit_price` | `Money` | System/ERP (catalog) | — |
| `line_discount` | `Money` | System/ERP | — |
| `line_total` | `Money` | System | `round_money(ordered_qty.value * unit_price.amount − line_discount.amount)` |
| `tax_lines` | `list[TaxLine]` | ERP (tax engine) | `tax_amount = line_total * rate` (or extracted, if `inclusive`) |
| `fulfilled_qty` | `Quantity` | ERP (sum of shipment lines) | `sum(f.qty for f in fulfillments where line_id matches)` |
| `invoiced_qty` | `Quantity` | ERP (sum of invoice lines) | `sum(i.qty for i in invoices where line_id matches)` |

---

## 4. The other domains, same pattern

### `Fulfillment` (one shipment)

| Field | Provided by |
|---|---|
| `fulfillment_id` | System |
| `shipped_at` | ERP |
| `carrier`, `tracking_number` | ERP |
| `lines: [{order_line_id, qty: Quantity}]` | ERP |

### `Invoice`

| Field | Provided by |
|---|---|
| `invoice_id`, `erp_invoice_id` | ERP |
| `issued_at`, `due_at` | ERP |
| `lines: [{order_line_id, qty, unit_price, tax_lines}]` | ERP |
| `total: Money` | System — same `line_total`/`tax` formulas as §3, applied to invoice lines |
| `amount_paid` | System | `sum(payment.amount for payment in payments linked to this invoice)` |
| `balance_due` | System | `total − amount_paid` |

### `Payment`

| Field | Provided by |
|---|---|
| `payment_id` | System |
| `invoice_id` | ERP |
| `amount: Money`, `method`, `received_at` | ERP |

### `Return` / credit memo

| Field | Provided by |
|---|---|
| `return_id`, `erp_return_id` | ERP |
| `lines: [{order_line_id, qty, reason_code}]` | ERP |
| `credit_amount: Money` | System — same line-total formula, negative |

---

## 5. Status movement — branching, not linear

Today's `StatusApplier` walks a fixed list (`[confirm, fulfill, close]`) by index — it
cannot express "3 of 5 units shipped." Replace the index-walk with an explicit
**transition table** per domain: `{from_states} × trigger → to_state`. Order-level status
is **derived from line quantities**, not set directly by an ERP status string.

### Order lifecycle (submission side — unchanged)
`SUBMITTED → VALIDATED → READY_FOR_DELIVERY → SENT_TO_ERP` — same as today, no change needed here.

### `fulfillment_status` (derived, replaces part of today's `CanonicalStatus`)

| Condition on lines | `fulfillment_status` |
|---|---|
| all `fulfilled_qty == 0` | `UNFULFILLED` |
| `0 < fulfilled_qty < ordered_qty` for any line | `PARTIALLY_FULFILLED` |
| all `fulfilled_qty == ordered_qty` | `FULFILLED` |
| any line has `fulfilled_qty > ordered_qty`... | invalid — reject the fulfillment event, don't apply it |

This single rule replaces the old `CONFIRMED → FULFILLED` jump and *also* naturally
produces `PARTIALLY_FULFILLED` — no new status enum value needed on the ERP side, just a
`Fulfillment` record with less-than-full quantities.

### `invoice_status` (derived, same shape)

| Condition | `invoice_status` |
|---|---|
| no invoices | `NOT_INVOICED` |
| `sum(invoiced_qty) < sum(ordered_qty)` | `PARTIALLY_INVOICED` |
| `sum(invoiced_qty) == sum(ordered_qty)` and `balance_due == 0` on all invoices | `PAID` |
| `sum(invoiced_qty) == sum(ordered_qty)` and `balance_due > 0` | `INVOICED` (unpaid) |

### `CANCELLED` / `RETURNED` — side branches, not end-of-line

| From | Trigger | To |
|---|---|---|
| any pre-`FULFILLED` state | `cancel` | `CANCELLED` |
| `FULFILLED` or later | `cancel` | *rejected* — must go through `Return`, not cancel |
| `FULFILLED`/`INVOICED` + a `Return` record | — | order stays `FULFILLED`, but gains a visible `has_returns` flag — a return doesn't erase fulfillment history |

This is the generalization of today's `Order.cancel()` guard (`aggregate.py:132-135`), just
expressed as a table instead of one method's `if`.

---

## 6. ERP adapters don't all have to support all of this

Per ADR-0003, each adapter stays independent. Add one capability declaration per adapter:

```python
class ErpCapabilities(frozenset[str]):
    ...  # e.g. {"tax", "partial_fulfillment", "multi_currency", "returns"}
```

`DeliveryHandler` builds the **full** canonical payload always; an adapter only reads the
fields its `capabilities` include and ignores the rest — same graceful-degradation pattern
already proven for unregistered `erp_type` in `map_native_status` (returns `None`, doesn't
crash). Odoo's adapter today would declare `{}` (no tax, no partial fulfillment via webhook
— matches its documented gaps) and keep working exactly as it does now; nothing breaks.

---

## 7. Where this actually lands in code

| Change | File |
|---|---|
| `Money`, `Quantity`, `Address`, `Party`, `TaxLine` | new `src/shared/money.py`, `src/shared/quantity.py` |
| `OrderLine` gains pricing/tax/tracking fields | `src/modules/ordering/domain/models.py` |
| New events: `FulfillmentRecorded`, `InvoiceIssued`, `PaymentReceived`, `OrderReturned` | `src/modules/ordering/domain/events.py` |
| Derive `fulfillment_status`/`invoice_status` | new pure functions in `src/modules/ordering/domain/routing.py`-style module, called from `Order` aggregate |
| `uom_conversions` column | `items` table, migration |
| `ErpCapabilities` | `src/modules/integration/application/ports.py` |

## 8. Suggested build order (don't do this in one PR)

1. ✅ **Done.** `Money`/`round_money` (`src/shared/money.py`) and `OrderLine.quantity: Decimal`
   (`ordering/domain/models.py`) — `Decimal` is stringified before it hits a JSONB column
   (`aggregate.py`'s `OrderSubmitted` payload and `snapshot_state()`) and coerced back on
   load via `OrderLine.__post_init__`. Tests: `src/shared/tests/test_money.py`,
   `test_quantity_is_decimal_and_survives_event_replay_exactly` in `test_order_aggregate.py`.
   **Not yet covered by this step:** the projection (`OrderLineView`) and the payload
   handed to `OdooAdapter.submit` still carry `float` — they're read-only display/ERP-wire
   paths with no math performed on them yet, so hardening them has no payoff until step 2
   adds real calculations. `GraphQL` input/output types also stay `float` on purpose (no
   external API change in this step).
2. ✅ **Done.** `OrderLine` gained `unit_price`/`line_discount`/`tax_rates` (`Money`/`TaxRate`,
   `ordering/domain/models.py`), JSONB-safe (de)serialization via `OrderLine.to_dict`/
   `from_dict` (also replaced the old manual dict-building in `aggregate.py`). Pure
   calculation functions in new `ordering/domain/calculations.py`: `line_total`,
   `line_tax_total` (handles both inclusive-extracted and exclusive-added tax),
   `line_total_with_tax`, `order_subtotal`/`order_tax_total` (sum priced lines, raise on
   currency mismatch), `order_grand_total`. Tests: `ordering/tests/test_calculations.py`
   (unit + Hypothesis property tests — totality, tax-rate invariant, subtotal-equals-
   sum-of-lines) and a new event-replay round-trip test in `test_order_aggregate.py`.
   `pytest src tests`: 121 unit + 2 integration passed, 5 skipped (unchanged — no live
   Postgres/AWS in this environment).

2b. ✅ **Done** (follow-up to step 2, same increment). **The catalog is now the price
   source** — `Item.unit_price` (`catalog/domain/models.py`, migration `0005_item_price`),
   set via the operator `syncItem` mutation. `OrderService._priced()`
   (`ordering/application/order_service.py`) resolves it onto each line at submission
   time, before `OrderSubmitted` is emitted — see ADR-0011 for why the reseller never
   supplies a price. `line_total`/`subtotal` now flow end to end: projector → projection
   stores (both in-memory and Postgres, JSONB-safe) → GraphQL (`MoneyType`, both reseller
   and operator schemas) → UI (`ItemsPage` price input/column, both `OrderDetailPage`s
   show unit price/line total/subtotal). `order_discount`/`shipping` still aren't
   persisted on `Order` — still no event sets them, unchanged from step 2.
3. `fulfilled_qty`/`invoiced_qty` + derived `fulfillment_status`/`invoice_status` — the partial-fulfillment unlock.
4. `Fulfillment`/`Invoice`/`Payment`/`Return` as plain-CRUD lists — only once an ERP that actually reports these (SAP/NetSuite) is being onboarded.
5. `ErpCapabilities` — write it when the *second* adapter exists, not before (one adapter has nothing to differ from).
