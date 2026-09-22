# Infrastructure Design Plan — U0 Platform Foundation (shared infra for whole monolith)

## Context
U0 defines the shared infrastructure for the entire monolith. Known inputs:
- Stack: Python/FastAPI, PostgreSQL, DB-backed queue, 2 app instances, best-effort availability, logging+metrics+health.
- Deployment target was left undecided earlier (Req D3=D — recommend).
- Lightweight PoC posture (Security/Resiliency baselines OFF).

Answer the `[Answer]:` tags (or "recommend").

## Execution Checklist (artifacts)
- [ ] `infrastructure-design.md` (service mapping for compute, storage, queue, networking, monitoring)
- [ ] `deployment-architecture.md` (topology, environments, how the 2 instances run)
- [ ] `shared-infrastructure.md` (shared infra used across units)

---

## Questions

## Question 1
Deployment target / hosting model (D3 was undecided)?

A) Containers on a managed platform (Docker + a managed container service) — portable, standard (recommended)

B) A single VM / on-prem server running the app + PostgreSQL

C) Serverless (functions) — note: fits awkwardly with a DB-poller worker model

D) Local/containerized for PoC now (docker-compose), decide cloud later (recommended if this is a local proof)

E) Recommend

[Answer]: 

## Question 2
For the PoC, how should PostgreSQL be run?

A) Managed database service (if cloud) 

B) Containerized Postgres alongside the app (simple for PoC)

C) Recommend

[Answer]: 

## Question 3
How should the 2 app instances + worker be arranged?

A) 2 identical app containers each running BOTH API and the job poller/workers (simplest; SKIP LOCKED prevents double-processing) (recommended)

B) Separate API instances and dedicated worker instances (cleaner separation, more moving parts)

C) Recommend

[Answer]: 

## Question 4
Networking / entry point for the PoC?

A) A reverse proxy / load balancer in front of the 2 app instances (recommended)

B) Direct exposure of a single instance for a local PoC; add LB later

C) Recommend

[Answer]: 

## Question 5
Monitoring/logging destination for the PoC?

A) Logs to stdout (collected by the platform) + a lightweight metrics endpoint; wire to a real stack later (recommended)

B) Full monitoring stack now (e.g., Prometheus/Grafana + log aggregation)

C) Recommend

[Answer]: 

---

Fill in the `[Answer]:` tags and let me know when done.
