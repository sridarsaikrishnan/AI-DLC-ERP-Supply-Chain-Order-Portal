# ERP & Supply Chain Order Portal

An extensible portal that lets external clients place and manage orders routed to multiple ERP systems (MVP: ERP Next and Odoo) via a configuration-driven canonical mapping layer. Built as a modular monolith designed for later extraction into microservices.

See `aidlc-docs/` for the full AI-DLC design trail (requirements, stories, architecture, per-unit design).

## Current status
- **U0 Platform Foundation**: implemented (canonical model, validation, config model + routing resolver, security context, tenant-scoped persistence, DB-backed async queue with poller/workers, migrations, tests).
- U1 Identity, U2 Ordering & Lifecycle, U3 Integration, U4 Admin & Config: not yet built.

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

## Run locally (containers, PostgreSQL)
Requires Docker.
```
docker compose up --build
```
This starts PostgreSQL, two app replicas (each API + worker), and an Nginx proxy on http://localhost:8080.
Health: `GET /livez`, `GET /readyz`. Metrics: `GET /metrics`.

## Run tests
Requires a local Python 3.11+ with dependencies installed:
```
pip install -r requirements.txt
pytest
```
Note: `test_validator.py`, `test_routing.py`, and `test_property_based.py` are DB-free (pure logic). Repository/queue integration tests that need PostgreSQL run in the Build & Test phase.

## Security note (PoC)
This MVP intentionally skips several safeguards (plaintext passwords, inline ERP credentials, no explicit parameterized-query mandate) per an explicit proof-of-concept decision. These are flagged as blocking items to resolve before any production use.
