# Infrastructure Design — U1 Identity & Access

## Summary
U1 introduces **no new infrastructure**. It ships inside the same app image and uses the shared infrastructure defined by U0 (`aidlc-docs/construction/shared-infrastructure.md`).

## Service Mapping
| Concern | Mapping | Notes |
|---|---|---|
| Runtime | Same FastAPI app image (2 replicas) | Auth router + middleware live in-process |
| Data | Shared PostgreSQL | New tables: `users`, `credentials`, `mfa_enrollments` |
| Token verification | In-process (no external service) | Signing secret via `AUTH_SIGNING_SECRET` env |
| Entry | Same Nginx proxy | `/auth/*` routed like any other path |

## New Environment Variables
- `AUTH_SIGNING_SECRET` — token signing secret (set even for PoC so tokens are unforgeable)
- `TOKEN_TTL_MINUTES` — token lifetime (default 60)
- `LOGIN_MAX_FAILED_ATTEMPTS` (default 5), `LOGIN_THROTTLE_SECONDS` (default 300)

## Migration Addition
A new migration (`002_identity.sql`) adds the identity tables to the shared Postgres.

## Extension Compliance
- Security/Resiliency: DISABLED — N/A. Relaxed secret handling per Q7=A flagged (still recommend a real signing secret).
