# NFR Requirements — U3 Integration

Inherits the U0 platform baseline. U3-specific items:

## Inherited from U0
Stack (Python/FastAPI/PostgreSQL/SQLAlchemy), 2 instances, DB-backed queue with at-least-once + retry + idempotency, tenant isolation, logging/correlation/metrics/health, Security/Resiliency OFF, PBT partial.

## U3-Specific NFRs
- **NFR-U3-EXT-1 (primary)**: Adapters are pluggable behind the `ErpAdapter` interface + config-driven mapping, so adding a new ERP = new adapter class + config (days, not months) (NFR-2). No core routing/mapping change required.
- **NFR-U3-EXT-2**: U3 is the first microservice extraction candidate; its logic depends only on U0 and must avoid coupling to U2/U4 internals.
- **NFR-U3-REL-1**: Adapter failures distinguished as transient (retry via U0) vs terminal (fail fast). Idempotency prevents duplicate ERP submissions on retry.
- **NFR-U3-PERF-1**: Best-effort; ERP calls happen in workers, off the request path.
- **NFR-U3-SEC-1 (accepted risk, Q7=A)**: ERP connection details/credentials may be read inline from config; flagged for hardening (secrets manager later).

## Tech Stack
Inherits U0. Adds `httpx` (already present) for future real-HTTP adapters; MVP stub adapters need no new libraries.
