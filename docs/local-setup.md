# Local setup

Get the platform running locally with no cloud account. Backing services run in Docker
(Postgres + the **floci** AWS emulator + Odoo); the code runs from your venv.

> Status: Phase 1 delivers the domain core (event-sourcing kernel, tenancy/ownership
> routing, Order aggregate, ERP adapter + delivery, inbound webhook ingress) as a fully
> tested library. The GraphQL API and worker hosts are wired in Phase 2 and will be added
> as `app`/`worker` services in `docker-compose.yml`.

## 1. Prerequisites
- Python 3.11+
- Docker + Docker Compose

## 2. Install the package (editable, with dev tools)
```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

## 3. Start backing services
```bash
docker compose up -d            # postgres, floci (:4566), odoo (:8069), odoo-db
```
First Odoo boot takes a minute or two (module install). Odoo UI: http://localhost:8069 (admin/admin).

## 4. Create the database schema
```bash
export DATABASE_URL=postgresql+psycopg2://portal:portal@localhost:5432/portal
alembic upgrade head
```
This creates the event store, outbox, projections, config/tenancy tables, the three
uniqueness constraints, and the row-level-security policies.

## 5. Provision the messaging topology (on floci)
```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
python -m scripts.messaging_bootstrap
```
Creates the SNS FIFO topic, the SQS FIFO queues + DLQs, and the subscriptions/filter policies.

## 6. Run the checks
```bash
pytest              # unit + integration tests (co-located per module + tests/e2e)
mypy src            # strict typing
ruff check src      # lint
lint-imports        # architecture boundaries (domain must not import infra/cloud SDKs)
```

## 7. Connect Odoo inbound webhooks (to collect status back)
Odoo Community has no native "webhook" action, so this uses a dedicated
shared-secret-in-path endpoint instead of the HMAC-signed one ERPNext gets — full setup
(secret provisioning, the Automation Rule's Python code, payload shape, verification) is
in **`docs/odoo-webhook-setup.md`**. Until a connection's webhook is configured, the
reconciliation sweeper polls status as the fallback — every connection gets that either
way, the webhook only lowers latency.

## Where things live
See `aidlc-docs/construction/target-arch-project-structure.md` for the "where do I find X"
map (inbound webhooks, public GraphQL, the shared library, migrations, tests, etc.).
