# User Stories — ERP & Supply Chain Order Portal

**Source**: `aidlc-docs/inception/requirements/requirements.md` and `design/README.md`.
**Approach** (approved plan): hybrid — epics at the top, each story tagged by persona, mapped to journeys, requirement IDs, and designed screens. Acceptance criteria use Given/When/Then; a single shared **Definition of Done** (Section "Cross-cutting") applies to every story instead of repeating it. Priorities use MoSCoW. Personas are defined in `personas.md` (P1 Operator, P2 Reseller Integrator, P3 Reseller Business User, P4 Platform Engineer).

**Legend**
- **Priority**: Must / Should / Could / Won't-for-now (MoSCoW)
- **Reqs**: requirement/acceptance IDs satisfied
- **Screen**: designed screen from `design/README.md`, or "Not yet designed" (design gap to be produced later)
- **Constraints**: applicable SECURITY-xx / RESILIENCY-xx rule IDs (full checks live in the Definition of Done)
- **Proposed**: behavior not yet an approved requirement (tracked as O-08)
- **Assumes**: story written on a recommended default for an open item; see "Open-item assumptions"

---

## EPIC 1 — Onboarding & Access

### US-001: Operator onboards a reseller and issues API access
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-37, FR-01, FR-03 · **Screen**: AdminTenants (`/admin/resellers`), AdminTenantDetail · **Constraints**: SECURITY-08, SECURITY-12, SECURITY-13
- **Story**: As the Platform Operator, I want to onboard a reseller and create its OAuth client, so that the reseller can access the API scoped to its own tenant.
- **Acceptance Criteria**:
  - Given a new reseller, when I onboard them, then a tenant is created and an OAuth client is provisioned in the identity provider with the tenant identifier issued as a token claim.
  - Given the created client, when the reseller authenticates, then every request is scoped by the tenant claim and cannot be overridden by request parameters.
  - Given onboarding actions, when completed, then each change is recorded in the audit trail with actor, timestamp, and before/after values.

### US-002: Operator binds a reseller to its existing ERP customer
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-20, AC-05 · **Screen**: AdminTenantDetail (`/admin/resellers/:tenantId`) · **Constraints**: SECURITY-08
- **Story**: As the Platform Operator, I want to link a reseller to its existing customer record in a specific ERP connection and verify it, so that orders can be delivered against the correct ERP customer.
- **Acceptance Criteria**:
  - Given a reseller and an ERP connection, when I create a binding, then it is verified against the ERP before being saved.
  - Given an existing binding, when I try to create a second binding for the same (tenant, connection), or bind the same ERP customer to another tenant, then the request is refused.
  - Given a customer with no binding, when ERP data for that customer is processed, then it is never published to any tenant.

### US-003: Reseller integrator authenticates machine-to-machine
- **Persona**: P2 · **Priority**: Must · **Reqs**: FR-03, FR-11 · **Screen**: Not yet designed (token/credentials flow) · **Constraints**: SECURITY-08, SECURITY-12
- **Story**: As the Reseller Integrator, I want to authenticate with OAuth 2.0 client credentials, so that my system can call the API securely without a human present.
- **Acceptance Criteria**:
  - Given valid client credentials, when I request a token, then I receive a token carrying my tenant claim.
  - Given a missing, expired, or wrong-issuer token, when I call any endpoint, then the request is rejected.

### US-004: Reseller business user signs in
- **Persona**: P3 · **Priority**: Must · **Reqs**: FR-03 · **Screen**: Not yet designed (sign in) · **Constraints**: SECURITY-12, SECURITY-04
- **Story**: As the Reseller Business User, I want to sign in through the OIDC authorization-code flow, so that I can use the web UI for my tenant only.
- **Acceptance Criteria**:
  - Given valid credentials, when I sign in, then I see only my tenant's data.
  - Given I sign out, when I return, then my session is invalidated and I must sign in again.

### US-005: Operator gets onboarding match suggestions
- **Persona**: P1 · **Priority**: Should · **Reqs**: FR-21 · **Screen**: AdminTenantDetail · **Constraints**: SECURITY-08
- **Story**: As the Platform Operator, I want the system to propose likely matches between a reseller and ERP customer records (by tax ID, email, or code), so that I can confirm bindings quickly.
- **Acceptance Criteria**:
  - Given a reseller, when I open the link flow, then candidate ERP customers are proposed with the matching attribute shown.
  - Given a proposed match, when I confirm it, then a verified binding is created; nothing is bound without my confirmation.

---

## EPIC 2 — Ordering

### US-006: Reseller places an order
- **Persona**: P2 · **Priority**: Must · **Reqs**: FR-05, FR-07, FR-09, FR-12 · **Screen**: Not yet designed (new-order form + line editor) · **Constraints**: SECURITY-05
- **Story**: As the Reseller Integrator, I want to submit an order through the canonical API, so that it is accepted and processed without me knowing the target ERP.
- **Acceptance Criteria**:
  - Given a valid order payload, when I submit it, then it is accepted quickly with an order identifier and an initial lifecycle status.
  - Given an invalid payload (types, lengths, formats, list sizes), when I submit it, then it is rejected with a reseller-safe validation error and no partial order is created.

### US-007: Reseller views the order list with status
- **Persona**: P3 · **Priority**: Must · **Reqs**: FR-34, FR-12..FR-15 · **Screen**: Main (`/orders`) · **Constraints**: SECURITY-08 · **Assumes**: O-07 (whether "Sent to ERP" wording is shown to resellers)
- **Story**: As the Reseller Business User, I want a list of my orders with current status and an attention notice, so that I can see at a glance what needs action.
- **Acceptance Criteria**:
  - Given my orders, when I open the list, then each shows the exact lifecycle status wording and a status badge in the correct role.
  - Given orders needing attention (Retrying, Rejected), when I open the list, then they are surfaced in the attention notice.
  - Given the list, when displayed, then no ERP name, instance, or ERP record ID appears anywhere.

### US-008: Reseller views order detail and timeline
- **Persona**: P3 · **Priority**: Must · **Reqs**: FR-34, FR-12..FR-15 · **Screen**: OrderDetail (`/orders/:orderId`) · **Assumes**: O-07
- **Story**: As the Reseller Business User, I want to see an order's lines, details, and status timeline, so that I understand its full history.
- **Acceptance Criteria**:
  - Given an order, when I open it, then I see its lines, details, and a timeline of lifecycle transitions including any Retrying state.
  - Given the detail view, when displayed, then it shows the deliveries for this order and no ERP identity.

### US-009: Reseller updates an order
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-09 · **Screen**: OrderDetail / Not yet designed (edit form) · **Constraints**: SECURITY-05 · **Assumes**: O-09 (update rules per lifecycle state)
- **Story**: As a reseller, I want to update an order while its state still allows it, so that I can correct details before fulfillment.
- **Acceptance Criteria**:
  - Given an order in an updatable state, when I submit a valid change, then it is accepted and reflected in status/history.
  - Given an order past the updatable states, when I attempt a change, then it is refused with a reseller-safe message.

### US-010: Reseller cancels an order
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-09 · **Screen**: OrderDetail · **Assumes**: O-09 (cancel rules per lifecycle state)
- **Story**: As a reseller, I want to cancel an order when its state allows, so that I can stop an order I no longer need.
- **Acceptance Criteria**:
  - Given an order in a cancelable state, when I cancel it, then it moves to a canceled outcome and the change is delivered by query and webhook.
  - Given a non-cancelable state, when I attempt to cancel, then it is refused with a reseller-safe message.

### US-011: Reseller reads items (read-only catalog)
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-10 (Q30) · **Screen**: Not yet designed (item catalog) · **Constraints**: SECURITY-08
- **Story**: As a reseller, I want to read the items available to me, so that I can build orders — without being able to modify them.
- **Acceptance Criteria**:
  - Given items synchronized from ERPs, when I query them, then I can read them but any create/update attempt is refused.
  - Given item data, when returned, then it carries no ERP identity or owning-ERP reference.

### US-012: Reseller reads its linked customer
- **Persona**: P2 · **Priority**: Should · **Reqs**: FR-11 · **Screen**: Not yet designed · **Constraints**: SECURITY-08 · **Assumes**: O-04 (reseller already has a customer record in each ERP it buys from)
- **Story**: As the Reseller Integrator, I want to read my linked customer profile, so that I can confirm the account orders are placed against.
- **Acceptance Criteria**:
  - Given a verified binding, when I query my customer, then I see the canonical customer fields and no ERP identity.
  - Given no binding for a needed connection, when I query, then the response is empty/handled gracefully with a reseller-safe message.

---

## EPIC 3 — Routing & Isolation (user-visible outcomes)

### US-013: Platform routes an order to exactly one ERP
- **Persona**: P2 (outcome), P1 (oversight) · **Priority**: Must · **Reqs**: FR-14, FR-16, FR-17, AC-03 · **Screen**: n/a (behavioral) · **Constraints**: SECURITY-11
- **Story**: As a reseller, I want my order routed automatically to the right back-end system, so that I never manage or even know the routing.
- **Acceptance Criteria**:
  - Given an order whose items are all owned by one connection and a tenant with a binding for it, when it is validated, then it is bound to that connection.
  - Given the order is routed, when its lifecycle continues, then the routing decision never changes for the life of the order.

### US-014: Mixed-ERP order is rejected safely
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-18, AC-04 (Q29 = A) · **Screen**: OrderDetail / API error
- **Story**: As a reseller, when I submit an order whose items belong to different back-end systems, I want a clear message to order separately, so that I can fix it without seeing internal details.
- **Acceptance Criteria**:
  - Given an order with items owned by different ERPs, when it is validated, then it is rejected with a reseller-safe message and no ERP is called.
  - Given the rejection message, when shown, then it explains what to do (order separately) and reveals no ERP identity.

### US-015: No ERP identity is ever exposed to resellers
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-19, AC-02 · **Screen**: all reseller screens · **Constraints**: SECURITY-08, SECURITY-11
- **Story**: As a reseller, I want to never see which ERP or instance serves me, so that back-end topology stays hidden.
- **Acceptance Criteria**:
  - Given any reseller-facing response, error, webhook, delivery-log entry, or UI screen, when inspected, then it contains no ERP name, instance, or ERP record identifier.
  - Given an ERP error, when surfaced to a reseller, then it is mapped to a canonical code with a reseller-safe message.

### US-016: Tenant data isolation
- **Persona**: P2 · **Priority**: Must · **Reqs**: FR-01, AC-01 · **Screen**: n/a (behavioral) · **Constraints**: SECURITY-08
- **Story**: As a reseller, I want my data strictly isolated from other tenants, so that no one can read or affect my orders.
- **Acceptance Criteria**:
  - Given a valid token for tenant A, when a request carries another tenant's identifier in its body or parameters, then that identifier is ignored and only tenant A's data is returned.
  - Given a resource ID belonging to another tenant, when requested, then access is denied.

---

## EPIC 4 — Delivery & Reliability

### US-017: Guaranteed delivery through an ERP outage
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-29, FR-13, AC-07 · **Screen**: OrderDetail (Retrying in timeline) · **Constraints**: RESILIENCY-10, RESILIENCY-12
- **Story**: As a reseller, I want my accepted order to be delivered even if the back-end is temporarily down, so that I never lose an order.
- **Acceptance Criteria**:
  - Given the owning ERP is unavailable, when I submit an order, then it is accepted, shown as Retrying, and delivered once the ERP returns.
  - Given repeated failures, when retries are exhausted per policy, then the message goes to a dead-letter path visible to the operator (not the reseller).

### US-018: Exactly-once effect under at-least-once delivery
- **Persona**: P2 · **Priority**: Must · **Reqs**: FR-30, AC-08, AC-16 · **Screen**: n/a · **Constraints**: RESILIENCY-10
- **Story**: As a reseller, I want duplicate processing to never create duplicate orders, so that my records stay correct.
- **Acceptance Criteria**:
  - Given a message delivered twice, when processed, then only one record results in the ERP and in the read model.
  - Given the worker crashes mid-processing, when it restarts, then the order completes with no loss and no duplicate.

### US-019: Reads continue when an ERP is down
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-31, AC-10 · **Screen**: Main, OrderDetail, DeliveryLog · **Constraints**: RESILIENCY-10
- **Story**: As a reseller, I want to keep reading my orders, items, and delivery log even during a back-end outage, so that the portal stays useful.
- **Acceptance Criteria**:
  - Given an ERP is down, when I query orders, items, or the delivery log, then the queries succeed from the platform's read model.

### US-020: ERP status changes appear in the lifecycle
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-15, FR-28, AC-09 · **Screen**: OrderDetail
- **Story**: As a reseller, I want back-end status changes reflected in my order's status, so that what I see stays current.
- **Acceptance Criteria**:
  - Given the ERP changes an order's status, when the change is ingested, then the mapped lifecycle state is visible by query and delivered by webhook.

### US-021: Rejected order shows a safe reason
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-13, FR-19 · **Screen**: OrderDetail
- **Story**: As a reseller, when the back-end refuses my order, I want a clear, safe reason, so that I can act without seeing internal detail.
- **Acceptance Criteria**:
  - Given the ERP rejects an order, when I view it, then it shows Rejected with a reseller-safe reason and no ERP identity.

---

## EPIC 5 — Webhooks & Delivery Log

### US-022: Reseller manages webhook endpoints
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-32 · **Screen**: WebhookEndpoints (`/webhooks`) · **Constraints**: SECURITY-05, SECURITY-08
- **Story**: As a reseller, I want to register and manage webhook endpoints (create, update, pause, resume, deactivate), so that my system receives status updates.
- **Acceptance Criteria**:
  - Given a new endpoint, when I add it, then a one-time signing secret is shown once and stored only as a hash.
  - Given an endpoint, when I pause/resume/deactivate it, then delivery behavior changes accordingly.

### US-023: Signed webhook delivery
- **Persona**: P2 · **Priority**: Should · **Reqs**: FR-32 · **Screen**: WebhookEndpoints · **Constraints**: SECURITY-13 · **Proposed**: signature header format and replay window (O-08)
- **Story**: As the Reseller Integrator, I want webhook requests signed, so that I can verify they came from the platform.
- **Acceptance Criteria**:
  - Given a delivered webhook, when I verify the signature with my secret, then valid requests verify and tampered ones fail.
  - Given the verification help on screen, when I follow it, then I can implement verification without back-end knowledge.

### US-024: Delivery log with attempts and replay
- **Persona**: P2, P3 · **Priority**: Must · **Reqs**: FR-33, AC-11 · **Screen**: DeliveryLog (`/deliveries`) · **Constraints**: SECURITY-08
- **Story**: As a reseller, I want a delivery log of each webhook with its attempts and payload, and the ability to replay, so that I can diagnose and recover missed events.
- **Acceptance Criteria**:
  - Given a webhook endpoint fails, when delivery is attempted, then attempts are retried and each is recorded with status, timestamps, and the canonical payload.
  - Given a delivery entry, when I replay it, then the event is re-sent; the log contains no ERP identity.

### US-025: Webhook event types
- **Persona**: P2 · **Priority**: Should · **Reqs**: FR-32 · **Screen**: WebhookEndpoints · **Proposed**: event names `order.created`, `order.status_changed`, `order.retrying`, `order.rejected` (O-08)
- **Story**: As the Reseller Integrator, I want well-named event types, so that I can route events in my system.
- **Acceptance Criteria**:
  - Given a lifecycle change, when it occurs, then the matching event type is emitted with the canonical payload shape.

### US-026: Signing-secret rotation with overlap
- **Persona**: P2 · **Priority**: Could · **Reqs**: FR-32 · **Screen**: WebhookEndpoints · **Proposed**: 24-hour overlap on rotation (O-08)
- **Story**: As the Reseller Integrator, I want to rotate a signing secret with an overlap window, so that I can migrate without missing verifications.
- **Acceptance Criteria**:
  - Given I rotate a secret, when the overlap window is active, then signatures from either the old or new secret verify; after it ends, only the new one does.

---

## EPIC 6 — ERP Integration & Extensibility

### US-027: Add an ERP through configuration
- **Persona**: P4 · **Priority**: Must · **Reqs**: FR-24, FR-26, FR-27 · **Screen**: Not yet designed (connection/mapping admin) · **Constraints**: SECURITY-01, SECURITY-06
- **Story**: As the Platform Engineer, I want to add a new ERP (or instance) via configuration — endpoint, auth, capabilities — so that onboarding it takes days, not months.
- **Acceptance Criteria**:
  - Given connection configuration, when I register a new ERP instance, then it is available for routing and ingestion without new connector code.
  - Given credentials, when stored, then they are encrypted per connection and never logged.

### US-028: Declarative canonical↔native mappings
- **Persona**: P4 · **Priority**: Must · **Reqs**: FR-25 · **Screen**: Not yet designed (mapping viewer/editor) · **Constraints**: SECURITY-13
- **Story**: As the Platform Engineer, I want to define declarative field maps and named transforms between the canonical model and each ERP's format, so that no per-ERP template or transformation language is needed.
- **Acceptance Criteria**:
  - Given a mapping, when I define source/target paths, type conversions, and value lookups, then canonical data converts to native and back.
  - Given a lossy field, when mapped, then the acceptable deviation is documented (verified later by round-trip property tests).

### US-029: Conformance suite for an ERP
- **Persona**: P4 · **Priority**: Must · **Reqs**: FR-27, AC-12 · **Screen**: n/a
- **Story**: As the Platform Engineer, I want a conformance suite that proves a new/changed ERP integration, so that I can trust it before enabling it.
- **Acceptance Criteria**:
  - Given a new ERP added with configuration, mappings, and fixtures, when the conformance suite runs, then it passes without changes to core code beyond registered transform functions.

### US-030: Ingest ERP changes into the read model
- **Persona**: P4, P2 · **Priority**: Must · **Reqs**: FR-28, AC-09 · **Screen**: n/a · **Constraints**: RESILIENCY-05
- **Story**: As the Platform Engineer, I want ERP-side changes ingested by polling or events and translated to canonical events, so that the read model stays current.
- **Acceptance Criteria**:
  - Given an ERP change, when ingested, then it is translated to a canonical event and applied to the read model, and downstream status/webhooks reflect it.

### US-031: Encrypted ERP credential storage
- **Persona**: P1, P4 · **Priority**: Must · **Reqs**: FR-26, NFR-06 · **Screen**: AdminConnections · **Constraints**: SECURITY-01, SECURITY-12
- **Story**: As the Platform Operator, I want each ERP connection's credentials stored encrypted, so that a database leak does not expose ERP access.
- **Acceptance Criteria**:
  - Given credentials, when saved, then they are AES-GCM encrypted with a key from configuration and a stored key identifier, and are never returned in plaintext or logs.

---

## EPIC 7 — Operator Administration

### US-032: Monitor connection health
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-26, FR-35 · **Screen**: AdminConnections (`/admin/connections`) · **Constraints**: RESILIENCY-05, RESILIENCY-06, RESILIENCY-07
- **Story**: As the Platform Operator, I want to see each connection's health, queue, settings, and recent errors, so that I can act before resellers are affected.
- **Acceptance Criteria**:
  - Given connections, when I open the screen, then I see health status, queue/backlog, and recent raw errors (operator-only).

### US-033: Resolve item-ownership conflicts
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-22, AC-06 · **Screen**: AdminItemOwnership (`/admin/items/ownership`)
- **Story**: As the Platform Operator, I want to resolve items reported by more than one ERP, so that each tenant-visible item has exactly one owner.
- **Acceptance Criteria**:
  - Given two ERPs report the same item, when items sync, then the item is flagged and not published to tenants until I resolve ownership.
  - Given a conflict, when I assign an owner, then the item becomes publishable.

### US-034: Triage failed and dead-lettered messages
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-29, FR-30, FR-19 · **Screen**: AdminFailedMessages (`/admin/failed-messages`) · **Constraints**: RESILIENCY-10
- **Story**: As the Platform Operator, I want to see retrying, rejected, and dead-lettered messages with the raw ERP error beside the reseller-safe message, so that I can diagnose and recover.
- **Acceptance Criteria**:
  - Given failing messages, when I open the screen, then I see the raw error (operator-only) next to the reseller-safe message, and can retry or resolve.

### US-035: Review the audit trail
- **Persona**: P1 · **Priority**: Must · **Reqs**: FR-38 · **Screen**: AdminAudit (`/admin/audit`) · **Constraints**: SECURITY-13, SECURITY-14
- **Story**: As the Platform Operator, I want an audit trail of administrative changes with before/after values, so that changes are accountable.
- **Acceptance Criteria**:
  - Given any administrative change, when it happens, then it is recorded with who, what, when, and before/after values, and the log cannot be altered by application roles.

### US-036: Manage field mappings (operator view)
- **Persona**: P1 · **Priority**: Should · **Reqs**: FR-25, FR-35 · **Screen**: Not yet designed (mapping editor)
- **Story**: As the Platform Operator, I want to view and adjust mappings for a connection, so that I can correct field issues without a code change.
- **Acceptance Criteria**:
  - Given a connection's mappings, when I view them, then I see field maps and transforms; edits are audited and validated before taking effect.

---

## EPIC 8 — Developer Enablement

### US-037: One-command local environment
- **Persona**: P4 · **Priority**: Must · **Reqs**: FR-39, AC-13, NFR-09 · **Screen**: n/a
- **Story**: As the Platform Engineer, I want the whole stack to start locally in containers with one command, so that I can develop and test without a cloud account.
- **Acceptance Criteria**:
  - Given a fresh clone, when I run the single start command, then the full stack starts in containers and integration tests pass without a cloud account.

### US-038: Safe seed tool
- **Persona**: P4 · **Priority**: Must · **Reqs**: FR-40, AC-14 · **Screen**: n/a
- **Story**: As the Platform Engineer, I want a seed tool that creates fictional data on non-production targets only, so that I can populate environments safely and reversibly.
- **Acceptance Criteria**:
  - Given a target outside the allow-list, when the seed tool runs, then it refuses.
  - Given an allowed target, when I run it twice, then it creates no duplicates; when I reset, then it removes only what it created.

---

## Cross-cutting — Definition of Done (applies to every story)

A story is Done only when all of the following hold (per the approved Q3/Q6 approach; this replaces a per-story checklist):

- **Functional**: acceptance criteria pass; example-based tests cover the criteria.
- **Security (Q19=A, blocking)**: inputs validated (SECURITY-05); authZ enforced with tenant/object/function checks and server-side token validation (SECURITY-08); no secrets/PII/ERP identity in logs (SECURITY-03); errors fail closed and generic to users (SECURITY-15); relevant SECURITY-01..15 items for the story are satisfied or marked N/A with rationale.
- **No ERP identity (FR-19/AC-02)**: verified for every reseller-facing output on the story.
- **Resiliency (Q20=A, blocking)**: external calls have timeouts; delivery paths are idempotent and use the durable queue/outbox with retry/backoff where applicable (RESILIENCY-10, RESILIENCY-12); health/metrics emitted (RESILIENCY-05, RESILIENCY-06).
- **Property-based testing (Q21=A, full)**: identified properties (round-trip mapping, idempotent processing, routing determinism, binding/ownership uniqueness, lifecycle state machine) have PBT with shrinking and logged seeds, alongside example-based tests (PBT-01..PBT-10).
- **Accessibility (UI stories)**: text contrast ≥ 4.5:1, control borders ≥ 3:1 in light and dark themes, real semantic elements, visible focus ring, no color-only meaning; tokens/components from the design system (no new hex or fonts; self-hosted fonts).
- **Traceability**: story references its FR/AC and screen (or "Not yet designed"); audit trail captures operator changes.

---

## Open-item assumptions (stories written on recommended defaults; confirm)

| Open item | Assumption used | Stories | Status |
|---|---|---|---|
| O-01 | Mixed-ERP orders rejected at Validated | US-014 | Resolved (Q29=A); no longer an assumption |
| O-02 | Items read-only for resellers | US-011 | Resolved (Q30=A); no longer an assumption |
| O-04 | Each reseller already has a customer record in each ERP it buys from | US-012 | Open — confirm |
| O-07 | Lifecycle label "Sent to ERP" may be shown to resellers | US-007, US-008 | Open — confirm (may need reseller-safe relabel) |
| O-08 | Webhook signing scheme, replay window, event names, secret-rotation overlap | US-023, US-025, US-026 | Open (proposed) — confirm |
| O-09 | Order update/cancel rules per lifecycle state | US-009, US-010 | Open — confirm |

---

## Future scope — Won't-for-now (scope boundaries)

- **US-F1: Self-service ERP onboarding by customers** — customers add an ERP via UI/config with no platform-engineer involvement. (Future phase, Q16.)
- **US-F2: Automated cross-ERP workflows** — an event in one ERP triggers action in another. (Future phase, Q16.)
- **US-F3: SAP support** — add SAP as a third ERP. (Out of MVP, Q1.)
- **US-F4: Split orders across ERPs** — one order fulfilled by multiple ERPs. (Explicitly out; MVP is one order = one ERP.)
- **US-F5: Platform-created ERP customers** — the platform creates/updates ERP customer records. (Out; platform only binds to existing customers.)
- **US-F6: Data exports** — reseller/operator export features. (Proposed in design; deferred.)
- **US-F7: AI-assisted ERP onboarding via MCP** — an MCP server wraps the onboarding surface (introspect ERP schema, propose mappings, create connection, run conformance, read failures) so an AI agent can draft config + declarative mappings and iterate until the conformance suite passes; a human operator approves, and it runs against non-production targets first. Feasible because onboarding is declarative config + mappings, not connector code (FR-24..FR-27). Guardrails: no auto-publish to tenants (FR-20, FR-22), no ERP-identity leakage (FR-19), operator-managed encrypted credentials. (Future phase; extends Q16.)

**Design principle carried into Application Design** (to keep US-F7 cheap later): ERP onboarding operations (connections, mappings, conformance runs) are exposed as an **API-first, machine-drivable interface**; the operator admin UI is a client of that API, not the only way to drive it.

---

## Coverage check (requirements → stories)

| Requirement area | Stories |
|---|---|
| Tenancy & access (FR-01..FR-04) | US-001, US-003, US-004, US-016 |
| Reseller API & payloads (FR-05..FR-07) | US-006, US-011, US-012, US-022 |
| Business data (FR-08..FR-11) | US-006, US-011, US-012, US-002 |
| Order lifecycle (FR-12..FR-15) | US-006, US-007, US-008, US-009, US-010, US-020, US-021 |
| Routing (FR-16..FR-19) | US-013, US-014, US-015 |
| Binding & ownership (FR-20..FR-22) | US-002, US-005, US-033 |
| ERP integration (FR-23..FR-28) | US-027, US-028, US-029, US-030, US-031 |
| Delivery reliability (FR-29..FR-31) | US-017, US-018, US-019 |
| Webhooks & delivery log (FR-32, FR-33) | US-022, US-023, US-024, US-025, US-026 |
| UIs (FR-34, FR-35, FR-36) | US-007, US-008, US-024, US-032..US-035 |
| Operator administration (FR-37, FR-38) | US-001, US-035 |
| Dev & test (FR-39, FR-40) | US-037, US-038 |
