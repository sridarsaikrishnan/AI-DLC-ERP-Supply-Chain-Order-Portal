# Requirements Document - ERP & Supply Chain Order Portal

**Date**: 2026-09-21
**Status**: Draft for review - generated from the answers in `requirement-verification-questions.md`. Resiliency decisions are recorded at MVP level (Q22-Q28) and should be confirmed.
**Architecture direction (updated 2026-09-21)**: AWS-native. Backend Java + Spring Boot; identity = Amazon Cognito; messaging = Amazon SQS FIFO + SNS; datastore = RDS PostgreSQL (kept). The earlier portable-core rule is retired (see NFR-05). Local development uses the Floci AWS emulator (Cognito/SQS/SNS) plus a real PostgreSQL container; the auth/token path is validated against real Cognito in a dev AWS account.
**Requirement source tags**: Q# = questionnaire answer, D = decision made by the user in discussion, P = proposed design direction (to confirm in Application Design).

---

## 1. Intent Analysis Summary

- **User request**: "I have a requirement to build a application portal for ERP and Supply chain. This portal will be used by external clients to place order to various ERP systems such as SAP, ERP Next and Odoo. Each ERP system can have multiple instances. It will interact over order management workflow and able to seamlessly route the requests to respective ERP system without having to write integrators/connectors. We will start small, proving it works with two ERPs and four kinds of business data, then grow toward easier setup by customers and automated workflows between systems, so that adding the next ERP takes days and not months. I want to build it using AIDLC"
- **Request type**: New Project (greenfield, standalone product; nothing reused from any existing system)
- **Scope estimate**: System-wide and cross-system (API, workers, UI, identity, infrastructure, integration with multiple ERPs)
- **Complexity estimate**: Complex
- **Requirements depth**: Comprehensive (multi-tenant, security-critical, many integrations, traceability required)

## 2. Business Context

### 2.1 Goal
A multi-tenant order portal that lets resellers place and track orders that are delivered to the platform operator's ERP systems, without writing a connector per ERP. The MVP proves the approach with two ERPs and four kinds of business data. The longer-term goal is that adding the next ERP takes days, not months (Q16).

### 2.2 Actors
- **Platform operator (admin)**: the user's organization. Owns the ERPs, onboards resellers, configures ERP connections, mappings, item ownership and customer bindings, and sees raw ERP details.
- **Tenant = reseller**: one level of tenancy. Consumes the platform APIs directly (GraphQL preferred) and a web UI showing the data sent to their system. Never knows which ERP or instance serves them (D).
- **ERPs**: Odoo and ERPNext in the MVP (Q1 = C). Owned and operated on the operator's side. Customers already exist in them (D).

### 2.3 Terminology
- **Connection**: one ERP instance (ERP type + endpoint + credentials + capabilities).
- **Canonical model**: the fixed, platform-defined shape of each business entity, identical for every tenant.
- **Binding**: the operator-created link between a tenant and its existing customer record in one ERP connection.
- **Item owner**: the single ERP connection that owns an item.

### 2.4 MVP scope
- **In**: two ERPs, four data types (Q2), full order lifecycle (Q4), GraphQL API and web UI for resellers, admin surface for the operator, asynchronous guaranteed delivery, local-container development, AWS deployment.
- **Out (future phases)**: self-service onboarding by customers, automated cross-ERP workflows (Q16 = D), SAP, per-tenant output templates, ERP customer creation by the platform, multi-ERP split orders.

---

## 3. Functional Requirements

### 3.1 Tenancy and access
- **FR-01** Tenant is the reseller, one level only. Every request is scoped by a tenant identifier taken from a validated token claim, never from request parameters or the body. (Q9, Q11, D)
- **FR-02** A tenant may be served by several ERP connections (different ERPs and different instances). (Q9 = C, D)
- **FR-03** Partner systems authenticate with OAuth 2.0 client credentials; human UI users authenticate with OIDC authorization code. (Q8 = C, Q11 = B)
- **FR-04** The operator has a separate admin surface with function-level authorization; tenants cannot reach it. (D)

### 3.2 Reseller API
- **FR-05** Expose a GraphQL API (preferred) with queries for orders, items and the tenant's linked customer, and mutations to create, update and cancel orders and to manage webhook endpoints. (Q8, D)
- **FR-06** Response and webhook payloads have one canonical, fixed shape for every tenant. There are no per-tenant output templates or transformation languages. (D)
- **FR-07** Order mutations are acknowledged quickly with an order identifier; outcomes arrive as status changes, visible by query and by webhook. (Q7 = A)

### 3.3 Business data (Q2 = A)
- **FR-08** Canonical models for Sales Order, Purchase Order, Product/Item and Customer.
- **FR-09** Orders (Sales and Purchase): create, read, update and cancel (Q3 = C), subject to lifecycle-state rules to be defined in Functional Design.
- **FR-10** Items are synchronized from the ERPs and are read-only for tenants; tenants cannot create or update items. Each item has exactly one owning ERP connection. (Q30 = A, confirmed; D)
- **FR-11** Customers are existing ERP records, linked to tenants by binding and read-only for tenants. The platform does not create or update ERP customers in production. (D)

### 3.4 Order lifecycle (Q4 = B)
- **FR-12** States: Draft, Submitted, Validated, Sent to ERP, Confirmed, Fulfilled, Closed.
- **FR-13** Exception states Retrying (delivery to the ERP failed and is queued for retry) and Rejected (the ERP refused the order, reason shown). (P, derived from Q7)
- **FR-14** The Validated step performs input and business validation, resolves routing, and checks the customer binding. Its routing result is stored and never changes for the life of the order. (P)
- **FR-15** After Sent to ERP, status movements come only from the order's owning ERP, translated to the lifecycle through a per-ERP status mapping table. (D)

### 3.5 Routing
- **FR-16** One order goes to exactly one ERP connection. Orders and items are not split across ERPs. (D)
- **FR-17** Routing is decided by the platform from the ownership of the order's items (Q10 = C). A tenant-level default applies only to orders that have no items yet, such as drafts. (P)
- **FR-18** An order whose items are owned by different ERPs is rejected at Validated with a reseller-safe message asking the reseller to order separately. (Q29 = A, confirmed)
- **FR-19** ERP identity is never exposed to a tenant: no ERP name, instance or ERP record identifier in the API, errors, webhooks, delivery log or UI. The reseller and admin GraphQL schemas are separate, and ERP errors are mapped to canonical error codes with reseller-safe messages. (D)

### 3.6 Customer binding and item ownership
- **FR-20** The operator creates a binding per (tenant, connection) to an existing ERP customer, verified against the ERP when created. Uniqueness: one binding per (tenant, connection), and an ERP customer belongs to at most one tenant. An order needs a binding for its owning ERP. ERP data for unbound customers is never published to any tenant. (P)
- **FR-21** A one-time onboarding aid proposes matches between resellers and ERP customers (for example by tax ID, email or code) from the ERPs' own customer lists; the operator confirms each. (P)
- **FR-22** Item ownership is unique per tenant-visible item. When two ERPs report the same item, the item is flagged to the operator and not published until resolved. (P)

### 3.7 ERP integration (Q1 = C, Q5 = D, Q6 = D)
- **FR-23** MVP ERPs are Odoo and ERPNext, each with multiple instances.
- **FR-24** Integration is over each ERP's REST APIs, with an adapter seam so other protocols can be added later.
- **FR-25** Mapping between the canonical model and each ERP's native format is declarative: field maps (source path, target path, type conversion, value lookups) plus a small set of named transform functions. No template or transformation language. (D)
- **FR-26** Connection details are configuration: endpoint, authentication, pagination, rate limits and capability flags. ERP credentials are stored per connection, encrypted, and managed by the operator. (Q5, P)
- **FR-27** Adding an ERP means configuration, mappings, fixtures and a passing conformance suite, targeting days rather than months. (Q16 = D)
- **FR-28** ERP changes are ingested by polling or ERP-side events, translated to canonical events and applied to the platform's read model.

### 3.8 Reliability of delivery (Q7 = A, Q17 = A)
- **FR-29** Guaranteed delivery: an accepted order is durably queued and retried with backoff until it succeeds or is rejected by the ERP. An ERP outage never loses an order.
- **FR-30** Processing is idempotent under at-least-once delivery, ordered per order, published through a transactional outbox, and failures go to a dead-letter path visible to the operator. (P)
- **FR-31** Reads are served from the platform's own read model, not directly from an ERP. (Q7, D)

### 3.9 Webhooks and delivery log
- **FR-32** Tenants register and manage webhook endpoints (create, update, pause, resume, deactivate). Webhook requests are signed. (D for endpoints, P for signing)
- **FR-33** A delivery log records each webhook: canonical payload, status, attempts and timestamps, with replay. It is visible in the UI and API and contains no ERP identity. (D)

### 3.10 User interfaces (Q8 = C, Q13 = A)
- **FR-34** Reseller web UI (React): order list and detail with status timeline, delivery log, webhook endpoint management.
- **FR-35** Operator admin UI: tenants, OAuth clients, connections, mappings, item ownership and conflicts, customer bindings, raw ERP errors, audit trail.
- **FR-36** UIs follow the ERP Platform design system (Claude Design artifact: https://claude.ai/artifact/NpEvLYzy99C4C1ishLaM4d) and the proposed screen designs in `design/` (see `design/README.md`; canvas: https://claude.ai/artifact/6eBqj5D5HxF6heLE2DKkqy). Reseller screens must not show ERP identity (FR-19).

### 3.11 Operator administration
- **FR-37** Onboarding a reseller creates the tenant, its OAuth app client in Amazon Cognito through the Cognito Identity Provider API (client_credentials for M2M) with the tenant identifier issued as a token claim, its bindings and any item ownership. (P)
- **FR-38** Every administrative change is recorded with who, what, when and before/after values. (SECURITY-13)

### 3.12 Development and testing
- **FR-39** The entire stack runs locally in containers with a single-command start. No cloud account is needed for local work or tests. (D)
- **FR-40** A seed tool creates fictional customers, items, connections, tenants and bindings on non-production ERPs only, is repeatable, tags what it creates, can remove exactly that, and refuses any target outside an allow-list. (D)

---

## 4. Non-Functional Requirements

### 4.1 Priorities and scale
- **NFR-01** Top priority is reliability and guaranteed delivery of orders to ERPs (Q17 = A).
- **NFR-02** Expected scale is moderate: hundreds to low thousands of orders per day (Q18 = B). This is an assumption to revisit (O-05).
- **NFR-03** Extensibility: a new ERP or data type is added by configuration and mapping, not by writing a connector (Q16).
- **NFR-04** No explicit latency or throughput targets have been given (O-06).
- **NFR-12** Infrastructure resilience is deliberately MVP-level (backup and restore, single region). Application-level reliability is not reduced: a durable queue (Amazon SQS FIFO), retry with backoff, idempotent processing and a transactional outbox remain required (NFR-01).

### 4.2 Technology and deployment (see Section 5)
- **NFR-05** AWS-native rule (replaces the retired portable-core rule, 2026-09-21): the platform targets AWS-managed services (Amazon Cognito, SQS/SNS, RDS PostgreSQL) and application code MAY call AWS APIs, isolated behind interfaces to keep the domain unit-testable. Local development uses the Floci AWS emulator for Cognito/SQS/SNS plus a real PostgreSQL container. The emulator is a convenience and is NOT authoritative for security-critical behavior: the authentication/token path MUST be validated against real Cognito in a dev AWS account (see Testing, AC-13/AC-15). (D)
- **NFR-06** Configuration is delivered as environment variables: injected from AWS Secrets Manager by ECS in AWS, from a git-ignored `.env` file locally (pointed at Floci). AWS access uses task IAM roles in AWS (no static keys) and dummy credentials against Floci locally. ERP credentials are AES-GCM encrypted in PostgreSQL with a key from Secrets Manager/KMS and a stored key identifier for rotation. (D, P)
- **NFR-07** Structured logging, metrics and traces via OpenTelemetry, with a correlation identifier on every request and message.
- **NFR-08** UI accessibility: text contrast at least 4.5:1 and control borders at least 3:1 in light and dark themes, as in the design system.
- **NFR-09** Developer experience: one-command local environment, hot reload, and integration tests that start their own containers.

### 4.3 Security (Q19 = A, blocking)
| Rule | Project requirement |
|---|---|
| SECURITY-01 | Encrypt at rest and in transit (TLS 1.2+) for RDS PostgreSQL, SQS/SNS, backups, Terraform state and any bucket. Managed keys (KMS). |
| SECURITY-02 | Access logging on the ALB to an encrypted, private log store. |
| SECURITY-03 | Structured logs with timestamp, correlation ID, level and message, centralized. No ERP credentials, tokens or PII in logs. |
| SECURITY-04 | Security headers on all HTML endpoints (CSP, HSTS, nosniff, frame options, referrer policy), including the UI container and the Cognito Hosted UI. The UI self-hosts scripts and fonts. |
| SECURITY-05 | Validate every GraphQL input: types, lengths, formats, list sizes. Enforce request size, query depth and complexity limits. Parameterized queries only. |
| SECURITY-06 | Least-privilege IAM per task role, no wildcard actions or resources, scoped trust policies. |
| SECURITY-07 | Deny-by-default networking. ECS tasks and RDS in private subnets; reach SQS/SNS/Cognito via VPC endpoints or egress-controlled paths. The only public inbound is the ALB on 80/443. Cognito is managed via IAM, with no self-hosted admin console. |
| SECURITY-08 | Deny by default. Object-level checks tie every record to the calling tenant, preventing cross-tenant access by ID. Admin routes require role checks. CORS allow-list. Validate the token on every request (signature, expiry, audience, issuer). |
| SECURITY-09 | No default or static credentials (AWS access via IAM roles). Generic production errors. Current supported runtime versions. No sample apps deployed. |
| SECURITY-10 | Committed lock files, dependency vulnerability scanning in CI, SBOM for production, pinned base images and tools, no `latest` tags. |
| SECURITY-11 | Security-critical logic (authorization, credential encryption) in dedicated modules. Rate limiting on public endpoints. Misuse cases: cross-tenant access, ERP identity inference through errors or IDs, webhook replay, item-ownership manipulation. |
| SECURITY-12 | Amazon Cognito enforces password policy, MFA for admin accounts, session/token expiry and logout, and advanced-security (compromised-credential and adaptive-risk) protection. No hardcoded secrets; Secrets Manager is the store, injected as environment variables. |
| SECURITY-13 | Safe deserialization of ERP and webhook input, verified artifacts, SRI for any external script, audited admin changes with before/after values. |
| SECURITY-14 | Alerts on authentication failures, authorization failures and privilege changes. Log retention of at least 90 days, tamper-evident, and application roles cannot delete logs. Operational and security dashboards. |
| SECURITY-15 | Explicit error handling on every external call, global error handler, fail closed, resources released on error paths, generic user-facing errors. |

### 4.4 Resiliency (Q20 = A, blocking)
| Rule | Project requirement | Status |
|---|---|---|
| RESILIENCY-01 | Classify `api`, `worker`, RDS PostgreSQL, Cognito and SQS/SNS as Critical and the UI as High; document business impact and dependencies. Cognito and SQS/SNS are AWS-managed (multi-AZ by default). | Proposed, confirm |
| RESILIENCY-02 | MVP targets (proposed, confirm): internal availability target 99.5% with no contractual SLA; RTO 4 hours; RPO 15 minutes using RDS point-in-time recovery. Strategy: Backup and Restore. | Decided at MVP level (Q22 = A) |
| RESILIENCY-03 | Lightweight process: change record, approval, rollback note. No existing organizational process assumed. | Decided (Q24 = B) |
| RESILIENCY-04 | A CI/CD pipeline proposed for Terraform and JVM/Spring Boot containers; rollback by redeploying the previous version; rolling deployment. | Decided (Q25 = B, Q26 = A, Q27 = B) |
| RESILIENCY-05 | Metrics, structured logs, distributed traces and a health dashboard. | Requirement captured |
| RESILIENCY-06 | Shallow and deep health checks (database, SQS reachability, Cognito JWKS) wired to ALB health checks. | Requirement captured |
| RESILIENCY-07 | Alarms for resiliency degradation (single-zone operation, backup failure, consumer lag, retry backlog); capacity monitoring. | Requirement captured |
| RESILIENCY-08 | Single region, multi-zone: `api` and `worker` tasks in 2 or more zones, RDS Multi-AZ. SQS, SNS and Cognito are regional AWS-managed services (multi-AZ by default). Moving identity to Cognito removes the Keycloak zone-redundancy concern (O-10 closed). | Decided (Q23 = A) |
| RESILIENCY-09 | ECS auto-scaling with minimum and maximum limits; identify service quotas. | Requirement captured |
| RESILIENCY-10 | Timeouts on every external call, circuit breakers and bulkheads per ERP connection. Degraded mode: reads continue from the read model when an ERP is down. | Requirement captured |
| RESILIENCY-11..13 | Backup and Restore: automated encrypted RDS backups with point-in-time recovery, retention policy, periodic test restore, and a runbook to redeploy from Terraform and restore. Outbox retention to allow republishing to SQS (validate in Application Design). | Requirement captured |
| RESILIENCY-14 | Resiliency testing approach. | Asked at NFR Design |
| RESILIENCY-15 | Lightweight incident response and post-incident review process; alerts route to it. | Decided (Q28 = B) |

### 4.5 Property-based testing (Q21 = A, blocking)
- **NFR-10** Framework: jqwik with JUnit 5 (P, confirm at NFR Requirements). Shrinking enabled, seed logged on every run, PBT runs in CI. Reusable domain generators. Example-based tests also pin every business-critical path.
- **NFR-11** Candidate properties, to be formalized in Functional Design:
  - Round-trip: canonical to ERP-native to canonical for each ERP (documenting lossy fields); event and payload serialization; credential encryption and decryption.
  - Idempotence: reprocessing the same command or event, outbox relay, webhook delivery de-duplication.
  - Invariants: one order maps to one connection; routing is deterministic for the same inputs; binding and item-ownership uniqueness; order totals and currency consistency.
  - Stateful: the order lifecycle state machine compared to a simple model over random command sequences.

---

## 5. Technology Decisions
| Area | Decision | Source |
|---|---|---|
| Backend | Java 21 + Spring Boot (Spring for GraphQL, Spring Web, Spring Security) | Q12 = X (Java/Spring Boot; changed 2026-09-21, was D) |
| Build | Gradle (multi-module), JVM container images | Q12 = X |
| Frontend | React | Q13 = A |
| Cloud | AWS | Q14 = A, D |
| Compute | ECS Fargate containers: `api`, `worker`, `ui` (modular monolith, two deployables plus UI). No Keycloak container — identity is managed Cognito. | P |
| Datastore | PostgreSQL (RDS) with row-level tenant isolation (kept; DynamoDB rejected — relational domain with uniqueness and transactional needs). Aurora Serverless v2 (PostgreSQL) is the serverless upgrade path. | Q15 = C, P |
| Messaging | Amazon SQS FIFO (MessageGroupId = order ID for per-order ordering) with SNS fan-out to per-consumer queues; transactional outbox; native dead-letter queue + redrive | D (SQS chosen 2026-09-21, was Kafka/MSK) |
| Identity | Amazon Cognito (OIDC): user pool + app clients; client_credentials for M2M, authorization-code for UI; tenant identifier as a token claim; app validates standard JWTs | D (Cognito chosen 2026-09-21, was Keycloak) |
| Edge | ALB only; no API gateway, WAF or CloudFront in the MVP; rate limiting in the API | D |
| Infrastructure as code | Terraform (run through a container) | D |
| Configuration | Environment variables (Secrets Manager via ECS in AWS; `.env` locally); AWS access via task IAM roles; ERP credentials encrypted in PostgreSQL (key from Secrets Manager/KMS) | D, P |
| Observability | OpenTelemetry to CloudWatch/X-Ray in AWS, Jaeger or Grafana locally | P |
| Local environment | Docker Compose: real PostgreSQL, Floci (emulates Cognito/SQS/SNS; pinned `floci/floci` image), mock ERP, optional Odoo and ERPNext profile. Auth/token path verified against real Cognito in a dev AWS account. | D, P |
| Local AWS emulation | Floci (LocalStack-style AWS emulator) for Cognito/SQS/SNS and Terraform smoke-tests; not authoritative for security-critical behavior | D (2026-09-21) |
| Testing | JUnit 5, jqwik (property-based), Testcontainers; tiers: unit, integration, ERP conformance, post-deploy smoke test in a dev AWS account | P |
| Persistence | Spring Data JPA / Hibernate (or jOOQ), Flyway migrations | P |

---

## 6. Assumptions and Constraints
- The product is standalone; no code, service or data is shared with any other system.
- The ERPs belong to the operator, so a tenant's ERP is never visible or chosen by the tenant.
- Customers already exist in the ERPs; the platform only binds to them.
- Items are not split across ERPs, and an order has one ERP for life.
- Q19-Q21 extension opt-ins were entered as answers in the questionnaire on the user's behalf and should be confirmed.

## 7. Open Items and Pending Decisions
| ID | Item | Blocks |
|---|---|---|
| O-01 | RESOLVED (Q29 = A): orders with items owned by different ERPs are rejected at Validated with a reseller-safe message. See FR-18, AC-04. | Closed |
| O-02 | RESOLVED (Q30 = A): items are read-only for tenants. See FR-10. | Closed |
| O-03 | Confirm the MVP-level resiliency answers (Q22-Q28), which were filled in on the instruction "MVP, not too much resilience". Change Q24, Q25, Q28 to A if the organization has existing processes. | Confirmation only |
| O-04 | Whether every reseller already has a customer record in each ERP it will buy from. | Onboarding plan |
| O-05 | Q18 scale is an assumption; real volume and number of tenants and ERP instances unknown. | NFR Requirements |
| O-06 | Latency, throughput and availability (SLA) targets. | NFR Requirements |
| O-07 | Whether the lifecycle label "Sent to ERP" may be shown to resellers, since it reveals that an ERP exists. | Functional Design |
| O-08 | Webhook signing scheme and retention period for the delivery log. | Application Design |
| O-09 | Order update and cancel rules per lifecycle state. | Functional Design |
| O-10 | RESOLVED (2026-09-21): identity moved to Amazon Cognito (AWS-managed, multi-AZ), so the Keycloak single-instance zone-redundancy concern no longer applies. | Closed |
| O-11 | Consider opting out of the Resiliency extension (Q20 = B) if the MVP should not carry its blocking rules (multi-zone compute, DR runbooks). Application-level reliability stays as NFR-01 either way. | User decision |

## 8. Extension Compliance at This Stage
- **Security Baseline**: enabled. Requirements for SECURITY-01 to 15 are captured (Section 4.3). Design-level and infrastructure-level verification happens in later stages. No blocking finding at this stage.
- **Resiliency Baseline**: enabled. No blocking findings at this stage: the decisions required by RESILIENCY-02, 03, 04, 08 and 15 are recorded at MVP level (Q22-Q28) and marked for confirmation. RESILIENCY-14 is asked at NFR Design. O-10 is now closed (identity moved to managed Cognito).
- **Property-Based Testing**: enabled (full). Framework proposed (PBT-09); property identification (PBT-01) happens in Functional Design. No blocking finding at this stage.

## 9. Traceability
| Questionnaire | Answer | Requirements |
|---|---|---|
| Q1 | C (Odoo + ERPNext) | FR-23 |
| Q2 | A | FR-08 to FR-11 |
| Q3 | C | FR-09 (orders: full CRUD), FR-10 (items read-only, Q30), FR-11 (customers read-only) |
| Q4 | B | FR-12 to FR-15 |
| Q5 | D | FR-25, FR-26, FR-27 |
| Q6 | D | FR-24 |
| Q7 | A | FR-07, FR-29, FR-31 |
| Q8 | C | FR-03, FR-05, FR-34, FR-35 |
| Q9 | C | FR-01, FR-02 |
| Q10 | C | FR-17 |
| Q11 | B | FR-03, SECURITY-08, SECURITY-12 |
| Q12 | X (Java/Spring Boot; changed 2026-09-21, was D=.NET) | Section 5 |
| Q13 | A | FR-34, FR-35, Section 5 |
| Q14 | A | Section 5, NFR-05 |
| Q15 | C | Section 5 |
| Q16 | D | FR-27, NFR-03, Section 2.4 |
| Q17 | A | NFR-01, FR-29 |
| Q18 | B | NFR-02, O-05 |
| Q19 | A | Section 4.3 |
| Q20 | A | Section 4.4 |
| Q21 | A | Section 4.5 |
| Q22-Q28 | A, A, B, B, A, B, B | Section 4.4, NFR-12 |
| Q29 | A (reject mixed-ERP orders at Validated) | FR-18, AC-04 |
| Q30 | A (items read-only for tenants) | FR-10 |

---

## 10. Acceptance Criteria
- **AC-01 (FR-01)** Given a valid token for tenant A, when a request carries another tenant's identifier in its body or parameters, then that identifier is ignored and only tenant A's data is returned.
- **AC-02 (FR-19)** Given any reseller-facing response, error, webhook, delivery-log entry or UI screen, when inspected, then it contains no ERP name, instance or ERP record identifier.
- **AC-03 (FR-14, FR-16, FR-17)** Given an order whose items are all owned by one connection and a tenant with a binding for it, when the order is validated, then it is bound to that connection and the binding never changes afterwards.
- **AC-04 (FR-18)** Given an order with items owned by different ERPs, when it is validated, then it is rejected with a reseller-safe message and no ERP is called.
- **AC-05 (FR-20)** Given an existing binding, when the operator creates a second binding for the same (tenant, connection), or the same ERP customer for another tenant, then the request is refused.
- **AC-06 (FR-22)** Given two ERPs reporting the same item, when items are synchronized, then the item is flagged to the operator and not published to tenants.
- **AC-07 (FR-29)** Given the owning ERP is unavailable, when an order is submitted, then it is accepted, shown as Retrying, and delivered once the ERP returns.
- **AC-08 (FR-30)** Given a message is delivered twice, when it is processed, then only one record results in the ERP and the read model.
- **AC-09 (FR-15)** Given the ERP changes an order's status, when the change is ingested, then the mapped lifecycle state is visible by query and delivered by webhook.
- **AC-10 (FR-31)** Given an ERP is down, when a tenant queries orders, items or the delivery log, then the queries still succeed from the read model.
- **AC-11 (FR-32, FR-33)** Given a webhook endpoint fails, when delivery is attempted, then attempts are retried, recorded in the delivery log, signed, and can be replayed.
- **AC-12 (FR-25, FR-27)** Given a new ERP is added with configuration, mappings and fixtures, when the conformance suite runs, then it passes without changes to core code beyond registered transform functions.
- **AC-13 (FR-39)** Given a fresh clone, when the single start command is run, then the full stack starts in containers and integration tests pass without a cloud account.
- **AC-14 (FR-40)** Given a target outside the allow-list, when the seed tool runs, then it refuses. Given an allowed target, running it twice creates no duplicates and its reset removes only what it created.
- **AC-15 (SECURITY-08)** Given an unauthenticated request, or a token that is expired or from the wrong issuer, when any endpoint is called, then it is rejected. Given a tenant token, when an admin operation is called, then it is refused.
- **AC-16 (NFR-01)** Given the worker crashes while processing an accepted order, when it restarts, then the order is completed with no loss and no duplicate.
- **AC-17 (NFR-10)** Given the CI pipeline, when it runs, then property-based tests run with their seed logged, and every business-critical path also has an example-based test.