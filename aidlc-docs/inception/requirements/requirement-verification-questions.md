# Requirements Clarification Questions — ERP & Supply Chain Order Portal

Please answer each question by filling in the letter choice after the `[Answer]:` tag. If none of the options match, choose the "Other" option and describe your preference after the tag. Answer as many as you can; where you're unsure, pick the option closest to your intent and I'll refine.

---

## Section A — Scope & MVP Definition

## Question 1
You mentioned starting with **two ERPs**. Which two should the MVP prove out first?

A) SAP + Odoo

B) SAP + ERPNext

C) Odoo + ERPNext

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 2
You mentioned **four kinds of business data**. Which four should the MVP support? (Pick the set closest to your intent.)

A) Sales Orders, Purchase Orders, Products/Items, Customers

B) Sales Orders, Invoices, Products/Items, Inventory/Stock

C) Sales Orders, Purchase Orders, Customers, Suppliers/Vendors

D) Sales Orders, Products/Items, Customers, Inventory/Stock

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
What operations should external clients perform on these business data types in the MVP?

A) Create only (place orders, submit records)

B) Create + Read (place orders and check status/details)

C) Full CRUD (create, read, update, cancel)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
For the "order management workflow", what is the core lifecycle you want to model in the MVP?

A) Simple: Order Placed → Sent to ERP → Confirmed/Rejected

B) Standard: Draft → Submitted → Validated → Sent to ERP → Confirmed → Fulfilled → Closed

C) Advanced: Standard plus approvals, holds, partial fulfillment, returns

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Section B — The "No Connectors" Vision

## Question 5
The heart of your vision is routing to ERPs "without writing integrators/connectors". Which approach best matches what you mean?

A) Configuration-driven adapters — a generic engine reads per-ERP config/metadata (endpoints, field mappings, auth) so onboarding a new ERP means writing config, not code

B) Canonical model + declarative mapping — clients speak one canonical API; declarative transformation rules map canonical data to each ERP's native format

C) Plugin/registry model — thin per-ERP plugins conforming to a standard interface, discoverable at runtime

D) A combination: canonical API + declarative mappings + config-driven connection details

X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 6
How should the portal communicate with each ERP's native API?

A) REST/HTTP APIs (SAP OData, Odoo JSON-RPC/REST, ERPNext REST)

B) Message queue / event-based where supported, REST otherwise

C) File/batch (CSV, IDoc, flat files) for some ERPs

D) Mix — REST primary, with adapters able to support others later

X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 7
When the target ERP is temporarily unavailable, how should the portal behave?

A) Queue the request and retry automatically until it succeeds (asynchronous, guaranteed delivery)

B) Reject immediately and let the client retry (synchronous)

C) Configurable per data type — some async/queued, some synchronous

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Section C — Clients, Access & Multi-Tenancy

## Question 8
Who are the "external clients" and how do they interact with the portal?

A) Business users via a web UI

B) Partner systems via an API (machine-to-machine)

C) Both — web UI for humans and API for system integrations

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 9
How should tenancy / client isolation work, given each ERP can have multiple instances?

A) Multi-tenant — one client can be routed to a specific ERP instance based on their configuration

B) Each client is bound to exactly one ERP instance

C) A client may place orders across multiple ERP instances (routing decided per request)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 10
How should a request be routed to a specific ERP **instance** (e.g., which SAP system)?

A) Determined by the authenticated client's configuration/profile

B) Specified explicitly in each request (client names the target)

C) Rule-based routing (region, product line, order type, load, etc.)

D) Combination of client config with optional per-request override

X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 11
How should external clients authenticate to the portal?

A) API keys

B) OAuth 2.0 / OpenID Connect (tokens)

C) Both API keys (M2M) and OAuth/OIDC (users)

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Section D — Technology & Deployment

## Question 12
Do you have a preferred technology stack for the backend?

A) Java (Spring Boot)

B) Python (FastAPI / Django)

C) Node.js / TypeScript (NestJS / Express)

D) .NET (C#)

X) Other / no preference — recommend one for me

[Answer]: X - Java with Spring Boot (changed 2026-09-21 by user decision; was D = .NET). Rationale: richest integration ecosystem (Spring for GraphQL, Spring Kafka, Apache Camel), Keycloak and Testcontainers are JVM-native, and jqwik covers property-based testing.

## Question 13
If a web UI is needed, do you have a frontend preference?

A) React

B) Angular

C) Vue

D) No UI needed in MVP (API only)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
What is the target deployment environment?

A) AWS (cloud)

B) Azure

C) Google Cloud

D) On-premises / self-hosted (containers, Kubernetes)

X) Other / no preference — recommend one for me

[Answer]: A

## Question 15
What datastore preference do you have for portal state (orders, mappings, config, audit)?

A) Relational (PostgreSQL / MySQL)

B) NoSQL document (MongoDB / DynamoDB)

C) Relational for core data + a message broker for async routing (e.g., PostgreSQL + Kafka/RabbitMQ/SQS)

D) Other / no preference — recommend one for me

[Answer]: C

---

## Section E — Growth & Future-Proofing

## Question 16
Your goal is "adding the next ERP takes days, not months." Which capability matters most for the MVP foundation? (This guides how much we invest early.)

A) A clean canonical model + adapter interface, even if onboarding still needs a developer

B) Self-service, config-driven onboarding (customers/admins add an ERP via UI/config, no code)

C) Automated cross-system workflows (e.g., order in one ERP triggers action in another)

D) Prioritize A now; B and C are explicitly future phases

X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 17
What are the most important non-functional priorities for the MVP? (Choose the top priority; others can still be addressed.)

A) Reliability & guaranteed delivery of orders to ERPs

B) Extensibility (ease of adding new ERPs and data types)

C) Security & tenant isolation

D) Performance & throughput (high order volume)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 18
Is there an expected scale for the MVP that should shape the design?

A) Low — proof of concept, tens of orders/day, a handful of clients

B) Moderate — hundreds to low thousands of orders/day

C) High — tens of thousands+ orders/day from many clients

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Section F — Extension Opt-Ins (AIDLC)

## Question 19: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 20: Resiliency Extensions
Should the resiliency baseline be applied to this project?

**What this extension is.** Enabling it applies a set of directional, design-time best practices for building resilient systems, derived from the AWS Well-Architected Framework (Reliability Pillar). It steers requirements, design, and code toward fault tolerance, high availability, observability, and recoverability.

**What this extension is NOT.** It does not make your workload production-ready, nor certify any availability/RTO/RPO target. It is a starting point, not a substitute for a formal review.

A) Yes — apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads)

B) No — skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 21: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)

C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Additional Clarifications (from user discussion)

These extend the letter answers above. Where a clarification is more specific than a letter answer, the clarification applies.

### Confirmed by the user
- **Standalone product.** Not related to any existing system; nothing is reused from other codebases or services.
- **Actors.** The user is the platform operator (admin) and onboards tenants, ERP connections and mappings. A tenant is a reseller (one level; no separate end-client layer).
- **Consumers.** Resellers consume the platform APIs directly, GraphQL preferred (Q8). A web UI lets a reseller see the data that was sent to their system (delivery log). The operator has a separate admin UI.
- **ERPs are operator-owned and hidden from tenants.** A reseller must never learn which ERP or instance served their data. Routing is decided by the platform (Q10 = C), never by the reseller.
- **A tenant can be served by several ERPs and several instances** (Q9 = C).
- **One order = one ERP.** A sales order and all its status movements come from a single ERP. Orders are not split, and items are not split across ERPs (each item is owned by exactly one ERP).
- **Customers already exist in the ERPs.** The platform does not create ERP customers in production. A dev/test seed script may create fictional customers, items and bindings, restricted to non-production targets.
- **Deployment on AWS** (Q14 = A), not Azure.
- **Fixed output payload.** Reseller-facing payloads (API responses, webhooks) have one canonical shape for every tenant. There are no per-tenant output templates and no template/transformation language such as JSONata. Mapping between each ERP's native format and the canonical model is still required inside the platform.
- **Technology:** Java with Spring Boot (Q12 changed to X on 2026-09-21; was D = .NET), Terraform for infrastructure as code, Amazon SQS FIFO + SNS for async messaging (chosen 2026-09-21, was Apache Kafka/MSK), Amazon Cognito as the OAuth 2.0 / OIDC identity provider (chosen 2026-09-21, was Keycloak). AWS-native direction; Floci emulates AWS services for local development.
- **Local development:** everything runs in containers, with a smooth single-command developer experience and no dependency on a cloud account for local work or tests.
- **MVP scope:** no API gateway, WAF or CloudFront. An ALB fronts the containers and rate limiting lives in the API. Configuration comes from environment variables, not a secrets provider.

### Proposed design direction (confirm in Application Design)
- Map each reseller to its existing ERP customer with a binding per (tenant, ERP connection), created by the operator and verified against the ERP. Uniqueness: one binding per (tenant, connection), and an ERP customer belongs to at most one tenant.
- Route an order by the ERP that owns its items. Resolve routing once, at the Validated stage, and keep it for the life of the order.
- Reseller-facing surfaces (API, errors, webhooks, delivery log, UI) never expose ERP names, instances, or ERP record IDs. Use a separate public schema from the operator/admin schema and sanitize ERP errors into canonical codes.
- Ensure one owner per item: detect the same item reported by two ERPs and flag it to the operator instead of publishing it.
- Customers (Q2) are read and linked only. Creating or updating ERP customers is out of scope (Q3 applies to orders and items).
- Use Amazon Cognito as the OIDC provider (user pool + app clients), emulated locally via Floci and real in AWS. The API validates standard OIDC JWTs (signature/JWKS, issuer, audience, expiry). The operator admin flow creates each reseller app client through the Cognito Identity Provider API, with the tenant identifier issued as a token claim. (Changed 2026-09-21, was Keycloak.)
- Local stack with Docker Compose: real PostgreSQL, Floci (emulates Cognito/SQS/SNS), a mock ERP, and an optional profile with real Odoo and ERPNext. Use Testcontainers so integration tests start their own containers (Postgres real; AWS services via Floci). (Changed 2026-09-21, was Kafka/Keycloak containers.)
- Messaging (Amazon SQS FIFO + SNS, changed 2026-09-21 from Kafka): MessageGroupId = order ID for per-order ordering; publish through a transactional outbox in PostgreSQL; SQS gives native per-message redelivery (visibility-timeout backoff) and a native dead-letter queue with redrive (Q7 = A); SNS fans out to a per-consumer SQS queue (ERP delivery, webhook dispatch, read-model projection).
- Terraform layout with shared modules and one environment folder per stage, run through a container for reproducibility. Floci used for local Terraform/AWS smoke-tests.
- Modular monolith: two deployables (API and worker) plus a UI container. Split further only when a real need appears.
- AWS-native rule (replaces the retired portable-core rule, 2026-09-21): the platform targets AWS-managed services (Cognito, SQS/SNS, RDS PostgreSQL); application code MAY call AWS APIs, isolated behind interfaces for testability. Platform settings are environment variables (injected from Secrets Manager by ECS in AWS, from a git-ignored .env pointed at Floci locally); AWS access uses task IAM roles. ERP connection credentials are stored encrypted in PostgreSQL (AES-GCM, key from Secrets Manager/KMS, key ID stored with the ciphertext). The Floci emulator is a convenience and is not authoritative for security-critical behavior; the auth/token path is validated against real Cognito in a dev AWS account.
- Serve the UI from a container (not S3/CloudFront), keep payload and delivery logs in PostgreSQL, and run ERP polling with an in-app scheduler.
- Test tiers: unit tests with no containers; integration tests with Testcontainers; ERP conformance tests against real Odoo and ERPNext containers; a post-deploy smoke test in a dev AWS account.

### Open items
- Handling of an order that contains items owned by different ERPs (proposed: reject at Validated with a reseller-safe message).
- Q18 (scale) is an assumption; revise if the real volume is a small pilot.
- Whether every reseller already has a customer record in each ERP it will buy from.
- Whether the lifecycle label "Sent to ERP" (Q4) is acceptable to show resellers, since it reveals that an ERP exists.

---

## Section G — Resiliency Follow-up Questions (required by the Resiliency extension)

MVP context: the user said, "We are building MVP so I dont expect Too much resilience." The answers below are the lightest options that still satisfy the Resiliency extension. They were filled in on that instruction and can be changed.

- Q22 = A: Backup and Restore. RDS automated backups with point-in-time recovery; redeploy from Terraform.
- Q23 = A: single region, multi-zone.
- Q24, Q25, Q28 = B: no existing organizational process is assumed; a lightweight one is proposed. Change to A and name the process if your organization already has one.
- Q26 = A, Q27 = B: roll back by redeploying the previous version; rolling deployment (the ECS default).

## Question 22: RTO/RPO Goals and Disaster Recovery Strategy
What are your Recovery Time Objective (RTO) and Recovery Point Objective (RPO) goals? These determine the appropriate Disaster Recovery strategy and infrastructure redundancy level.

A) RPO/RTO: Hours — Backup & Restore strategy. Lowest cost. Data backed up, no services deployed; redeploy from IaC and restore from backups on failure.

B) RPO/RTO: 10s of minutes — Pilot Light strategy. Data live, services idle; scaled up on failover.

C) RPO/RTO: Minutes — Warm Standby strategy. Data live, services run at reduced capacity; scaled up during failover.

D) RPO/RTO: Near real-time — Multi-site Active/Active strategy. Highest cost; live services in multiple regions.

E) N/A — Single-region deployment is acceptable, no cross-region DR needed. Rely on multi-zone availability within one region.

X) Other (please describe after [Answer]: Atag below)

[Answer]: A

## Question 23: Regional Topology
Does this workload require multi-region deployment, or is single-region with multi-zone redundancy sufficient?

A) Single-region, multi-zone — tolerates zone failure, not full-region failure. Lower cost.

B) Multi-region active-passive — survives region failure with failover. Higher cost.

C) Multi-region active-active — survives region failure with no downtime. Highest cost.

X) Other (describe after [Answer]: Atag below)

[Answer]: A

## Question 24: Change Management Process
How should production changes for this workload be governed?

A) Use our existing organizational change management process — provide the name/tool (e.g., ServiceNow, Jira Change, internal CAB).

B) No formal process exists yet — propose a lightweight change management process (change record + approval + rollback note).

C) N/A — this workload is exempt from formal change management. Document the exemption rationale.

X) Other (describe after [Answer]: Btag below)

[Answer]: B

## Question 25: CI/CD and Deployment Tooling
What CI/CD tooling and deployment process should this workload use?

A) Use our existing CI/CD pipeline — provide the tool (e.g., GitHub Actions, GitLab CI, Jenkins, CodePipeline).

B) No pipeline exists — propose a CI/CD pipeline definition appropriate to Terraform and the JVM/Spring Boot container runtime.

X) Other (describe after [Answer]: Btag below)

[Answer]: B

## Question 26: Rollback Mechanism
How should a failed production deployment be rolled back?

A) Redeploy previous IaC/artifact version (version-pinned rollback)

B) Blue/green swap back to the previous environment

C) Canary auto-rollback on health/metric regression

D) Database-aware rollback required (schema/data migration reversal) — flag for explicit design

E) Use our organization's existing rollback procedure — provide reference

X) Other (describe after [Answer]: Atag below)

[Answer]: A

## Question 27: Deployment Style
What deployment strategy is acceptable for this workload's risk profile?

A) Direct / in-place (lowest cost, highest blast radius)

B) Rolling (gradual instance replacement)

C) Blue/green (zero-downtime cutover, higher cost)

D) Canary (progressive traffic shift with automated rollback)

X) Other (describe after [Answer]: Btag below)

[Answer]: B

## Question 28: Incident Response Process
How are production incidents handled for this workload?

A) Use our existing incident response process — provide the reference (e.g., PagerDuty runbooks, internal on-call process).

B) No formal process exists — propose a lightweight incident response and Correction of Errors (COE) process.

X) Other (describe after [Answer]: Btag below)

[Answer]: B

---

## Section H — Functional Follow-up Questions

## Question 29: Orders With Items From Different ERPs
An order normally contains items owned by a single ERP. If a reseller submits an order whose items are owned by different ERPs, what should happen?

A) Reject at the Validated step with a reseller-safe message asking them to order separately (recommended for the MVP)

B) Split into per-ERP sub-orders and show the reseller one order with a combined status

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 30: Item Write Access for Resellers
Can resellers create or update items, or are items read-only for them (synchronized from the ERPs)?

A) Read-only for resellers (recommended for the MVP)

B) Resellers can create and update items

X) Other (please describe after [Answer]: tag below)

[Answer]: A
