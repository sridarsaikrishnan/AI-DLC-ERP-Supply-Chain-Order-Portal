# NFR Requirements — U4 Admin & Configuration

Inherits U0 platform baseline. U4-specific:
- **NFR-U4-SEC-1**: All admin endpoints require ADMIN role (U1). (Full security baseline still OFF per Q7=A.)
- **NFR-U4-SEC-2 (accepted risk, Q7=A)**: ERP connection_ref may hold inline credentials; flagged for hardening.
- **NFR-U4-EXT-1**: Admin config is the mechanism that makes "add a new ERP in days" real — register instance + routing + mapping without code changes (supports NFR-2).

## Tech Stack
Inherits U0. FastAPI admin router, U0 config repositories/models, U1 ADMIN guard, U3 adapter registry for connectivity checks. No new libraries.
