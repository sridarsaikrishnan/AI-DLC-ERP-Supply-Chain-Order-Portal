# NFR Requirements — U2 Ordering & Lifecycle

Inherits U0 platform baseline. U2-specific:
- **NFR-U2-PERF-1**: Order submission stays responsive by persisting + enqueuing only (fulfillment async via U3).
- **NFR-U2-SEC-1**: All order data access is tenant-scoped via U0 (fail-closed); tenantId sourced from the U1 token, never the request body.
- **NFR-U2-USE-1**: Validation errors return field-level detail (US-2.1 acceptance).

## Tech Stack
Inherits U0 (FastAPI routers, U0 repositories, U0 queue). No new libraries.
