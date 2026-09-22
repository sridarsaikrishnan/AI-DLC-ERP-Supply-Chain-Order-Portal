# Infrastructure Design — U3 Integration

## Summary
No new infrastructure for MVP. U3 runs inside the same app image (worker handlers registered into U0's queue) and uses the shared PostgreSQL. Stub adapters mean no external ERP connectivity is required for the PoC.

## Service Mapping
| Concern | Mapping | Notes |
|---|---|---|
| Runtime | Same app image; handlers run in the worker loop | U3 is first extraction candidate -> could later run as a dedicated worker service |
| Data | Shared PostgreSQL (orders, jobs, config) | No new tables |
| ERP connectivity | None in MVP (stub adapters) | Real adapters (httpx) + outbound network later |
| Config | ERP instances / routing rules / mappings from U0 config tables (authored by U4) | Seed config used until U4 lands |

## Future extraction note
U3 depends only on U0. To extract: run its handlers as a separate worker process consuming the same job table (or a dedicated queue), sharing the U0 foundation library.

## Extension Compliance
- Security/Resiliency: DISABLED — N/A (inline creds per Q7=A flagged; no auto-failover per Q4=A).
