# ADR-0010: Split `worker` into independently-scalable roles

| | |
|---|---|
| Status | Accepted — implemented |
| Affects | `src/worker` |

## In one sentence
`worker` reads a `WORKER_ROLE` env var (`all` by default) so each of its 6 jobs — 4
consumers, the relay, the reconciler — can be deployed and scaled as its own process from
the same image, instead of always running every job in one process.

## Why this needed a decision

| Problem | Detail |
|---|---|
| `worker` ran everything in one process | 4 SQS consumers, the outbox relay, and the reconciliation scheduler, each as a background thread, with no way to run a subset |
| Not every job scales the same way | The outbox relay is safe to run in multiple replicas (`SELECT ... FOR UPDATE SKIP LOCKED`); the SQS consumers too (dedup on `event_id`) |
| The reconciler was the exception | **Fixed separately** — `src/worker/connection_lock.py`'s `PostgresConnectionLock` (per-connection advisory lock) means two `worker` replicas no longer double-sweep; see ADR-0007. This removed the one blocker to splitting roles at all. |

## The decision
`Settings.worker_roles` (env `WORKER_ROLE`, default `all`) is a set of
`{order-processing, order-delivery, projections, webhook-dispatch, relay, reconcile}`.
`worker/main.py` only builds and starts the thread(s) for roles actually requested — no
SQS queue lookup, no thread, for a role this process doesn't run. Comma-separated values
combine lightweight roles into one process (e.g. `WORKER_ROLE=relay,reconcile`). The
default (`all`) reproduces today's exact single-process behavior — this is additive, not
a breaking change to how `worker` runs if nobody sets the env var.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Full microservices split (one deployable per queue) | Same reasoning as [ADR-0001](0001-modular-monolith.md) — more operational cost than the current problem justifies |
| Leave `worker` as one process, just don't scale it past 1 replica | Works but caps throughput and removes fault isolation — a stuck ERP call in `order-delivery` can starve `projections` in the same process |
| CLI flag (`--role=`) instead of an env var | Inconsistent with every other setting in this codebase (`APP_PROFILE`, `ERP_ADAPTER_MODE`, …), which are all env-driven (`Settings`, 12-factor) |

## Consequences

| | |
|---|---|
| ✅ | Per-role scaling and fault isolation is possible now — a dedicated ECS task per role, same image, different `WORKER_ROLE` |
| ✅ | Same image, same codebase — no new deployable to build or version |
| ✅ | Default behavior unchanged for anyone not setting `WORKER_ROLE` |
| ⚠️ | Terraform/ECS task-definition work to actually deploy N role-scoped tasks instead of one `all` task is separate, not yet done — this ADR covers the application-level mechanism, not the infra rollout |

## Revisit when
Actually deploying per-role ECS tasks (Terraform/CDK work) is undertaken — that's
infrastructure-design scope building on this, not a reason to revisit the mechanism here.
