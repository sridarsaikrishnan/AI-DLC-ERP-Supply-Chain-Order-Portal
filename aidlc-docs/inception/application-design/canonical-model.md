# Canonical Model, Inputs & Outputs — ERP & Supply Chain Order Portal

This document shows, concretely, what a reseller **sends in**, the **canonical model** the platform works with internally, and what the reseller **gets back**. It uses proper type, field, and operation names so it reads like the real thing. Types will be finalized in Functional Design, but names here are intended to carry through to code.

> Golden rule (FR-19 / AC-02): reseller-facing inputs and outputs contain **no ERP name, instance, or ERP record id**. Internal canonical objects may carry an `owningConnectionId`; the reseller-facing view types never do. This is enforced by using **separate types** (`SalesOrder` internal aggregate vs `SalesOrderView` reseller DTO), not by filtering fields at runtime.
>
> All sample values below are illustrative and fictional; they are not seed data.

---

## 1. Shared value types

```java
// Money is always an amount + ISO-4217 currency. No floating point for money.
record Money(BigDecimal amount, String currencyCode) {}          // e.g. (129.50, "EUR")

record Quantity(BigDecimal value, String unitOfMeasure) {}       // e.g. (10, "EA")

record Address(
    String line1, String line2, String city,
    String region, String postalCode, String countryCode) {}    // countryCode ISO-3166 alpha-2

enum OrderType { SALES, PURCHASE }

// The exact lifecycle words from the design system.
enum OrderLifecycleStatus {
    DRAFT, SUBMITTED, VALIDATED, SENT_TO_ERP,
    CONFIRMED, FULFILLED, CLOSED,                                 // normal
    RETRYING, REJECTED                                           // exceptions
}
```

---

## 2. Reseller INPUT (GraphQL, `/graphql`)

The reseller never sends a customer or any ERP detail. The customer is resolved from the tenant's verified binding; routing is derived from item ownership. `externalReference` is the reseller's own id and is used for idempotency.

```graphql
input CreateSalesOrderInput {
  externalReference: String!          # reseller's own order id (idempotency key)
  currencyCode: String!               # ISO-4217, e.g. "EUR"
  requestedDeliveryDate: Date
  lines: [CreateOrderLineInput!]!
  note: String                        # free text, reseller-safe
}

input CreateOrderLineInput {
  itemId: ID!                         # platform item id (NOT an ERP/sku from an ERP)
  quantity: Float!
  unitOfMeasure: String!              # e.g. "EA"
}

type Mutation {
  createSalesOrder(input: CreateSalesOrderInput!): SalesOrderView!
  updateSalesOrder(orderId: ID!, input: UpdateSalesOrderInput!): SalesOrderView!
  cancelSalesOrder(orderId: ID!, reason: String): SalesOrderView!
}
```

### Sample request (illustrative)
```json
{
  "externalReference": "PO-2026-000481",
  "currencyCode": "EUR",
  "requestedDeliveryDate": "2026-10-15",
  "lines": [
    { "itemId": "itm_7f3a9c20", "quantity": 10, "unitOfMeasure": "EA" },
    { "itemId": "itm_1b6d0e4a", "quantity": 2,  "unitOfMeasure": "EA" }
  ],
  "note": "Deliver to north dock"
}
```

---

## 3. Internal CANONICAL model

The platform-owned shape, identical for every tenant. This is the aggregate the domain works with; it carries internal fields (like `owningConnectionId`) that never reach a reseller.

```java
record SalesOrder(
    OrderId orderId,                 // platform UUID, e.g. "ord_9c1e..."
    String orderNumber,             // platform-generated human ref, e.g. "SO-100482"
    TenantId tenantId,
    OrderType type,                 // SALES
    OrderLifecycleStatus status,
    String externalReference,       // echoed back to the reseller
    CustomerRef customer,           // resolved from the (tenant, connection) binding
    String currencyCode,
    List<OrderLine> lines,
    OrderTotals totals,
    ConnectionId owningConnectionId, // INTERNAL ONLY — never in a reseller view (FR-19)
    Instant createdAt,
    Instant updatedAt,
    List<StatusHistoryEntry> statusHistory
) {}

record OrderLine(
    LineId lineId,
    ItemRef item,                   // itemId + sku (sku is platform-side, ERP-neutral)
    Quantity quantity,
    Money unitPrice,
    Money lineTotal
) {}

record OrderTotals(Money subtotal, Money tax, Money grandTotal) {}

record StatusHistoryEntry(
    OrderLifecycleStatus status,
    Instant occurredAt,
    String resellerSafeNote         // e.g. "Order accepted", never raw ERP text
) {}

// Read-only for resellers (FR-10). Owning ERP is internal only.
record Item(
    ItemId itemId, String sku, String name, String description,
    String unitOfMeasure, Money listPrice, boolean active,
    ConnectionId owningConnectionId // INTERNAL ONLY
) {}

// Linked, read-only (FR-11). ERP record id is internal only.
record Customer(
    CustomerId customerId, String displayName,
    Address billingAddress, Address shippingAddress, String taxId,
    ConnectionId connectionId, String erpCustomerId // INTERNAL ONLY
) {}
```

`PurchaseOrder` mirrors `SalesOrder` with a `SupplierRef supplier` instead of `customer`.

---

## 4. Reseller OUTPUT (GraphQL view types)

Reseller-facing types are a **separate set** with the internal-only fields structurally absent. There is one canonical output shape for every tenant (FR-06).

```graphql
type SalesOrderView {
  orderId: ID!
  orderNumber: String!              # platform ref, e.g. "SO-100482"
  externalReference: String!
  status: OrderStatus!              # DRAFT..CLOSED, RETRYING, REJECTED
  currencyCode: String!
  lines: [OrderLineView!]!
  totals: OrderTotalsView!
  createdAt: DateTime!
  updatedAt: DateTime!
  timeline: [StatusEventView!]!
  # NOTE: no owningConnectionId, no ERP name/instance/record id
}

type OrderLineView {
  lineId: ID!
  itemId: ID!
  itemName: String!
  quantity: Float!
  unitOfMeasure: String!
  unitPrice: MoneyView!
  lineTotal: MoneyView!
}

type StatusEventView { status: OrderStatus!, occurredAt: DateTime!, note: String }
type MoneyView { amount: String!, currencyCode: String! }   # string amount to avoid float loss
```

### Sample response (illustrative)
```json
{
  "orderId": "ord_9c1e77a2",
  "orderNumber": "SO-100482",
  "externalReference": "PO-2026-000481",
  "status": "SENT_TO_ERP",
  "currencyCode": "EUR",
  "lines": [
    { "lineId": "ln_1", "itemId": "itm_7f3a9c20", "itemName": "Widget A",
      "quantity": 10, "unitOfMeasure": "EA",
      "unitPrice": { "amount": "12.50", "currencyCode": "EUR" },
      "lineTotal": { "amount": "125.00", "currencyCode": "EUR" } }
  ],
  "totals": {
    "subtotal": { "amount": "125.00", "currencyCode": "EUR" },
    "tax":      { "amount": "23.75",  "currencyCode": "EUR" },
    "grandTotal": { "amount": "148.75", "currencyCode": "EUR" }
  },
  "createdAt": "2026-09-21T09:14:02Z",
  "updatedAt": "2026-09-21T09:14:07Z",
  "timeline": [
    { "status": "SUBMITTED", "occurredAt": "2026-09-21T09:14:02Z", "note": "Order received" },
    { "status": "VALIDATED", "occurredAt": "2026-09-21T09:14:05Z", "note": "Order validated" },
    { "status": "SENT_TO_ERP", "occurredAt": "2026-09-21T09:14:07Z", "note": "Order sent for fulfillment" }
  ]
}
```

### Rejection output (mixed-ERP or invalid) — reseller-safe (FR-18/FR-19)
```json
{
  "orderId": "ord_9c1e77a2",
  "status": "REJECTED",
  "timeline": [
    { "status": "REJECTED", "occurredAt": "2026-09-21T09:14:05Z",
      "note": "Items on this order cannot be fulfilled together. Please place them as separate orders." }
  ]
}
```

---

## 5. ERP-native side (internal, via MappingEngine)

Each ERP has its own native shape **and its own protocol** (verified 2026-09-21): **Odoo** via XML-RPC/JSON-RPC `create` on the `sale.order` ORM model; **ERPNext** via REST `POST /api/resource/Sales Order`. The `DeclarativeMappingEngine` converts canonical↔native field values using version-controlled field maps; the per-ERP transport adapter handles the call itself. No ERP-native structure or protocol detail is ever exposed to resellers.

```
SalesOrder (canonical)  --toNative(connectionId)-->  Map<String,Object> (Odoo sale.order / ERPNext Sales Order)
NativeStatusChange      --toCanonical(connectionId)-->  OrderLifecycleStatus + resellerSafeNote
```

## 5a. Status mapping table — canonical ↔ Odoo & ERPNext

Grounded in verified native vocabularies (2026-09-21). **Platform-side** statuses are set by our platform and have no native ERP equivalent; **ERP-derived** statuses are computed by the ingestion `statusDerivation` from multiple native fields. Version caveats tracked in O-12/O-14; final tables confirmed in Functional Design.

| Canonical `OrderLifecycleStatus` | Origin | Odoo (`sale.order`) | ERPNext (`Sales Order`) |
|---|---|---|---|
| `DRAFT` | Platform-side | — (order not yet sent to Odoo) | — (not yet created) |
| `SUBMITTED` | Platform-side | — | — |
| `VALIDATED` | Platform-side | — | — |
| `SENT_TO_ERP` | Platform-side (set when the ERP `create` call succeeds) | record created; `state` typically `draft`/`sent` pre-confirm, or `sale` if auto-confirmed | record created; `docstatus = 0` (Draft) or `1` if submitted on create |
| `CONFIRMED` | ERP-derived | `state = 'sale'` (delivery not yet full) | `docstatus = 1` and `status ∈ {To Deliver and Bill, To Deliver, To Bill}` |
| `FULFILLED` | ERP-derived | `state = 'sale'` and `delivery_status = 'full'` | `docstatus = 1` and `status = 'Completed'` (or `%Delivered = 100`) |
| `CLOSED` | ERP-derived / platform | `locked = true` (order locked/done; version-dependent) | `status = 'Closed'` |
| `RETRYING` | Platform-side (delivery failed, queued to retry) | — | — |
| `REJECTED` | ERP-derived / platform | our `create`/confirm failed, or `state = 'cancel'` | submit validation error, or `docstatus = 2` (Cancelled) in response to our action |

Notes:
- Odoo tracks fulfillment/billing outside `state` (in `delivery_status` / `invoice_status`); `FULFILLED` therefore needs `delivery_status`, not `state` alone.
- ERPNext `status` blends delivery + billing; `docstatus` gives the submit/cancel axis. Both are needed.
- `On Hold` (ERPNext) and partial delivery (`To Deliver`, `%Delivered < 100`) remain `CONFIRMED` in the canonical model for the MVP (no separate "partially fulfilled" canonical state — revisit if needed).
- First-match-wins ordering applies (evaluate `FULFILLED`/`CLOSED`/`REJECTED` before the broader `CONFIRMED`).

## 5b. Illustrative field mapping (data)

A mapping is data, e.g. (illustrative):
```yaml
# mappings/odoo/sales-order.yaml  (version-controlled, Q2=B)
target: "sale.order"
fields:
  - { from: "externalReference", to: "client_order_ref" }
  - { from: "customer.erpCustomerId", to: "partner_id", transform: "toInt" }
  - { from: "currencyCode", to: "currency_id", lookup: "currencyByCode" }
lines:
  path: "order_line"
  fields:
    - { from: "item.sku", to: "product_id", lookup: "productBySku" }
    - { from: "quantity.value", to: "product_uom_qty" }
# Canonical status is DERIVED from MULTIPLE native fields, not a single lookup (verified 2026-09-21):
#   Odoo:    sale.order.state (draft|sent|sale|cancel) + delivery_status + invoice_status
#   ERPNext: docstatus (0 draft | 1 submitted | 2 cancelled) + status (To Deliver and Bill|To Bill|Completed|Closed|Cancelled) + %Delivered
statusDerivation:
  odoo:
    - { when: "state == 'sale' && delivery_status == 'full'", canonical: FULFILLED }
    - { when: "state == 'sale'",                              canonical: CONFIRMED }
    - { when: "state == 'cancel'",                            canonical: REJECTED }
  erpnext:
    - { when: "docstatus == 1 && status == 'Completed'",      canonical: FULFILLED }
    - { when: "docstatus == 1 && status == 'Closed'",         canonical: CLOSED }
    - { when: "docstatus == 1",                               canonical: CONFIRMED }
    - { when: "docstatus == 2",                               canonical: REJECTED }
# Note: SENT_TO_ERP is a platform-side status set when the create call succeeds (before the ERP confirms),
#       not a native ERP state. Full derivation tables are finalized in Functional Design (see O-14).
```
