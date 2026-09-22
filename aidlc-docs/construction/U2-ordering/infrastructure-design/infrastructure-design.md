# Infrastructure Design — U2 Ordering & Lifecycle

No new infrastructure. U2 adds client-facing routers to the same app image, reuses shared PostgreSQL (orders/status tables from U0) and the U0 queue. Catalog/inventory seed data loaded via a small seed (config/migration or in-code seed) for the PoC. See `U0-foundation/infrastructure-design/`.

## Extension Compliance
- Security/Resiliency: DISABLED — N/A.
