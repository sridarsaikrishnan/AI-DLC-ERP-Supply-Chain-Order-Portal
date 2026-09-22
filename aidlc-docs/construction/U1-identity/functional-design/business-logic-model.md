# Business Logic Model — U1 Identity & Access

## Process 1: Login (US-1.1)
- Input: username, password
- Logic: look up user by username; check throttle (BR-U1-3); compare password (as-is, Q7=A); on mismatch increment failedAttempts and return generic error; on match, if MFA enrolled -> return MFA challenge, else issue token.
- Output: AuthResult(token) OR MfaChallenge OR error.

## Process 2: Verify MFA (US-1.2)
- Input: challenge reference (userId), TOTP code
- Logic: validate code against totpSecret; on success issue token; on failure deny (subject to throttle).
- Output: AuthResult(token) OR error.

## Process 3: Issue Token
- Logic: build a signed token carrying userId, tenantId, role, issuedAt, expiresAt; reset failedAttempts.
- Output: bearer token string.

## Process 4: Resolve Context (used by all protected endpoints)
- Input: bearer token
- Logic: verify signature + expiry; build SecurityContext { userId, tenantId, role }; set it for the request (feeds U0 tenant scoping, BR-U1-4).
- Output: SecurityContext or AuthorizationError.

## Process 5: Authorize (BR-U1-5)
- Input: SecurityContext, required role/action
- Logic: check role satisfies the requirement.
- Output: allow or AuthorizationError.

## Data Flow (text)
```
POST /auth/login -> Process 1 -> (MFA? Process 2) -> Process 3 -> token
Protected request -> Process 4 (resolve context) -> Process 5 (authorize) -> handler (U2/U4)
```

## Notes
- Token signing/verification and TOTP are the security-sensitive pieces; verification is deterministic (candidate for unit tests, not full PBT).
- Password hashing intentionally omitted for MVP (Q7=A) — flagged in U0 NFR requirements as blocking-before-production.
