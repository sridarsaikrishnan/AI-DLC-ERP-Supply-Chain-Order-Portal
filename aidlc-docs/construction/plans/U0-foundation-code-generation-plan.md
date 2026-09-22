# Code Generation Plan — U0 Platform Foundation

## Single Source of Truth
This plan governs U0 code generation. Steps are executed in order; each is checked off as completed.

## Unit Context
- **Unit**: U0 Platform Foundation (shared module; no direct user stories, foundation for U1–U4)
- **Stack**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, pytest + Hypothesis
- **Workspace root**: `c:\Users\bhawna.chaudhari\Project AIDLC`
- **Layout** (greenfield monolith, folder-per-module): app code under `src/`, tests under `tests/`
- **Dependencies**: none (U0 is the base)
- **Accepted risks (Q7=A)**: plaintext passwords, inline ERP credentials, no explicit parameterized-query mandate (SQLAlchemy still parameterizes by default)

## Target Structure (application code at workspace root)
```
src/
├── app/                      # composition root, FastAPI app, health endpoints
├── shared/                   # errors, logging, correlation, metrics
└── modules/
    └── foundation/
        ├── canonical/        # canonical schemas + validator (LC-5)
        ├── config/           # config models + resolver (LC-6)
        ├── context/          # SecurityContext + propagation (LC-3)
        ├── persistence/      # DB, base + tenant-scoped repos, JobStore, IdempotencyStore (LC-1)
        └── queue/            # enqueuer, poller, worker host, handler registry (LC-2)
tests/
└── foundation/               # unit + property-based tests
migrations/                   # DB schema (SQL)
docker-compose.yml
Dockerfile
requirements.txt
README.md
```
Documentation summaries go to `aidlc-docs/construction/U0-foundation/code/` (markdown only).

---

## Generation Steps

- [x] **Step 1 — Project Structure Setup**: created `src/`, `tests/`, `migrations/`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` (app x2 + postgres + nginx), base FastAPI app in `src/app/`, and `README.md`.
- [x] **Step 2 — Shared Cross-Cutting (`src/shared/`)**: structured JSON logger, correlation-id middleware, error types, metrics + health endpoints (`/livez`, `/readyz`, `/metrics`).
- [x] **Step 3 — Canonical Model + Validator (`modules/foundation/canonical/`)**: Pydantic models + `validate()` implementing BR-1 (pure functions).
- [x] **Step 4 — Config Model + Resolver (`modules/foundation/config/`)**: config models + ConfigResolver / `evaluate_routing`.
- [x] **Step 5 — Security Context (`modules/foundation/context/`)**: SecurityContext value object, context var provider, job context binder.
- [x] **Step 6 — Persistence Layer (`modules/foundation/persistence/`)**: SQLAlchemy engine/session, ORM tables, `TenantScopedRepository` base (auto tenant filter + fail-closed, BR-2).
- [x] **Step 7 — Queue & Worker Host (`modules/foundation/queue/`)**: Job model, JobStore (SKIP LOCKED), IdempotencyStore, WorkerHost (retry/backoff, idempotent), HandlerRegistry, Poller.
- [x] **Step 8 — DB Migration Scripts (`migrations/001_foundation.sql`)**: all foundation tables.
- [x] **Step 9 — Unit Tests (`tests/foundation/`)**: pytest for validator + routing.
- [x] **Step 10 — Property-Based Tests**: Hypothesis tests for validation invariant + canonical JSON round-trip.
- [x] **Step 11 — Documentation**: `aidlc-docs/construction/U0-foundation/code/code-summary.md` + `README.md`.

## Story Traceability
U0 has no direct stories; it enables all. Its correctness gates: US-1.3 (tenant isolation), US-2.1 (canonical validation), US-6.2/6.3 (config model), and the async fulfillment of E2–E5.

## Verification Note
Code authored against design. Tests NOT executed here (no working Python runtime / no Docker on this machine — only Windows Store python alias stubs). DB-free pure-logic tests are ready to run via `pytest`; DB-backed tests deferred to Build & Test.
