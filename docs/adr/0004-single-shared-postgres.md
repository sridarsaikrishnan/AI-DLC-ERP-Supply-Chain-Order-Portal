# ADR-0004: One shared Postgres for everything

| | |
|---|---|
| Status | Accepted |
| Affects | Whole system |

## In one sentence
The event store, the outbox, every read-side projection, and all plain config/CRUD tables
live in one Postgres database — no second datastore anywhere.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Several different storage shapes, one system | An event store (for `Order`), an outbox (for reliable event publishing), read-side projections, and plain config/CRUD tables (connections, items, bindings) all need somewhere to live |

## The decision

| | |
|---|---|
| Storage | All of it in one Postgres database (Aurora Serverless v2 in AWS) — no second datastore for events, no separate store for projections |
| Boundaries | Enforced in code (the `import-linter` layering contract), not by database separation |

## Alternatives considered

| Option | Rejected because |
|---|---|
| A dedicated event-store product (e.g. EventStoreDB) | A second datastore to operate, back up, and monitor — for a system with one Postgres's worth of load |
| Database-per-module | No current operational need (no independent scaling, no separate team ownership); would add cross-database transaction/consistency problems for no benefit yet |

## Consequences

| | |
|---|---|
| ✅ | Simple operationally — one connection pool, one backup story, one place to look for data |
| ✅ | The outbox pattern works cleanly: an Order's new events and its outbox row commit in the **same transaction**, so a crash can never lose a committed event |
| ⚠️ | Every module's write load lands on the same database — at high enough ERP/tenant volume this becomes a shared bottleneck |

## Revisit when
A specific module's read/write volume starts measurably contending with the rest (the same
trigger named in [ADR-0001](0001-modular-monolith.md) — they'd likely be reconsidered
together).
