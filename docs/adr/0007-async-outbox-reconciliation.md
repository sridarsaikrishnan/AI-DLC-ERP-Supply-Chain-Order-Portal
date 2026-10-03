# ADR-0007: Async delivery via outbox + queue, with polling as the fallback

| | |
|---|---|
| Status | Accepted |
| Affects | `worker`, `integration`, `src/shared/eventsourcing` |

## In one sentence
Order delivery to the ERP goes through a transactional outbox → queue pipeline, with a
scheduled poll as a correctness fallback that works even if webhooks never arrive.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Talking to an ERP is slow and unreliable | Shouldn't block a GraphQL request |
| ERP webhooks aren't trustworthy as the only signal | Can be missed, dropped, or never arrive — and some ERPs send "thin" webhooks with no real status in the payload |

## The decision

| Path | How it works |
|---|---|
| Write path | Order events land in Postgres inside the same transaction as an **outbox row**. A relay thread drains the outbox to SNS FIFO, which fans out to SQS FIFO queues (order-processing, order-delivery, projections, webhook-dispatch) consumed by `worker` |
| Fallback path | A `ReconcileScheduler` polls `adapter.fetch_status()` for every open order on a fixed interval (default 15 min), **independent of whether webhooks work at all** |

## Alternatives considered

| Option | Rejected because |
|---|---|
| Rely on webhooks only | Some ERPs send "thin" webhooks (just an ID, no status) or drop them entirely — a fully event-driven-only design has no correctness fallback |
| Synchronous ERP calls from `api` | Ties API response time to a third-party system's latency/availability |

## Consequences

| | |
|---|---|
| ✅ | A crash can never lose a committed event — the outbox write is transactional with the state change |
| ✅ | Even an ERP with unreliable or "thin" webhooks eventually reaches correct state — just on a 15-minute cadence instead of near-real-time |
| ✅ | The reconciliation scheduler takes a per-connection Postgres advisory lock before sweeping (`src/worker/connection_lock.py`) — running more than one `worker` replica no longer double-sweeps a connection; a replica that doesn't win the lock just skips it that cycle (see [ADR-0010](0010-worker-role-split.md), whose blocking concern this resolves) |

## Revisit when
The reconcile interval is too slow for a specific ERP/business need — tighten the
interval, or wire the webhook path to call `fetch_status` directly for thin-webhook ERPs.
