# Functional Design Plan — U1 Identity & Access

## Unit Context
U1 handles authentication (username/password), MFA, security context resolution, and authorization. Stories: US-1.1 (login), US-1.2 (MFA), US-1.3 (tenant-scoped access). Depends on U0 (persistence, SecurityContext, errors). Note accepted risk Q7=A: passwords stored as-is (no hashing) for MVP.

## Artifacts
- [ ] `business-logic-model.md` (login, MFA, context resolution, authorization processes)
- [ ] `business-rules.md` (credential rules, MFA rules, authorization rules, throttling)
- [ ] `domain-entities.md` (User, Credential, MfaEnrollment, Session/Token, Role)

---

## Questions

## Question 1
How are users and their tenant assignment created for MVP?

A) Seeded/admin-provisioned users (an admin or seed script creates users mapped to a tenant); no self-signup (recommended for MVP)

B) Self-registration flow where users sign up and are assigned to a tenant

C) Recommend

[Answer]: 

## Question 2
What MFA method for MVP (US-1.2)?

A) TOTP (authenticator app) — standard, no external dependency (recommended)

B) Email one-time code

C) SMS one-time code (needs an SMS provider)

D) Recommend

[Answer]: 

## Question 3
Session/token model for the API?

A) Stateless signed token (JWT-style) returned on login, sent as a bearer token (recommended)

B) Server-side session id stored in DB, sent as a cookie/header

C) Recommend

[Answer]: 

## Question 4
Authorization / roles model for MVP?

A) Two roles: ClientUser (place/track/correct own tenant's orders) and Admin (routing/mapping/instance config). Corrective actions require ClientUser+; admin config requires Admin. (recommended)

B) Single role for all authenticated users (no role distinction yet)

C) Fine-grained permissions per action

D) Recommend

[Answer]: 

## Question 5
Login throttling / lockout (US-1.1 acceptance criteria mention throttling)?

A) Soft throttle: after N failed attempts, temporary delay/backoff on that account (recommended)

B) Hard lockout: lock the account after N failures until admin/timed reset

C) None for MVP

D) Recommend

[Answer]: 

---

Fill in the `[Answer]:` tags and let me know when done (or reply "recommended").
