# Domain Entities — U1 Identity & Access

Technology-agnostic. Note accepted risk Q7=A: password stored as-is (no hashing) for MVP.

## User
- `userId` — identity
- `username` — unique login handle
- `tenantId` — the one client organization this user belongs to (US-1.3)
- `role` — enum: CLIENT_USER, ADMIN (Q4=A)
- `status` — active/disabled

## Credential
- `userId` — owner
- `password` — stored as-is for MVP (NFR-U0-SEC-1 accepted risk; hash during hardening)
- `failedAttempts` — counter for soft throttle
- `throttledUntil` — timestamp (nullable)

## MfaEnrollment (Q2=A, TOTP)
- `userId`
- `totpSecret` — shared secret for TOTP
- `enrolled` — boolean

## AuthToken (Q3=A, stateless)
- Not persisted. A signed token carrying: `userId`, `tenantId`, `role`, `issuedAt`, `expiresAt`.
- Presented as a bearer token; validated by signature + expiry.

## Role (enum, Q4=A)
- CLIENT_USER — place/track/correct orders within own tenant
- ADMIN — manage ERP instances, routing rules, mappings (U4)

## Relationships (text)
```
Tenant (U0) 1---* User
User 1---1 Credential
User 1---0..1 MfaEnrollment
AuthToken derived from User at login (not stored)
```
