# Application Design Clarification

Your answers are internally consistent — this is a confirmation, not a contradiction to resolve. Please fill in the `[Answer]:` tags.

## Clarification 1: Microservices vs the lightweight MVP posture
You chose Q1=B (microservices from day one) and Q2=C (fully async via internal queue/workers). Earlier you set a lightweight PoC posture: Security OFF, Resiliency OFF, moderate volume (hundreds–low thousands of orders/day), Medium risk.

Microservices + async messaging from day one adds operational complexity (inter-service networking, distributed data, message broker, orchestration, distributed failure modes) that normally pairs with a resiliency baseline. I want to confirm the intent.

A) Yes — commit to microservices + async from day one. I accept the added operational complexity; per-ERP/component isolation and future scale justify it. (Keep resiliency OFF for MVP as previously decided.)

B) Actually, reconsider — use a modular monolith with clean boundaries and an internal async queue, designed to extract into microservices later (lower MVP complexity, same end-state path).

C) Microservices from day one AND enable the resiliency baseline after all (revisit that decision), since we're taking on distributed-system complexity.

D) Other (please describe after [Answer]: tag below)

[Answer]: whatever is recommeded

## Clarification 2: Service granularity (only if you keep microservices)
If microservices, how granular for MVP?

A) Coarse-grained: a few services — e.g., Portal/Order service, Integration service (routing + mapping + adapters + async workers), Admin/Config service, Identity. (recommended balance)

B) Fine-grained: a separate service per major component (Order Intake, Routing, Mapping, each Adapter, Lifecycle, Admin, Identity).

C) N/A — I chose modular monolith in Clarification 1.

D) Other (please describe after [Answer]: tag below)

[Answer]: A
