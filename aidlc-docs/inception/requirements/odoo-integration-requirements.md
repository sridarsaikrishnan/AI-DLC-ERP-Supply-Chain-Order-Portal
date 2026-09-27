# Requirements — Real Odoo Integration (Increment 2)

## Intent Analysis
- **User request**: Replace the Odoo mock adapter with a real Odoo integration, stand up a local Odoo development environment, and connect it to the running portal. Fix the existing architecture where required.
- **Request type**: Enhancement + Integration (brownfield). Turns a stubbed extension seam into a working external-system connector.
- **Scope estimate**: Multiple components — `src/modules/integration/` (new real adapter, bootstrap selection), `src/modules/foundation/config` + `persistence` + `migrations` (connection model change), root `docker-compose.yml` (local Odoo), and portal seed data.
- **Complexity estimate**: Moderate. Well-bounded by the existing `ErpAdapter` protocol; the only structural change is how connection credentials are modeled and reach the adapter.
- **Basis**: Reviewed the docker POC (`docker/odoo-quickstart/` — Odoo 17 + JSON-RPC event consumer) and the `main` branch (carries only the Odoo quickstart + AWS-native design trail; no `src/`). The proven POC pattern is stock-Odoo JSON-RPC with connection details supplied as configuration.

## Decisions (from `odoo-integration-questions.md`)
| # | Decision | Answer |
|---|---|---|
| Q1 | Protocol | **A** — JSON-RPC via Odoo external API (`/jsonrpc`), stock Odoo, no add-on |
| Q2 | Connection model (architecture fix) | **A** — extend `ErpInstance` + `erp_instances` table with structured connection fields + migration |
| Q3 | Mapping depth | **A** — full: resolve/create partner, resolve/create products, real `sale.order` with lines |
| Q4 | Missing partner/product | **A** — auto-create on submit |
| Q5 | Status reconciliation | **A** — adapter translates Odoo state → existing native tokens; handler map unchanged |
| Q6 | Real vs stub selection | **A** — real adapter default; stub kept for tests; selectable via config/env flag |
| Q7 | Local Odoo wiring | **A** — add `odoo` (+Postgres) to root `docker-compose.yml`; seed a matching ERP instance |
| Q8 | Corrective actions | **A** — Cancel + Amend (draft/sent) + Resubmit |
| Q9 | Security extension | **B** — off (local dev/PoC) |
| Q10 | Resiliency extension | **A** — on (scoped to code-level reliability of the external call; see NFRs) |
| Q11 | Property-based testing | **B** — partial (pure functions & round-trips) |

## Functional Requirements

- **FR-I2-1 — Real Odoo adapter.** Provide `OdooAdapter` implementing the existing `ErpAdapter` protocol (`submit`, `fetch_status`, `send_corrective_action`, `check_connectivity`) using Odoo's JSON-RPC external API (`common.authenticate` + `object.execute_kw`).
- **FR-I2-2 — Submit creates a real sales order.** `submit(erp_payload, connection)` creates a `sale.order` in Odoo with order lines, resolving the customer to a `res.partner` and each line's product to a `product.product` (by code/ref). Returns the Odoo order reference (`name`, e.g. `S00021`) as `erp_reference`.
- **FR-I2-3 — Auto-provision referenced entities.** If a referenced partner or product does not exist, create it on submit (partner by name/email; product by code/name with list price). (Q4=A)
- **FR-I2-4 — Status sync.** `fetch_status(erp_reference, connection)` reads the Odoo order's `state` (and, where available, delivery/invoice status) and maps it to a native status token consumed by the existing handler.
- **FR-I2-5 — Status mapping.** Map Odoo → native tokens so the handler's `_NATIVE_TO_CANONICAL` map is unchanged (Q5=A):
  - `draft`, `sent` → `Accepted`
  - `sale` → `Processing`
  - delivery done / `done` → `Shipped`
  - fully invoiced → `Invoiced`
  - `cancel` → `Cancelled`
- **FR-I2-6 — Corrective actions.** `send_corrective_action` supports (Q8=A):
  - `CANCEL` → call `action_cancel`; terminal error if the order is already delivered/invoiced.
  - `AMEND` → update order lines while the order is `draft`/`sent`; terminal error otherwise.
  - `RESUBMIT` → create a new order (delegates to submit).
- **FR-I2-7 — Connectivity check.** `check_connectivity(connection)` authenticates against Odoo and returns success/failure (used by the Admin connections health view).
- **FR-I2-8 — Connection configuration (architecture).** Extend the ERP-instance connection model to carry `base_url`, `database`, `username`, and `secret` (Q2=A):
  - Update `ErpInstance` (pydantic) and `ErpInstanceRow` (ORM) with the new fields.
  - Add a schema migration for `erp_instances`.
  - Keep `connection_ref` for display/back-compat; the adapter receives the structured connection.
- **FR-I2-9 — Adapter selection.** Register the real `OdooAdapter` as the default for `ErpType.ODOO`; fall back to `OdooStubAdapter` when a config/env flag selects stub mode (e.g., `ERP_ODOO_MODE=stub`) so CI without Odoo still runs (Q6=A). ERPNext remains a stub this increment.
- **FR-I2-10 — Local Odoo dev environment.** Add an `odoo` service and its Postgres to the root `docker-compose.yml`, auto-initialized with the Sales/Contacts apps; a single `docker compose up` brings up portal + Odoo (Q7=A).
- **FR-I2-11 — Seeded connection.** Seed an `ODOO` ERP instance in the portal pointing at the local Odoo (`base_url`, `database`, `admin` user), plus a routing rule so submitted orders route to it, enabling an end-to-end demo out of the box.

## Non-Functional Requirements

- **NFR-I2-1 (Resiliency / RESILIENCY-10).** All Odoo calls MUST use explicit connect/read **timeouts** (no unbounded waits). Transient failures (network errors, 5xx, timeouts) MUST surface as retryable (`AdapterResult.terminal = False`) so the existing bounded-retry queue backs off and retries; business rejections (invalid state, not found) MUST be `terminal = True`. Adapter MUST degrade gracefully (a marked-unavailable/unreachable instance fails routing cleanly rather than hanging).
- **NFR-I2-2 (Observability / RESILIENCY-05/06).** Reuse existing structured logging + correlation IDs for each Odoo call (model, method, order id, outcome). The existing `/livez`, `/readyz`, `/metrics` endpoints remain; `check_connectivity` provides a deep-dependency signal for the Admin connections view.
- **NFR-I2-3 (Idempotency).** Submission remains idempotent via U0's dedupe key; the adapter MUST NOT create duplicate orders on retry of an already-succeeded submission (guarded by the queue's dedupe + not re-submitting when an `erp_reference` already exists).
- **NFR-I2-4 (Config/secret handling).** Consistent with Q9=B (security OFF, PoC): the Odoo secret is stored inline in `erp_instances` and supplied via seed/compose env for local dev. Flagged as a pre-production hardening item (move to a secret store, encrypt at rest) — **not** implemented this increment.
- **NFR-I2-5 (Testability / PBT partial).** Pure mapping functions MUST have property-based tests: canonical→Odoo payload mapping and Odoo-state→native-token mapping (total function over all Odoo states; round-trip where applicable). Use **Hypothesis** (already in the stack).

## Extension Compliance Summary

**Security Baseline** — Disabled (Q9=B). Inline credential storage and plaintext secret accepted for local dev; recorded as a pre-production hardening item.

**Resiliency Baseline** — Enabled (Q10=A), scoped to this local-dev increment:
| Rule | Status | Note |
|---|---|---|
| RESILIENCY-05 Monitoring/Logging | Compliant | Reuse structured logging + correlation + `/metrics` |
| RESILIENCY-06 Health checks | Compliant | `/livez`,`/readyz`; `check_connectivity` deep check |
| RESILIENCY-10 Dependency isolation | Compliant (target) | Timeouts + retryable/terminal classification + graceful degradation (NFR-I2-1) |
| RESILIENCY-01 Criticality | Compliant | Odoo connector = High; portal core = Critical (documented here) |
| RESILIENCY-02 RTO/RPO & DR | **N/A** | No production deployment/DR in this increment's scope |
| RESILIENCY-03 Change mgmt | **N/A** | Local dev increment |
| RESILIENCY-04 CI/CD & rollback | **N/A** | No deployment pipeline change in scope |
| RESILIENCY-07 Resiliency monitoring | **N/A** | No cloud infra in scope |
| RESILIENCY-08 Multi-zone/region | **N/A** | Single local instance |
| RESILIENCY-09 Auto-scaling | **N/A** | Local dev |
| RESILIENCY-11/12/13 DR/backup/failover | **N/A** | No persistent production data / DR in scope |
| RESILIENCY-14 Chaos/DR testing | **N/A** | Deferred to Operations if productionized |
| RESILIENCY-15 Incident response | **N/A** | Local dev |

> The N/A determinations above are scoping calls for a local-dev integration increment. If this is intended to move toward production, the deferred resiliency decision points (RTO/RPO & DR strategy, change management, CI/CD & rollback, deployment style, regional topology, incident response, resiliency testing) must be answered. Raise this at the requirements gate to switch them on.

**Property-Based Testing** — Partial (Q11=B). Enforced rules: PBT-02 (round-trip), PBT-03 (invariant), PBT-07 (generators), PBT-08 (shrinking/repro), PBT-09 (framework = Hypothesis). Targets: payload mapping and status-token mapping. Other PBT rules advisory/N/A for this thin integration layer.

## Testable Properties (for PBT-01/Code Gen)
- **P1 (invariant/total):** Odoo-state→native-token mapping returns a valid native token for every known Odoo state and a safe default (no exception) for unknown states.
- **P2 (invariant):** canonical→Odoo payload mapping preserves line count and non-negative quantities/prices; never emits `None` product refs.
- **P3 (round-trip, partial):** for the subset of fields with a defined inverse mapping, `from_erp(to_erp(x))` preserves those fields.

## Key Requirements Summary
Add a real, stock-Odoo JSON-RPC adapter behind the existing `ErpAdapter` seam; make it the default with a stub fallback flag; extend the ERP-instance connection model (structured fields + migration) as the one deliberate architecture fix; run a local Odoo via the root compose and seed a connection + route so orders flow portal → queue → Odoo and statuses sync back — all with timeouts and retryable/terminal error classification, and property-based tests on the pure mapping functions.
