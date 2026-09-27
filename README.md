# ERP & Supply Chain Order Portal

An extensible portal that lets external clients place and manage orders routed to multiple ERP systems (MVP: ERP Next and Odoo) via a configuration-driven canonical mapping layer. Built as a modular monolith designed for later extraction into microservices.

See `aidlc-docs/` for the full AI-DLC design trail (requirements, stories, architecture, per-unit design).

## Current status
- **U0 Platform Foundation**: implemented (canonical model, validation, config model + routing resolver, security context, tenant-scoped persistence, DB-backed async queue with poller/workers, migrations, tests).
- **U3 Integration — real Odoo adapter**: implemented. Orders submit to a live Odoo over JSON-RPC (create `sale.order`, resolve/create partner + products), status syncs back, and cancel/amend/resubmit are supported. See **ERP integration: local Odoo** below. ERP Next remains a stub.
- Remaining feature units are tracked in `aidlc-docs/`.

## Tech stack
Python 3.11 · FastAPI · SQLAlchemy · PostgreSQL · pytest + Hypothesis. Async work runs on a DB-backed job table with `SELECT ... FOR UPDATE SKIP LOCKED`.

## Project layout
```
src/
  app/                     # FastAPI composition root, health + metrics
  shared/                  # logging, correlation, errors, metrics
  modules/foundation/      # U0: canonical, config, context, persistence, queue
tests/foundation/          # unit + property-based tests
migrations/                # PostgreSQL schema (auto-applied by the postgres container)
Dockerfile, docker-compose.yml, nginx.conf
```

## Web UI
A browser UI is served by the same app (no separate frontend server):
- Open **http://127.0.0.1:8000/** in a modern browser (Chrome/Edge — not Internet Explorer).
- Sign in with a seeded account: `client/client123` (place/track/correct orders) or `admin/admin123` (also gets the Admin screens).
- Covers everything through the browser: login (+MFA when enrolled), place/amend orders, browse catalog & inventory, view order detail + status history, corrective actions (cancel/resubmit/amend), and admin config (register ERP instances, routing rules, mappings, view config).
- Static assets live in `web/` and are mounted at `/static`; the API docs remain at `/docs`.

## Run locally (no Docker, quickest)
Requires Python 3.11+. Uses SQLite by default (no database to install); tables are created and demo users seeded automatically on startup.
```
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on *nix)
pip install -r requirements.txt
uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```
Then open http://127.0.0.1:8000/ for the UI, or http://127.0.0.1:8000/docs for the API.

## Run locally (containers, PostgreSQL + Odoo)
Requires Docker. This is the recommended way to see orders flow end-to-end into a real ERP.
```
docker compose up --build
```
This starts, from the root `docker-compose.yml`:
- **postgres** — the portal database (migrations in `migrations/` auto-applied on first init)
- **odoo** + **odoo-db** — a local Odoo 17 with the Sales app, reachable at http://localhost:8069 (login `admin` / `admin`)
- **app1**, **app2** — two portal replicas (each API + worker)
- **proxy** — Nginx on http://localhost:8080

Health: `GET /livez`, `GET /readyz`. Metrics: `GET /metrics`.

First boot takes a couple of minutes while Odoo installs modules. See **ERP integration: local Odoo** below for the end-to-end flow and configuration.

## ERP integration: local Odoo (real, not a mock)

The portal submits orders to a **real Odoo** over its JSON-RPC external API. There is no
separate mock service — the integration talks to the Odoo instance defined in the root
`docker-compose.yml` (the earlier `docker/odoo-quickstart/` scratch stack was removed).

**Where the local setup lives**
- **Odoo services**: the `odoo` and `odoo-db` services in `docker-compose.yml` (repo root). Odoo UI at http://localhost:8069, login `admin` / `admin`, database `odoo`.
- **The adapter**: `src/modules/integration/adapters/odoo.py` (JSON-RPC client in `odoo_client.py`, pure mapping in `odoo_mapping.py`).
- **Connection details** are stored on the ERP instance (`erp_instances.base_url/database/username/secret`). A local Odoo instance + a match-all routing rule are seeded automatically:
  - PostgreSQL path: `migrations/003_odoo_connection.sql`
  - SQLite path: `src/app/seed.py` (reads `ODOO_BASE_URL`/`ODOO_DB`/`ODOO_USER`/`ODOO_SECRET`)

**End-to-end flow (containers)**
1. `docker compose up --build` and wait for Odoo to finish first-boot module install.
2. Open the portal at http://localhost:8080, sign in as `client` / `client123`, and place an order.
3. The submission is enqueued; a worker routes it (match-all rule → local Odoo) and the Odoo adapter creates a `sale.order` (auto-creating the customer and any missing products).
4. Watch the order's status in the portal update as the worker syncs Odoo's state back (Accepted → Processing → Invoiced). You can also see the order in Odoo's **Sales** app at http://localhost:8069.

**Running the portal on your host against Odoo in Docker**
Bring up just Odoo (`docker compose up odoo odoo-db`), then run the app on SQLite pointing at it:
```
set ODOO_BASE_URL=http://localhost:8069   # PowerShell: $env:ODOO_BASE_URL="http://localhost:8069"
uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```

**Configuration**

| Env var | Default | Purpose |
|---|---|---|
| `ERP_ODOO_MODE` | `real` | `real` uses the live Odoo adapter; `stub` uses the in-memory `OdooStubAdapter` (tests/CI without Odoo) |
| `ERP_ODOO_TIMEOUT_SECONDS` | `10` | Per-call Odoo timeout (no unbounded waits) |
| `ODOO_BASE_URL` | `http://localhost:8069` | Odoo base URL (SQLite seed path) |
| `ODOO_DB` | `odoo` | Odoo database name |
| `ODOO_USER` | `admin` | Odoo login |
| `ODOO_SECRET` | `admin` | Odoo password/API key (stored inline — local dev only) |

Transient Odoo failures (network, timeout, HTTP 5xx) are retried by the portal's bounded-retry
queue; business errors (invalid state, not found) fail the order without retry.

> Security note: the Odoo secret is stored inline in `erp_instances` and passed via env for local
> dev (the security extension is intentionally OFF for this PoC). Move secrets to a secret store and
> encrypt at rest before any production use.

## Run tests
Requires a local Python 3.11+ with dependencies installed:
```
pip install -r requirements.txt
pytest
```
Note: `test_validator.py`, `test_routing.py`, and `test_property_based.py` are DB-free (pure logic). Repository/queue integration tests that need PostgreSQL run in the Build & Test phase.

## Security note (PoC)
This MVP intentionally skips several safeguards (plaintext passwords, inline ERP credentials, no explicit parameterized-query mandate) per an explicit proof-of-concept decision. These are flagged as blocking items to resolve before any production use.
--test