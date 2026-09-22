# NFR Requirements — U1 Identity & Access

U1 inherits the platform NFR baseline set by U0 (see `U0-foundation/nfr-requirements/`). Only U1-specific items are listed here.

## Inherited from U0 (unchanged)
- Stack: Python / FastAPI / PostgreSQL / SQLAlchemy.
- 2 app instances, moderate volume, best-effort availability.
- Structured logging + correlation id + metrics + health.
- Tenant isolation enforced by U0 repositories (fail-closed).
- Security baseline OFF; PBT partial; resiliency OFF.

## U1-Specific NFRs
- **NFR-U1-SEC-1 (accepted risk, Q7=A)**: Passwords stored as-is (no hashing). Blocking-before-production.
- **NFR-U1-SEC-2**: Auth token is a stateless signed token. The signing secret is read from configuration/env. For MVP this secret handling follows the same relaxed posture (Q7=A) but a real secret should be used even in the PoC to keep tokens unforgeable. (Minimal, not the full baseline.)
- **NFR-U1-SEC-3**: TOTP secret per user stored in DB (as-is for MVP, consistent with Q7=A).
- **NFR-U1-PERF-1**: Login and token verification are best-effort; token verification must be in-process (no DB hit) so protected endpoints stay fast.
- **NFR-U1-REL-1**: Soft-throttle counters persisted with the Credential (survive restarts).

## Tech Stack Decisions
No new stack decisions — inherits U0. Adds two libraries:
- A JWT/signing library for the stateless token (e.g., PyJWT).
- A TOTP library (e.g., pyotp) for MFA.
