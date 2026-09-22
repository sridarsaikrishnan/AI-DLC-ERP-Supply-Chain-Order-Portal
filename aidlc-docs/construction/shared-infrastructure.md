# Shared Infrastructure — ERP & Supply Chain Order Portal

Defined by U0 (Platform Foundation) and used by ALL units (U1–U4). Later per-unit Infrastructure Design should reference this rather than redefining shared pieces.

## Shared Services (PoC, docker-compose)
- **Reverse Proxy (Nginx)** — single HTTP entry point to the app replicas.
- **App Replicas (x2)** — identical FastAPI containers, each running API + in-process workers. All modules (identity, ordering, integration, admin, foundation) are packaged in the same image (modular monolith).
- **PostgreSQL (1 container, persistent volume)** — shared datastore for:
  - Tenant-owned data (orders, status history) — row-level tenant isolation
  - Platform config (ERP instances, routing rules, mapping definitions)
  - Job queue table + idempotency table
- **Logging** — JSON to stdout, platform-collected.
- **Metrics/Health** — `/metrics`, `/livez`, `/readyz` per replica.

## Shared Cross-Cutting Concerns (from U0)
- Security context propagation (from Identity, U1) available to all modules.
- Correlation-id middleware and structured logging.
- Tenant-scoped repository base enforcing fail-closed isolation.
- DB-backed queue + worker host with at-least-once/bounded-retry/idempotency.

## Accepted Risks (carried from NFR Requirements Q7=A)
- Plaintext passwords, inline ERP credentials, no explicit parameterized-query mandate. All flagged blocking-before-production; to be resolved in the deferred security-hardening phase.

## Future (deferred, designed-for)
- Managed container platform + managed Postgres + managed load balancer.
- Dedicated worker service (extract U3 Integration first).
- Real message broker if volume exceeds the moderate target.
- Secrets manager for ERP credentials.
