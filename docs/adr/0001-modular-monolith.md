# ADR-0001: Modular monolith, not microservices

| | |
|---|---|
| Status | Accepted |
| Affects | Whole system |

## In one sentence
One codebase, split into two deployables (`api`, `worker`) that talk to each other only
through in-process function calls behind ports — never a network call between modules.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Need clean bounded contexts | catalog, connections, tenancy, ordering, integration, webhooks — without the codebase turning into a ball of mud |
| Small footprint today | One team, one Postgres's worth of data, one ERP live at time of writing — no current pressure to deploy or scale any module independently |

## The decision

| Deployable | Runs | Talks to |
|---|---|---|
| `api` | GraphQL (reseller + operator), inbound ERP webhook HTTP route | Postgres, Cognito |
| `worker` | SQS consumers, outbox relay, reconciliation sweeper | Postgres, SQS/SNS, the ERP, reseller webhooks |

**Two hard rules:**
- Modules call each other through plain Python function calls behind ports (interfaces) — never a network call between modules.
- Layering is enforced at build time: `import-linter` blocks `domain`/`shared` code from importing `boto3`, `fastapi`, or `strawberry`.

## Alternatives considered

| Option | Rejected because |
|---|---|
| One service per bounded context (microservices) | Pays for service discovery, distributed tracing, and network failure modes with no current need for independent scaling or deploy cadence |
| Single undifferentiated app (no `api`/`worker` split) | Synchronous request handling and long-running ERP/queue work have different failure and scaling profiles — worth separating even inside a monolith |

## Consequences

| | |
|---|---|
| ✅ | One deploy pipeline, no network hop between modules, fast to develop |
| ✅ | Module boundaries are enforced by tooling (`import-linter`), not just convention — splitting a module out later is a lift-and-shift, not an untangling job |
| ⚠️ | `api` and `worker` each share fate internally — a bug in one module can affect everything else in the same process |
| ⚠️ | Scaling today is per-deployable, not per-module (see [ADR-0010](0010-worker-role-split.md)) |

## Revisit when
A specific module needs a deploy cadence the others don't, a second team owns a module and
can't share the release train, or shared-Postgres contention becomes measurable at higher
ERP/tenant counts.
