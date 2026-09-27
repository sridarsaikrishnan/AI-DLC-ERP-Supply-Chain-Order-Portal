# Construction — U3 Real Odoo Integration (Increment 2)

Implements `aidlc-docs/inception/requirements/odoo-integration-requirements.md`.

## What was built
- **Real Odoo adapter** (`src/modules/integration/adapters/`):
  - `odoo_client.py` — stdlib (urllib) JSON-RPC client. Explicit per-call timeout.
    Errors classified as `OdooTransientError` (network/timeout/HTTP 5xx → retryable) vs
    `OdooTerminalError` (app error / HTTP 4xx / auth → permanent).
  - `odoo_mapping.py` — pure functions: `map_odoo_state_to_native` (total; safe default)
    and `build_odoo_order_payload` (line-count-preserving, non-negative qty, no null refs).
  - `odoo.py` — `OdooAdapter` implementing the `ErpAdapter` protocol: `submit` (create
    `sale.order`, resolve/create `res.partner` + `product.product`), `fetch_status`
    (state + invoice/delivery → native token), `send_corrective_action`
    (cancel/amend/resubmit), `check_connectivity`.
- **Connection model (architecture change, FR-I2-8)**: `ErpInstance` + `ErpInstanceRow`
  gained `base_url/database/username/secret`; adapters now receive an `ErpConnection`
  (built via `ErpConnection.from_instance`) instead of a bare string. Admin API + service
  accept the new fields. Migration: `migrations/003_odoo_connection.sql`; SQLite path in
  `src/app/seed.py` (adds columns + seeds instance/rule).
- **Adapter selection** (`bootstrap.py`): real adapter by default; `ERP_ODOO_MODE=stub`
  falls back to `OdooStubAdapter` for tests/CI.
- **Local Odoo** added to the root `docker-compose.yml` (`odoo` + `odoo-db`); a match-all
  routing rule + ODOO instance seeded so orders flow portal → queue → Odoo out of the box.

## Where the local setup lives
- Odoo services: root `docker-compose.yml` (`odoo` at http://localhost:8069, admin/admin).
- Seeded connection + routing: `migrations/003_odoo_connection.sql` (Postgres) and
  `src/app/seed.py` (SQLite).
- Run instructions & config table: root `README.md` → "ERP integration: local Odoo".

## Status mapping (FR-I2-5)
`draft`/`sent` → Accepted · `sale`/`done` → Processing · fully delivered → Shipped ·
fully invoiced → Invoiced · `cancel` → Cancelled · unknown → Processing (safe default).

## Tests
- `tests/integration/test_odoo_mapping_pbt.py` — Hypothesis PBT for the pure mapping
  functions (status totality, payload invariants, client-ref round-trip) + example-based
  known-state assertions.
- Note: not executed under pytest in the authoring environment (no package deps / no
  network to install them); mapping logic verified directly and all modules byte-compile.

## Extensions
- Security: OFF (PoC) — inline secret flagged for pre-production hardening.
- Resiliency: ON, scoped — timeouts + retryable/terminal classification + graceful
  degradation (RESILIENCY-10); logging/health reused (RESILIENCY-05/06). Infra/DR rules N/A.
- PBT: partial — enforced on pure mapping functions.
