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

## Tech stack
Python 3.11 · FastAPI + Strawberry GraphQL · SQLAlchemy + PostgreSQL (event store +
outbox + projections + config, one database) · boto3 against SNS/SQS/Secrets Manager
(floci locally, real AWS in prod — identical code either way) · pytest + Hypothesis ·
Alembic migrations.

## Project layout
```
src/
  api/            # FastAPI app: GraphQL (reseller + operator schemas), HTTP webhooks/health
  worker/         # SQS consumers, outbox relay, reconciliation scheduler
  composition.py  # the one place the object graph is wired (memory | postgres profile)
  modules/        # bounded contexts: catalog, connections, tenancy, ordering,
                  # integration (ERP adapters + status mapping), webhooks_inbound
                  # each has domain/ (pure), application/ (ports+services),
                  # infrastructure/ (memory + postgres adapters), tests/ (co-located)
  shared/         # eventsourcing kernel, messaging, persistence, secrets, config, types
migrations/       # Alembic
tests/e2e/        # full in-memory flow (place order -> deliver -> webhook -> projection)
tests/integration/# against real Postgres + floci (self-skip if unreachable)
scripts/          # messaging_bootstrap.py (SNS/SQS topology), seed_demo.py
docs/             # local-setup.md, database-schema.md, event-sourcing-explained.md,
                  # erp-integration-patterns.md, adding-an-erp.md, odoo-webhook-setup.md
                  # (architecture itself: aidlc-docs/.../target-architecture.md — one doc)
```

## Run locally
Full walkthrough (backing services, migrations, messaging topology, running the app and
worker as real processes): **`docs/local-setup.md`**.

Quick version:
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

## Adding a new ERP
`docs/adding-an-erp.md` — four touch points (a status mapper, an adapter, one registry
line, one enum member), no changes anywhere else. `docs/odoo-webhook-setup.md` covers the
optional inbound-webhook side specifically.

## Run tests
```bash
pip install -e ".[dev]"
pytest src tests
```
Everything under `src/*/tests/` and `tests/e2e/` is DB-free (pure logic + in-memory
adapters). `tests/integration/*` needs a real Postgres (and some, floci) — they self-skip
with a clear reason if unreachable rather than failing.
