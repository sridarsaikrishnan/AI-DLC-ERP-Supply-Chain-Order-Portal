# ADR-0010: Split `worker` into independently-scalable roles

| | |
|---|---|
| Status | Proposed — not yet implemented |
| Affects | `src/worker` |

## In one sentence
Give `worker` a role flag so each of its 4 jobs can be deployed and scaled independently
from the same image — except the reconciler, which needs a locking fix first.

## Why this needed a decision

| Problem | Detail |
|---|---|
| `worker` runs everything in one process today | 4 SQS consumers, the outbox relay, and the reconciliation scheduler, each as a background thread |
| Not every job scales the same way | The outbox relay is safe to run in multiple replicas (`SELECT ... FOR UPDATE SKIP LOCKED`); the SQS consumers too (dedup on `event_id`) |
| The reconciler is the exception | **Not safe to duplicate** — no per-connection locking, so two `worker` replicas today both sweep every connection on the same timer, doubling ERP API load every cycle |

## The decision (proposed)
- Give `worker`'s entrypoint a role flag (`--role=order-processing`, `--role=delivery`,
  `--role=relay`, `--role=reconcile`, …) so each consumer/relay/reconciler can be deployed
  and scaled as its own ECS task, from the same image.
- Fix the reconciler specifically: either an advisory lock per connection, or keep it a
  singleton task while everything else scales freely.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Full microservices split (one deployable per queue) | Same reasoning as [ADR-0001](0001-modular-monolith.md) — more operational cost than the current problem justifies |
| Leave `worker` as one process, just don't scale it past 1 replica | Works today but caps throughput and removes fault isolation — a stuck ERP call in `order-delivery` can starve `projections` in the same process |

## Consequences (expected)

| | |
|---|---|
| ✅ | Per-consumer scaling and fault isolation, without adopting a fully choreographed/microservices architecture |
| ✅ | Same image, same codebase — no new deployable to build or version |
| ⚠️ | Still requires fixing the reconciler's lack of locking before this is safe to actually scale past one `worker` replica |

## Status
Not yet implemented. This ADR records the plan and the reason it's needed, ahead of the work.
