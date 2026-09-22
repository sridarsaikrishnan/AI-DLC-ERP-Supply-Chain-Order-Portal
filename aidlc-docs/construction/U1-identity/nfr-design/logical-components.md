# Logical Components — U1 Identity & Access

Placed in `src/modules/identity/`.

## LC-U1-1: AuthService
- Implements login, verify MFA, issue token, resolve context, authorize (business-logic-model Processes 1–5).

## LC-U1-2: TokenService
- Encode/decode + verify signed tokens (PyJWT). Pure-ish encode/decode -> round-trip test candidate.

## LC-U1-3: TotpService
- Generate/verify TOTP (pyotp).

## LC-U1-4: Identity Repositories
- UserRepository, CredentialRepository, MfaEnrollmentRepository (backed by U0 persistence). These are platform/identity data (keyed by userId + tenantId), using U0 session.

## LC-U1-5: Auth Middleware / Dependencies
- `ContextMiddleware` (or FastAPI dependency): reads bearer token, resolves SecurityContext (P-U1-4), sets it for the request.
- `require_role(role)`: authorization guard (P-U1-5).

## LC-U1-6: Auth Router
- `POST /auth/login`, `POST /auth/mfa/verify`. (Provisioning is admin/seed, not a public endpoint in MVP.)

## Module Placement
```
src/modules/identity/
├── models.py         # ORM tables: users, credentials, mfa_enrollments
├── token_service.py  # LC-U1-2
├── totp_service.py   # LC-U1-3
├── repositories.py   # LC-U1-4
├── service.py        # LC-U1-1 AuthService
├── deps.py           # LC-U1-5 middleware/guards
└── router.py         # LC-U1-6 endpoints
```
