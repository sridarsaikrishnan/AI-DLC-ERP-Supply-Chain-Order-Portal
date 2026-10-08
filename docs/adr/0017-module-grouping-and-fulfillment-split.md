# 0017 — Group modules by subdomain; split `fulfillment` into its own aggregates

**Status:** Accepted — **amended:** `payments` and `returns` removed

> **Amendment:** the split below originally produced four modules. `payments` and `returns`
> were later deleted. They never changed an order's status, so they were not an extraction
> target worth keeping. `sales/` is now `ordering`, `quoting`, `shipment`, `invoicing`.

## In one sentence

The flat `src/modules/*` list is regrouped into three subdomain folders — `sales/`
(order lifecycle), `reference/` (master data), `integration/` (edges) — and the overloaded
`fulfillment` module is split so shipment and invoicing are their own modules.

## Why this needed a decision

| Problem | Detail |
|---|---|
| `fulfillment` was four things | One module held the `Fulfillment`, `Invoice`, `Payment`, and `Return` aggregates. They share nothing but the kernel; bundling them hid four independent lifecycles behind one name. |
| "Fulfillment" overloaded two meanings | The *act of dispatching* (carrier/tracking/POD) and the *quantity score* on the order (`fulfillment_status`) were both called "fulfillment". |
| Flat module list didn't show intent | `ordering`, `catalog`, `connections`, `tenancy`, `integration`, `webhooks_*` sat side by side with no signal of which are order-lifecycle vs. master-data vs. edge concerns. |
| Future extraction | We want pulling a module into its own service to be a move, not a refactor. That is easier when the folder boundary already matches the subdomain boundary. |

## The decision

**Grouping** (`src/modules/<group>/<module>/`):

- `sales/` — order lifecycle: `ordering`, `quoting`, `shipment`, `invoicing` (`payments` and `returns` were removed; see the amendment)
- `reference/` — master data: `catalog`, `connections`, `tenancy`
- `integration/` — edges: `erp` (ERP connectivity), `webhooks_inbound`, `webhooks_outbound`

**Split** — `fulfillment` → `shipment` + `invoicing`, each its own module and event-sourced
aggregate. (`payments` and `returns` were created in the same split and later removed.)
The dispatch aggregate is named **`Shipment`**
(`ShipmentRecorded` event, `shipment_service` on the container). The operator
`recordShipment` mutation was later removed: a shipment is a done ERP delivery, recorded
by the reconciliation sweeper.
"Delivery" is deliberately *not* used as the aggregate name — it is a downstream status a
carrier-tracking integration (e.g. AfterShip) would later drive, not the act of dispatch.

**Kept, on purpose:** the order's quantity-score vocabulary — `Order.record_fulfillment`,
`fulfillment_status`, `FulfillmentStatus`, the `OrderLineFulfilled` event. These describe
*how much of the order is fulfilled*, which is a score on the order, not the shipment act.
`ShipmentService` records a `Shipment` and then bumps that score. Keeping the two words
distinct (shipment = the act, fulfillment = the resulting score) is the point, not an
inconsistency.

A new `import-linter` contract enforces that `reference` is a leaf (it must not import
`sales` or `integration`).

## Alternatives considered

- **Leave `fulfillment` as one module** — rejected: it buries four unrelated lifecycles and
  blocks extracting any one of them cleanly.
- **Group name `order/`** — rejected: `order/ordering` stutters. `sales/` reads cleanly and
  covers quoting, shipment, and invoicing too.
- **Rename the aggregate `Delivery`** — rejected: delivery is a status, not the dispatch
  event; reserving the word avoids a second rename when carrier tracking arrives.
- **Collapse `integration/erp` to `integration`** — rejected: keeping the `erp/` module (with
  per-ERP code to live under `erp/adapters/<erp>/` when a second ERP appears) leaves room for
  non-ERP integrations as siblings and gives per-ERP separation without flattening.

## Consequences

| | |
|---|---|
| ✅ | Each aggregate is now its own module — the natural seam for a future service extraction. |
| ✅ | Folder layout communicates subdomain intent; `reference` leaf-ness is machine-checked. |
| ✅ | "Shipment" vs. "fulfillment score" ambiguity removed at the API and module level. |
| ⚠️ | The dispatch→order coupling is still **synchronous** here (`ShipmentService`/`InvoiceService` update the `Order` in one transaction via the `UnitOfWork`). That cross-aggregate transaction is the real extraction blocker and is addressed next (see "Revisit when"). |
| ⚠️ | `sales` still imports `CanonicalStatus` from `integration.erp` (in `ordering`'s adapters), so a `sales`-independence contract is **not** added yet. |
| ⚠️ | Event class names were renamed (`FulfillmentRecorded` → `ShipmentRecorded`). The event registry is keyed by class name, so events stored under the old name would not replay — acceptable only because this is pre-production with no durable event history to preserve. |

## Revisit when

The follow-up commit converts the synchronous `Shipment`/`Invoice` → `Order` coupling into
an **event-driven saga** (ordering consumes `ShipmentRecorded`/`InvoiceRecorded` instead of
these services touching the order directly), drops the cross-aggregate `UnitOfWork`, and
moves `CanonicalStatus` to the shared kernel — superseding FR-A4's single-transaction
guarantee with eventual consistency. That is what makes the modules genuinely extractable;
this ADR is the structural half, that is the behavioral half.
