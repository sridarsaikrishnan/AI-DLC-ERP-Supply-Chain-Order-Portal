# NFR Requirements Plan — U0 Platform Foundation

## Context
U0 is the shared foundation, so its NFRs and tech-stack choices set the baseline for the ENTIRE monolith (all units inherit them). Key drivers from requirements: extensibility (primary), logical multi-tenancy, moderate volume (hundreds–low thousands of orders/day), observability; Security & Resiliency baselines OFF for MVP; PBT partial.

## Execution Checklist (artifacts)
- [ ] `nfr-requirements.md` (scalability, performance, availability, security posture, reliability, maintainability)
- [ ] `tech-stack-decisions.md` (language, framework, datastore, queue, and rationale)

---

## Questions

## Question 1
Primary implementation language/runtime for the monolith?

A) TypeScript / Node.js (good ecosystem for REST + async workers; fast to build)

B) Python (strong for data mapping/transforms; readable DSL evaluation)

C) Java / Kotlin (Spring) (robust for enterprise ERP integration, strong typing)

D) Recommend based on the requirements

E) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
Primary datastore (single shared DB with row-level tenant filtering per D4=B)?

A) PostgreSQL (relational, JSON support for flexible mapping/config)

B) MySQL/MariaDB (relational)

C) MongoDB (document — flexible config/mapping docs)

D) Recommend based on the requirements

E) Other (please describe after [Answer]: tag below)

[Answer]: recommend

## Question 3
Async queue mechanism for MVP (fully async pipeline per earlier decision)?

A) A lightweight broker (e.g., Redis-backed queue) — simple to run for MVP

B) A full message broker (e.g., RabbitMQ/Kafka) — heavier, more future-proof

C) Database-backed job table + poller — fewest moving parts for a PoC

D) Recommend based on the requirements

E) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question 4
Performance targets for MVP (moderate volume)?

A) Submission API responds < 500 ms (enqueue only); ERP fulfillment async within seconds–minutes

B) Submission API < 200 ms; fulfillment async

C) No specific targets for PoC — best effort

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 5
Availability expectation for MVP (resiliency baseline is OFF)?

A) Single-instance, best-effort availability; acceptable brief downtime for a PoC

B) Basic redundancy (2 app instances) but no formal SLA

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
Observability baseline for the foundation?

A) Structured logging + correlation/trace id per request and job (recommended minimum for tracing orders end-to-end, satisfies NFR-5)

B) Logging only (no correlation ids)

C) Logging + metrics + basic health endpoints

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 7
Security posture note: you opted OUT of the security baseline for MVP. For the foundation, do you still want these minimal safeguards?

A) Yes — hash passwords, keep ERP credentials out of the domain model (reference only), and use parameterized queries. Minimal hygiene, not the full baseline. (recommended)

B) No — pure PoC, minimal safeguards not required now

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

Fill in the `[Answer]:` tags and let me know when done. You can answer "recommend" on any question and I'll choose with rationale.
