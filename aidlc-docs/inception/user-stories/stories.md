# User Stories — ERP & Supply Chain Order Portal

**Breakdown approach**: Feature-Based (organized by feature area/epic).
**Personas**: Client Order User (external), Platform Administrator (internal). See `personas.md`.
**Acceptance criteria**: Given/When/Then, happy path + key error/edge cases.
**Ordering**: Sequenced by epic (no separate priority levels).
**Scope**: MVP only. Deferred future capabilities (AI-assisted connector generation, self-service onboarding wizard, cross-system failover, SAP adapter, partner/API access) are intentionally excluded from stories per planning decision Q4=A.

All stories follow INVEST (Independent, Negotiable, Valuable, Estimable, Small, Testable).

---

## Epic E1: Client Access & Authentication

### US-1.1: Client user login
**As a** Client Order User, **I want** to log in with my username and password **so that** I can access my organization's ordering portal securely.

**Acceptance Criteria**
- Given a registered user with valid credentials, When they submit username and password, Then they are authenticated and taken to their portal home.
- Given invalid credentials, When they submit, Then login is rejected with a generic error and no indication of which field was wrong.
- Given repeated failed attempts, When the threshold is exceeded, Then further attempts are temporarily throttled.

### US-1.2: Multi-factor authentication
**As a** Client Order User, **I want** to complete an MFA step during login **so that** my account is protected beyond a password.

**Acceptance Criteria**
- Given a user has passed the password step, When MFA is required, Then they must provide a valid second factor before access is granted.
- Given an invalid or expired MFA code, When submitted, Then access is denied and the user may retry.

### US-1.3: Tenant-scoped access
**As a** Client Order User, **I want** to see only my organization's data **so that** other clients' orders are never visible to me.

**Acceptance Criteria**
- Given a logged-in user belonging to tenant T, When they view any order/catalog/inventory data, Then only records associated with tenant T are returned.
- Given a direct request for a record belonging to another tenant, When the request is made, Then it is denied (not found / forbidden).

---

## Epic E2: Order Placement

### US-2.1: Create and submit a sales order
**As a** Client Order User, **I want** to create and submit a sales order using canonical (ERP-agnostic) fields **so that** I can order without knowing which ERP fulfills it.

**Acceptance Criteria**
- Given a valid canonical order (customer/ship-to, line items with product + quantity, required fields), When submitted, Then the order is accepted, persisted against my tenant, and assigned a portal order ID.
- Given an order missing required canonical fields or failing validation, When submitted, Then submission is rejected with field-level validation messages and nothing is sent to any ERP.
- Given a valid order, When accepted, Then it enters the lifecycle in an initial "Submitted" state (see E4).

### US-2.2: See submission outcome and ERP acknowledgment
**As a** Client Order User, **I want** clear feedback on whether my order reached the target ERP **so that** I know it was received.

**Acceptance Criteria**
- Given an order routed to an ERP instance, When the ERP acknowledges receipt, Then the portal shows an accepted/acknowledged status with the ERP reference.
- Given the ERP returns an error on submission, When the response is received, Then the portal shows an understandable error and marks the order as failed (eligible for resubmit per E5).

---

## Epic E3: Catalog & Inventory Lookup

### US-3.1: Browse product catalog
**As a** Client Order User, **I want** to browse/search the product catalog **so that** I can find products to order.

**Acceptance Criteria**
- Given catalog data available for my tenant's routing context, When I browse or search, Then matching canonical products are listed with key attributes.
- Given no products match a search, When I search, Then an empty-state message is shown (not an error).

### US-3.2: Check inventory availability
**As a** Client Order User, **I want** to check inventory availability for a product **so that** I know whether it can be fulfilled before I order.

**Acceptance Criteria**
- Given a product, When I request availability, Then the portal returns current canonical availability sourced from the relevant ERP instance.
- Given the ERP is unreachable or returns no data, When availability is requested, Then the portal shows an "availability unavailable" indicator rather than failing the whole page.

---

## Epic E4: Order Lifecycle Tracking

### US-4.1: View current order status
**As a** Client Order User, **I want** to view the current status of my orders **so that** I know where each one is in the process.

**Acceptance Criteria**
- Given orders belonging to my tenant, When I open the orders list, Then each order shows its current lifecycle status (e.g., Submitted, Accepted, Processing, Shipped, Invoiced, Failed, Cancelled).
- Given an order, When I open its detail, Then I see the current status and the ERP reference.

### US-4.2: View order status history
**As a** Client Order User, **I want** to see the history of status changes for an order **so that** I can trace its progression.

**Acceptance Criteria**
- Given an order that has changed status over time, When I view its history, Then each transition is listed with a timestamp in chronological order.

### US-4.3: Status reflects ERP updates
**As a** Client Order User, **I want** the portal to reflect status changes coming from the ERP **so that** my view stays accurate without manual refresh from the ERP.

**Acceptance Criteria**
- Given the ERP updates an order's status, When the portal ingests that update, Then the order's status and history are updated accordingly.
- Given conflicting or out-of-order updates, When ingested, Then the portal applies them consistently (latest known state wins, with history preserved).

---

## Epic E5: Order Corrective Actions

### US-5.1: Resubmit a failed order
**As a** Client Order User, **I want** to resubmit an order that failed **so that** I can recover from transient errors without re-entering everything.

**Acceptance Criteria**
- Given an order in Failed state, When I resubmit, Then the portal re-sends it to the routed ERP instance and updates status based on the new outcome.
- Given an order not in a resubmittable state, When resubmit is attempted, Then the action is unavailable/blocked with an explanation.

### US-5.2: Cancel an order
**As a** Client Order User, **I want** to cancel an order **so that** I can stop fulfillment when it's no longer needed.

**Acceptance Criteria**
- Given an order in a cancellable state, When I cancel, Then the portal sends a cancel request to the ERP and, on success, marks the order Cancelled.
- Given the ERP rejects the cancellation (e.g., already shipped), When the response is received, Then the portal surfaces the reason and leaves the order in its prior state.

### US-5.3: Amend an order
**As a** Client Order User, **I want** to amend an order **so that** I can correct details before it's fulfilled.

**Acceptance Criteria**
- Given an order in an amendable state, When I submit valid amended canonical data, Then the portal sends the amendment to the ERP and reflects the outcome.
- Given amended data fails validation, When submitted, Then the amendment is rejected with field-level messages and the original order is unchanged.
- Given the ERP rejects the amendment, When the response is received, Then the portal surfaces the reason and preserves the prior order state.

---

## Epic E6: Routing & Mapping Configuration (Administrator)

### US-6.1: Register an ERP instance
**As a** Platform Administrator, **I want** to register an ERP instance (type, connection details) via a minimal internal UI **so that** the portal can route orders to it.

**Acceptance Criteria**
- Given valid ERP instance details (ERP type, endpoint, credentials reference), When I save, Then the instance is registered and available for routing rules and mappings.
- Given incomplete or invalid connection details, When I save, Then validation errors are shown and nothing is registered.
- Given a registered instance, When I request a connectivity check, Then the portal reports reachable/unreachable.

### US-6.2: Define content-based routing rules
**As a** Platform Administrator, **I want** to define routing rules based on order content (e.g., product line, region, warehouse) **so that** each order is sent to the correct ERP instance.

**Acceptance Criteria**
- Given registered ERP instances, When I create a rule mapping order-content conditions to a target instance, Then the rule is saved and applied to subsequent orders.
- Given an order matching a rule, When it is routed, Then it goes to the rule's target instance.
- Given an order matching no rule, When routed, Then it is rejected with a clear "no route matched" error (per FR-3.4).
- Given overlapping rules, When evaluated, Then a defined precedence determines the single selected instance.

### US-6.3: Manage canonical-to-ERP mappings
**As a** Platform Administrator, **I want** to manage field/value mappings between the canonical model and an ERP's schema via the minimal internal UI **so that** onboarding a new ERP is configuration, not custom code.

**Acceptance Criteria**
- Given a registered ERP instance, When I define field and value mappings for the four business data types, Then those mappings are used when translating canonical data to/from that ERP.
- Given a required canonical field with no mapping, When I save, Then the portal warns about the unmapped required field.
- Given a saved mapping, When an order is routed to that ERP, Then canonical data is translated per the mapping before submission and ERP responses are translated back to canonical.

### US-6.4: View current routing and mapping configuration
**As a** Platform Administrator, **I want** to view the current routing rules and mappings **so that** I can verify configuration and troubleshoot.

**Acceptance Criteria**
- Given existing configuration, When I open the config view, Then registered instances, routing rules, and mappings are displayed accurately.
- Given a recent change, When I view the config, Then the displayed configuration reflects the latest saved state.

---

## Traceability: Stories to Requirements

| Story | Requirements |
|---|---|
| US-1.1, US-1.2 | FR-7.1, FR-7.2 |
| US-1.3 | FR-6.2, FR-6.3, NFR-3.1, NFR-3.2 |
| US-2.1 | FR-1.1, FR-1.2, FR-1.3, FR-2.1 |
| US-2.2 | FR-8.1, FR-5.1 |
| US-3.1 | FR-2.3 |
| US-3.2 | FR-2.4 |
| US-4.1, US-4.2 | FR-2.2, FR-5.1, FR-5.4 |
| US-4.3 | FR-5.2 |
| US-5.1 | FR-5.3, FR-8.2 |
| US-5.2, US-5.3 | FR-5.3 |
| US-6.1 | FR-3.3, FR-4.4 |
| US-6.2 | FR-3.1, FR-3.2, FR-3.4 |
| US-6.3 | FR-4.1, FR-4.2, FR-4.3, NFR-2.1, NFR-2.2 |
| US-6.4 | FR-5.4, NFR-5.1 |
