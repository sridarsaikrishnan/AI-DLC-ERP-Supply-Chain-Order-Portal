# Code Generation Plan — U1 Identity & Access

## Unit Context
- **Unit**: U1 Identity & Access. Stories US-1.1 (login), US-1.2 (MFA), US-1.3 (tenant-scoped access).
- **Depends on**: U0 (persistence session, SecurityContext, errors).
- **Adds libraries**: PyJWT, pyotp.
- **Accepted risk (Q7=A)**: passwords stored as-is; still use a real `AUTH_SIGNING_SECRET`.

## Target Structure
```
src/modules/identity/
├── models.py         # ORM: users, credentials, mfa_enrollments
├── token_service.py  # PyJWT encode/decode/verify
├── totp_service.py   # pyotp verify
├── repositories.py   # User/Credential/MfaEnrollment repos (U0 session)
├── service.py        # AuthService: login, verify_mfa, resolve_context, authorize
├── deps.py           # FastAPI deps: current context, require_role
└── router.py         # POST /auth/login, POST /auth/mfa/verify
migrations/002_identity.sql
tests/identity/        # unit tests + token round-trip
```

## Generation Steps
- [x] **Step 1 — Identity ORM models** (`models.py`): users, credentials, mfa_enrollments tables.
- [x] **Step 2 — Migration** (`migrations/002_identity.sql`): identity tables + seed admin/client users for PoC.
- [x] **Step 3 — TokenService** (`token_service.py`): sign/verify JWT with userId/tenantId/role/exp.
- [x] **Step 4 — TotpService** (`totp_service.py`): verify TOTP code.
- [x] **Step 5 — Repositories** (`repositories.py`): user by username, credential read/update, mfa enrollment read.
- [x] **Step 6 — AuthService** (`service.py`): login (throttle + password compare + MFA branch), verify_mfa, issue_token, resolve_context, authorize (BR-U1-1..6).
- [x] **Step 7 — Deps & Router** (`deps.py`, `router.py`): bearer dependency -> SecurityContext, require_role guard, `/auth/login` + `/auth/mfa/verify`; wired into `src/app/main.py`.
- [x] **Step 8 — requirements.txt update**: added PyJWT, pyotp.
- [x] **Step 9 — Unit tests** (`tests/identity/test_token_and_authz.py`): token round-trip, TOTP verify, authorize matrix, context resolution.
- [x] **Step 10 — Documentation**: `aidlc-docs/construction/U1-identity/code/code-summary.md`.

## Story Traceability
- US-1.1 -> AuthService.login + router + throttle (Steps 6,7)
- US-1.2 -> TotpService + verify_mfa (Steps 4,6)
- US-1.3 -> resolve_context building U0 SecurityContext + require_role (Steps 6,7)

## Verification Note
Same environment limitation as U0 (no runnable Python/Docker here). DB-free tests (token round-trip, TOTP, throttle, authorize) authored to run under pytest; login/repository DB paths covered in Build & Test.
