# 0018 — Shipment/invoice → order is an event-driven saga, not one transaction

**Status:** Accepted (supersedes the atomic guarantee of FR-A4)

## In one sentence

Recording a shipment or an invoice no longer updates the `Order` in the same transaction;
it just saves its own aggregate and publishes `ShipmentRecorded`/`InvoiceRecorded`, and a
dedicated ordering consumer reacts to those events and bumps the order's quantity scores —
eventual consistency in exchange for genuinely independent modules.

## Why this needed a decision

| Problem | Detail |
|---|---|
| FR-A4 forced a cross-aggregate transaction | `ShipmentService`/`InvoiceService` loaded, mutated, and saved the `Order` inside a `UnitOfWork` alongside their own aggregate's save — one transaction spanning two aggregates (and, in the module split from ADR-0017, two modules). |
| That transaction is the extraction blocker | ADR-0017 made `shipment`/`invoicing` their own modules, but a shared write transaction means they can't be pulled into their own service without a distributed transaction. The folder split was cosmetic until this coupling was removed. |
| It also needed an ambient-session hack | `PostgresUnitOfWork` stashed a thread-local session that `PostgresEventStore.append` had to detect and join — machinery that existed only to make two aggregates commit together. |

## The decision

- `ShipmentService.record()` / `InvoiceService.record()` save only their own aggregate.
  The aggregate's event (`ShipmentRecorded` / `InvoiceRecorded`) is published — to the bus
  in the memory profile, via the outbox → relay → `order-fulfillment.fifo` queue in the
  postgres/AWS profile.
- A new ordering consumer, `OrderFulfillmentConsumer` (the `order-fulfillment` worker role),
  reacts to those two event types, loads the `Order`, and calls `record_fulfillment` /
  `record_invoice`. It depends only on the **event-type string and payload shape** — it
  does not import the `shipment`/`invoicing` modules. That is what lets `sales` drop its
  import of `integration` and earns the new "Sales does not import integration" contract.
- The `UnitOfWork` port, `NullUnitOfWork`, `PostgresUnitOfWork`, and the event store's
  ambient-session support are **removed**. Each aggregate append owns its own transaction
  (events + their outbox rows still commit together — the no-dual-write guarantee is
  per-aggregate and untouched).

Idempotency is unchanged in shape: `record_fulfillment`/`record_invoice` are additive, so
the consumer relies on the same `event_id` dedupe every other consumer uses (the worker's
`processed_events` wrapper; the in-memory bus's per-consumer dedupe).

## Alternatives considered

- **Keep the `UnitOfWork` (FR-A4 as written)** — rejected: it is exactly the coupling that
  blocks extraction, and it only ever protected a same-process, same-DB write.
- **Two-phase / distributed transaction across modules** — rejected: enormous complexity for
  a guarantee the saga gives us well enough; the order score is derivable and self-healing.
- **Have ordering import and call shipment/invoicing** — rejected: reinstates the module
  dependency in the other direction.

## Consequences

| | |
|---|---|
| ✅ | `shipment`/`invoicing`/`payments`/`returns` are now extractable — no shared write transaction with `ordering`. |
| ✅ | `sales` no longer imports `integration` (`CanonicalStatus` moved to `shared`); both facts are machine-enforced by import-linter contracts. |
| ✅ | Less machinery: the UoW port and the event store's thread-local ambient session are gone. |
| ⚠️ | **Eventual consistency**: between saving a shipment and the order's score updating there is now a bus/queue hop. In the memory profile `drain()` closes it synchronously; in postgres it's as-fast-as-the-relay/queue. A reader can briefly see a shipment recorded but the order score not yet bumped. |
| ⚠️ | A failure after the shipment is saved but before the order consumer succeeds leaves them temporarily divergent; at-least-once redelivery + dedupe converges them (worst case the message lands in the DLQ for operator triage, same as any other consumer). |
| ⚠️ | Supersedes FR-A4's "in one transaction" wording — recorded here rather than silently dropped. |

## Revisit when

A real business requirement needs a shipment and its order score to be atomically
consistent (e.g. a regulatory audit that cannot tolerate the brief divergence). Nothing
asks for that today, and the scores are derived/self-healing, so the saga's eventual
consistency is the right trade for independent modules.
