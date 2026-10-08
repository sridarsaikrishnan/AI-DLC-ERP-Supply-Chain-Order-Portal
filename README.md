# ERP & Supply Chain Order Portal

A multi-tenant portal that routes reseller orders to the ERP system that owns each item
(Odoo today; more via a small registration checklist — see `docs/adding-an-erp.md`), with
event-sourced orders, a transactional-outbox/SNS/SQS async pipeline, and a GraphQL API
split by audience (reseller vs. operator, so ERP identity never reaches a reseller — FR-19).

**Start here for how it actually works**:
`aidlc-docs/inception/application-design/target-architecture.md` (the one architecture
doc — AI-DLC's design-of-record, kept current in place rather than forked into a second
file; its "Implementation status" note at the top lists what changed since it was
drafted), `docs/database-schema.md` (every table), and
`docs/event-sourcing-explained.md` (why events instead of just updating rows).

## New here? What you're actually getting into

**It's a modular monolith, not microservices.** Every bounded context in `src/modules/`
(`sales/` — ordering, quoting, shipment, invoicing; `reference/` — connections, tenancy;
`integration/` — erp, webhooks_inbound, webhooks_outbound) runs inside the **same two
Python processes** — `api` and `worker` —
sharing one codebase and one Postgres database. Modules call each other through plain
Python function calls behind ports (interfaces), not network calls; nothing is deployed
or scaled independently. The only real process boundary is `api` ↔ `worker`, and even
that talks through Postgres + SQS, not direct RPC. This was a deliberate choice (see
`aidlc-docs/aidlc-state.md`'s Architectural Decisions): clean module boundaries so it
*could* be split into services later if a specific module ever needs independent scaling,
without paying microservices' operational cost (service discovery, distributed tracing,
network failure modes) up front for a system that doesn't need it yet.

**The three moving parts, in plain terms:**

| Process/service | What it does | Talks to |
|---|---|---|
| **`api`** (FastAPI) | Serves GraphQL (`/graphql/reseller`, `/graphql/operator`) and inbound ERP webhooks. Handles reads and synchronous writes (place/cancel an order). | Postgres, Cognito (auth) |
| **`worker`** | 4 SQS consumers (order-processing, order-delivery, projections, webhook-dispatch) + the outbox relay + the reconciliation scheduler. Everything asynchronous — talking to the ERP, building read models, sending outbound webhooks — happens here, not in `api`. | Postgres, SQS/SNS, the ERP (Odoo), reseller webhook endpoints |
| **`ui`** (React SPA) | The reseller and operator web app. Talks to `api` over GraphQL only — it has no direct database or queue access. | `api` |

```mermaid
flowchart LR
    UI["ui - React SPA"] -->|GraphQL| API["api - FastAPI"]
    API --> PG["Postgres - events, outbox, projections"]
    API --> COG["Cognito, floci locally"]
    WORKER["worker - SQS consumers"] --> PG
    WORKER --> SQS["SNS and SQS, floci locally"]
    WORKER --> ODOO["Odoo, or another ERP"]
    WORKER --> HOOK["reseller webhook endpoints"]
    ODOO -->|inbound webhook| API
```

**One database, two read models.** Writes to the transactional aggregates (`Order`,
`Shipment`, `Invoice`) go through events (`docs/event-sourcing-explained.md`); everything
else (connections, bindings, quotes) is plain CRUD rows. Same Postgres instance either
way — there's no second datastore to stand up.

## Tech stack
**Backend**: Python 3.11 · FastAPI + Strawberry GraphQL · SQLAlchemy + PostgreSQL (event
store + outbox + projections + config, one database) · boto3 against SNS/SQS/Secrets
Manager/Cognito (floci locally, real AWS in prod — identical code either way) · pytest +
Hypothesis · Alembic migrations.

**Frontend** (`ui/`): React 18 + TypeScript + Vite · TanStack Query (data fetching/cache,
no Apollo) · a hand-rolled GraphQL client and Cognito auth client (no SDKs) · plain CSS
against a small design-token system — no component framework. Builds to static files,
deployable to S3/CloudFront; no Node server in production.

## Project layout
```
src/
  api/               # FastAPI app: GraphQL (reseller + operator schemas), HTTP webhooks/health
  worker/            # SQS consumers, outbox relay, reconciliation scheduler
  composition.py     # the one place the object graph is wired (memory | postgres profile)
  modules/           # sales/ (ordering, quoting, shipment, invoicing),
                     # reference/ (connections, tenancy),
                     # integration/ (ERP adapters + status mapping, webhooks_inbound,
                     # webhooks_outbound)
                     # each has domain/ (pure), application/ (ports+services),
                     # infrastructure/ (memory + postgres adapters), tests/ (co-located)
  shared/            # eventsourcing kernel, messaging, persistence, secrets, config, types
ui/                  # React SPA (reseller + operator web app) — see "Tech stack" and
                     # "Run locally" below; no separate ui/README.md
migrations/          # Alembic
tests/e2e/           # full in-memory flow (place order -> deliver -> webhook -> projection)
tests/integration/   # against real Postgres + floci (self-skip if unreachable)
scripts/             # messaging_bootstrap.py (SNS/SQS topology), seed_demo.py,
                     # dev_webhook_receiver.py (dev-only test aid, NOT part of the app)
docs/                # local-setup.md, database-schema.md, event-sourcing-explained.md,
                     # erp-integration-patterns.md, adding-an-erp.md, odoo-webhook-setup.md,
                     # mapping/ (canonical<->ERP field tables), erps/ (per-ERP knowledge base)
                     # (architecture itself: aidlc-docs/.../target-architecture.md — one doc)
```

## Run locally
Full walkthrough (backing services, migrations, messaging topology, running the app and
worker as real processes, optional real-Cognito setup): **`docs/local-setup.md`**.

Quick version — backend:
```bash
docker compose up -d            # postgres, floci (AWS emulator), odoo
export DATABASE_URL=postgresql+psycopg2://portal:portal@localhost:5432/portal
alembic upgrade head
export AWS_ENDPOINT_URL=http://localhost:4566 AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
python -m scripts.messaging_bootstrap
python -m scripts.seed_demo
APP_PROFILE=postgres ERP_ADAPTER_MODE=stub python -m src.worker.main &
APP_PROFILE=postgres ERP_ADAPTER_MODE=stub uvicorn src.api.app:app --port 8000 &
```
GraphQL: `http://127.0.0.1:8000/graphql/reseller` (mutations: `placeOrder`,
`cancelOrder`; queries: `orders`, `order`). Health: `GET /livez`.

Quick version — frontend:
```bash
cd ui
npm install
cp .env.example .env       # points at the local API + floci Cognito by default
npm run dev                 # http://localhost:5173
```
Sign in with a seeded demo user (see `docs/local-setup.md` §7 to provision one) — a
reseller-role user lands on the order screens, an operator-role user lands on the admin
screens. `npm run build` produces the static `dist/` folder that gets deployed as-is.

Optional — watch outbound webhook deliveries land during dev:
```bash
python -m scripts.dev_webhook_receiver --port 8090 --secret <the endpoint's signing secret>
```
A standalone, dependency-free test aid (see the file's own docstring) — not something the
app itself starts or depends on.

## Adding a new ERP
`docs/adding-an-erp.md` — four touch points (a status mapper, an adapter, one registry
line, one enum member), no changes anywhere else. `docs/erps/` is the knowledge base for
each ERP once it's registered (auth quirks, API shape, gotchas found the hard way).
`docs/odoo-webhook-setup.md` covers the optional inbound-webhook side specifically.

## Run tests
Backend:
```bash
pip install -e ".[dev]"
pytest src tests
```
Everything under `src/*/tests/` and `tests/e2e/` is DB-free (pure logic + in-memory
adapters). `tests/integration/*` needs a real Postgres (and some, floci) — they self-skip
with a clear reason if unreachable rather than failing.

Frontend:
```bash
cd ui
npm run build      # tsc --noEmit && vite build — typecheck + production build in one step
```
