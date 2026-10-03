# ADR-0002: Event-source the `Order` aggregate only

| | |
|---|---|
| Status | Accepted |
| Affects | `ordering` module, `src/shared/eventsourcing` |

## In one sentence
Only `Order` replays its state from an immutable event stream — every other module is
plain CRUD rows in the same Postgres.

## Why this needed a decision

| Problem | Detail |
|---|---|
| `Order` has a real lifecycle to protect | Can't confirm before submitting, can't cancel after fulfilled — and it needs an audit trail of what happened and when |
| Everything else is just config/lookup data | `connections`, `items`, `tenant_connection_bindings` get created, updated, sometimes deleted — there's no meaningful "history of what happened" worth replaying |

## The decision

| | |
|---|---|
| `Order` | Event-sourced. State changes exclusively through emitted, immutable events (`OrderSubmitted`, `OrderValidated`, `OrderConfirmed`, …), replayed to rebuild state |
| Everything else | Plain CRUD rows, same Postgres database — no event stream, no replay |

## Alternatives considered

| Option | Rejected because |
|---|---|
| Event-source every aggregate | Most modules have no business need for a full history; adds replay/snapshot complexity for no payoff |
| CRUD for `Order` too (just an `orders` table with a `status` column) | Loses the audit trail and the ability to safely apply idempotent, guarded transitions under at-least-once delivery — both real requirements for an order pipeline talking to external ERPs |

## Consequences

| | |
|---|---|
| ✅ | One database serves two read models (event-sourced writes for `Order`, plain rows for everything else) without standing up a second datastore |
| ✅ | Order transitions are idempotent by construction (`confirm()`, `fulfill()`, `close()` no-op if already in the target state) — safe for SQS at-least-once redelivery |
| ⚠️ | Adding event sourcing to another aggregate later means learning this pattern fresh each time — it's not a reusable "just add events" toggle |

## Revisit when
Another aggregate needs the same guarantees `Order` needs (idempotent transitions under
retries, full audit history) — not just "would be nice to know what changed."
