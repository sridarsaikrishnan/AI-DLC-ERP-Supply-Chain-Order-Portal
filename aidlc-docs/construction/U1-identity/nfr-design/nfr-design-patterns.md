# NFR Design Patterns — U1 Identity & Access

Inherits U0 patterns (P-1..P-6). U1-specific patterns:

## P-U1-1: Stateless Token Auth
- Signed token (PyJWT) carrying userId, tenantId, role, exp. Verified in-process on each protected request; no session store, no DB hit (NFR-U1-PERF-1).
- Signing secret from env (`AUTH_SIGNING_SECRET`).

## P-U1-2: MFA (TOTP)
- pyotp verifies the code against the user's stored secret; time-window tolerance default.

## P-U1-3: Soft Throttle
- Credential row tracks failedAttempts + throttledUntil; checked on login, reset on success (BR-U1-3). Durable across restarts.

## P-U1-4: Context Bridge to U0
- On successful token verification, build a U0 `SecurityContext` and set it for the request scope so U0 tenant-scoped repositories work fail-closed (BR-U1-4).

## P-U1-5: Authorization Guard
- A dependency/guard checks role against the endpoint's requirement (CLIENT_USER / ADMIN) before the handler runs (BR-U1-5).

## Compliance Summary
- Security baseline: DISABLED — N/A (password/secret handling relaxed per Q7=A, flagged).
- Resiliency baseline: DISABLED — N/A.
- PBT (Partial): token encode/decode round-trip is a candidate pure round-trip test; otherwise unit tests. Compliant (scope respected).
