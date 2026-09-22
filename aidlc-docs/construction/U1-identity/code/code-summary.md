# U1 Identity & Access — Code Summary

## Generated Files (`src/modules/identity/`)
- `models.py` — UserRow, CredentialRow, MfaEnrollmentRow (passwords as-is per Q7=A)
- `token_service.py` — PyJWT issue/verify stateless token (P-U1-1)
- `totp_service.py` — pyotp verify + provision (P-U1-2)
- `repositories.py` — UserRepository, CredentialRepository, MfaRepository (U0 session)
- `service.py` — AuthService: login (throttle + as-is password + MFA branch), verify_mfa, resolve_context, authorize (BR-U1-1..6)
- `deps.py` — current_context (bearer -> SecurityContext, binds for U0 scoping), require_role guard
- `router.py` — POST /auth/login, POST /auth/mfa/verify

## Other changes
- `migrations/002_identity.sql` — identity tables + PoC seed (tenant-demo; admin/admin123; client/client123)
- `src/app/main.py` — includes identity router
- `requirements.txt` — added PyJWT, pyotp
- `tests/identity/test_token_and_authz.py` — token round-trip, TOTP, authorization matrix, context resolution

## Story Traceability
- US-1.1 login -> AuthService.login + router + soft throttle ✅ implemented
- US-1.2 MFA -> TotpService + verify_mfa ✅ implemented
- US-1.3 tenant-scoped access -> resolve_context builds U0 SecurityContext; require_role guard ✅ implemented

## Verification Status (honest)
- Authored against U1 design. **Tests NOT executed here** (no working Python/Docker in this environment).
- DB-free tests (token round-trip, TOTP, authorize matrix, context resolution) ready under `pytest`.
- Login/repository DB paths and seed verification deferred to Build & Test.

## Accepted Risks (Q7=A)
- Plaintext passwords in `credentials`; seed passwords in migration. Signing secret defaults to an insecure dev value unless `AUTH_SIGNING_SECRET` is set. All flagged blocking-before-production.
