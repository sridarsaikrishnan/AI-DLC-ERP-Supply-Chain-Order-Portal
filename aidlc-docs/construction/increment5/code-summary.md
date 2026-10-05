# Increment 5 — Code Generation summary

Backend + GraphQL only (Q6=A). All 174 unit/integration tests pass (5 skipped = live
AWS/Postgres only); both GraphQL schemas and the memory + postgres containers build.

## New module: `quoting`
- `domain/models.py`: `Quote`, `QuoteLine`, `EndCustomer`, `Subsidiary`, `QuoteStatus`, `is_valid_on`.
- `domain/errors.py`: `QuoteNotFound`, `QuoteNotValid`, `PriceNotQuoted`.
- `application/service.py`: `QuoteService` (create subsidiary, issue quote, mark accepted).
- `application/ports.py` + `infrastructure/{memory,postgres}.py`: repositories (quotes JSONB lines + subsidiaries).
- `tests/test_quoting.py`.

## `catalog` (ADR-0016 — product-only)
- `Item` dropped `unit_price`/`tax_rate`/`line_discount`; added `kind` (`ItemKind` PHYSICAL/LICENSE).
- `CatalogService.sync_item` + postgres repo + fact payload updated; `items` table columns changed in migration 0008.

## `ordering`
- `OrderLine`: `line_id` (FR-A3) + `kind` (FR-D1); `from_dict` tolerant for legacy payloads.
- `OrderState`: `READY_FOR_DELIVERY` → `ACCEPTED`; `FULFILLED` removed; `DeliveryStatus` added. `restore()` maps legacy state values.
- `Order` aggregate: `accept()` (emits the unchanged `OrderReadyForDelivery` event); `record_fulfillment(line_id, qty, carrier, proof_of_delivery)`, `record_invoice(line_id, qty)`, `set_vendor_date(line_id, date)`; `shipped/delivered/invoiced_qty_by_line` + `vendor_date_by_line`; derived `fulfillment_status`/`delivery_status`/`invoice_status`. `OrderFulfilled` kept as a no-op apply for replay. New events `OrderLineVendorDateSet`; `OrderSubmitted`/`OrderLineFulfilled`/`OrderLineInvoiced` gained defaulted fields (replay-safe).
- `OrderService.place_order(quote_id, lines=[OrderLineInput])`: price from quote, kind from catalog, refuses unquoted lines.
- `adapters.py`: `read_payload` sends `order_id` + `erp_customer_id` (via `CustomerDirectory`); `StatusApplier` progression `CONFIRMED→CLOSED`.
- projections (read_models/store/postgres_store/projector): scores + delivered + parties + per-line vendor/scheduled date; shared `line_is_delivered` rule.

## `fulfillment`
- `FulfillmentRecorded`/`Fulfillment` gained `proof_of_delivery`; service keys lines by `line_id` and wraps the Fulfillment+Order writes in a `UnitOfWork` (FR-A4).

## `integration`
- `odoo_adapter`: partner = `int(erp_customer_id)` (fail-closed if absent); idempotency keyed on `order_id`.
- `status_mapping`: `CanonicalStatus.FULFILLED` removed; Odoo `done`→`CONFIRMED`.

## shared / wiring
- `src/shared/unit_of_work.py` (`UnitOfWork` port + `NullUnitOfWork`); `PostgresUnitOfWork` + ambient-session plumbing in `persistence/engine.py`; `PostgresEventStore.append` joins the ambient session (FR-A4).
- `composition.py`: wires quoting repos + `QuoteService`, `TenancyCustomerDirectory`, the UoW into fulfillment/invoice services, and `OrderService(repo, quotes, items, quote_service)`.

## GraphQL
- Reseller: `placeOrder(quoteId, …)`, `quotes`/`quote`, order scores + `deliveryStatus` + `parties` + per-line `kind`/`scheduledDate`/shipped/delivered/invoiced.
- Operator: `issueQuote`, `createSubsidiary`, `subsidiaries`, `quotes`, `setVendorDate`; `recordFulfillment` with `lineId`/`proofOfDelivery`; `syncItem` with `kind` (no price); order `deliveryStatus` + `parties`.

## Migration
- `0008_increment5`: items product-only + `kind`; order party columns; `subsidiaries` + `quotes` tables.

## UI (done — Q6=A deferral lifted on request)
`ui/` updated to the new GraphQL shape and built in the existing design system:
- API/query/type layer (`api/queries/orders.ts`, `api/queries/admin.ts`) + hooks (`useOrders`, `useAdmin`).
- Reseller: quote-driven `NewOrderPage`, new `features/quotes/QuotesPage`, `OrderDetailPage` scores/delivered/parties/kind/scheduled.
- Operator: new `features/admin/QuotesPage` (issue) + `SubsidiariesPage`; `ItemsPage` edits `kind` (no price); `OrderDetailPage` scores/delivery/parties + record-shipment + set-vendor-date controls.
- `routes.tsx` + `App.tsx` nav extended. `npm run build` clean.

## Tooling (now runnable + green)
- Installed `ruff==0.6.9` + `import-linter==2.1`. Fixed a pre-existing import-linter config gap (`include_external_packages=true`). Split `SecretsManagerSecretStore` → `src/shared/secrets/aws.py` so the port stays SDK-free; both import-linter contracts KEPT. Safe ruff autofixes applied to Increment 5 files; remaining ruff findings are pre-existing repo-wide style (E501/TCH/E402), left as a separate cleanup.

## Deliberately deferred
- A standalone Vendor Order document (FR-E2); automatic fulfillment/invoice capture from Odoo (operator-entered only).
