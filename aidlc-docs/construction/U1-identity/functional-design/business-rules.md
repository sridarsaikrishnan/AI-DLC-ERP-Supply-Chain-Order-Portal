# Business Rules — U1 Identity & Access

## BR-U1-1: Authentication (US-1.1)
- BR-U1-1.1: Login requires a valid username + matching password (compared as-is for MVP, Q7=A).
- BR-U1-1.2: Invalid credentials return a generic error (no field-specific hint, no existence disclosure).
- BR-U1-1.3: On success with MFA enrolled, a second factor is required before a token is issued (BR-U1-2).

## BR-U1-2: MFA (US-1.2, TOTP)
- BR-U1-2.1: If the user has an MfaEnrollment, a valid TOTP code is required to complete login.
- BR-U1-2.2: An invalid/expired code denies access; the user may retry (subject to throttle).

## BR-U1-3: Soft Throttle (US-1.1)
- BR-U1-3.1: After N consecutive failed attempts (default 5), further attempts on that account are delayed/blocked until `throttledUntil`.
- BR-U1-3.2: A successful login resets `failedAttempts` and clears `throttledUntil`.

## BR-U1-4: Security Context / Tenant Scoping (US-1.3)
- BR-U1-4.1: A validated token yields a SecurityContext { userId, tenantId, role } (U0 type).
- BR-U1-4.2: The tenantId in the context is authoritative for U0 tenant-scoped repositories (fail-closed if absent).
- BR-U1-4.3: A user belongs to exactly one tenant; cross-tenant access is impossible by construction.

## BR-U1-5: Authorization (Q4=A)
- BR-U1-5.1: Corrective actions (resubmit/cancel/amend) require role >= CLIENT_USER.
- BR-U1-5.2: Admin/config operations (U4) require role == ADMIN.
- BR-U1-5.3: Unauthorized access raises AuthorizationError.

## BR-U1-6: User Provisioning (Q1=A)
- BR-U1-6.1: Users are admin/seed provisioned and mapped to a tenant at creation. No self-signup in MVP.
