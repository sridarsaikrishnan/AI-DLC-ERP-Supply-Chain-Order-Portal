# Deployment Architecture — U1 Identity & Access

No change to the U0 topology (Nginx -> 2 app replicas -> shared PostgreSQL). U1 adds:
- Auth endpoints (`/auth/login`, `/auth/mfa/verify`) served by the same replicas.
- Identity tables in the shared database.
- Auth middleware that runs on every protected request to resolve the SecurityContext.

See `U0-foundation/infrastructure-design/deployment-architecture.md` for the topology diagram; U1 does not alter it.
