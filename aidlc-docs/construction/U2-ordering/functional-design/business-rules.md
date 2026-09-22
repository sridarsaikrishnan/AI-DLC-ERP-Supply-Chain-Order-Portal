# Business Rules — U2 Ordering & Lifecycle

## BR-U2-1: Order Submission
- BR-U2-1.1: tenantId is taken from SecurityContext, never from the request body.
- BR-U2-1.2: Order must pass U0 canonical validation (BR-1) before persistence; nothing is sent to any ERP on validation failure.
- BR-U2-1.3: A valid order is persisted as Submitted and a SUBMISSION job enqueued (idempotent by order_id).

## BR-U2-2: Tenant Scoping (US-1.3)
- BR-U2-2.1: All reads/writes go through U0 tenant-scoped repositories (fail-closed).
- BR-U2-2.2: Access to another tenant's order returns not-found.

## BR-U2-3: Corrective Actions (Q3=A, Q4=A)
- BR-U2-3.1: Requires role >= CLIENT_USER (U1 authorization).
- BR-U2-3.2: Allowed only from states that permit the action (RESUBMIT from Failed; CANCEL/AMEND from non-terminal states); otherwise 409/blocked with explanation.
- BR-U2-3.3: AMEND re-validates the full amended canonical order (BR-1) before enqueueing.
- BR-U2-3.4: Actions are enqueued (async); the API returns "accepted"; outcome reflected via lifecycle (U3).

## BR-U2-4: Lookups (Q1=B, Q2=B)
- BR-U2-4.1: Catalog/inventory served from portal seed/cache against a default instance for MVP; empty results are a normal empty-state, not an error.
