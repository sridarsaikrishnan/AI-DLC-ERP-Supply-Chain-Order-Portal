# Infrastructure Design — U0 Platform Foundation (shared, whole monolith)

All choices are the recommended PoC-appropriate options (Q1=D, Q2=B, Q3=A, Q4=A, Q5=A).

## Service Mapping

| Logical Component | Infrastructure (PoC) | Notes / Future |
|---|---|---|
| App (FastAPI, all modules U0–U4) | Docker container image; 2 replicas | Portable; move to managed container service (ECS/EKS/ACA/GKE) later |
| Job poller / workers | Runs inside each app container (combined API+worker, Q3=A) | SKIP LOCKED prevents double-processing across the 2 replicas |
| PostgreSQL | Containerized Postgres (Q2=B), persistent volume | Swap to managed DB (RDS/Cloud SQL) when going to cloud |
| Queue | DB-backed job table in the same Postgres | First swap-out point for a real broker if volume grows |
| Reverse proxy / entry | Nginx (or Traefik) container in front of the 2 app replicas (Q4=A) | Becomes a managed load balancer in cloud |
| Logging | stdout as JSON, collected by the container platform (Q5=A) | Ship to log aggregation later |
| Metrics | `/metrics` endpoint on each app | Scrape with Prometheus later |
| Health | `/livez`, `/readyz` per replica | Used by orchestrator health checks later |
| Secrets/config | Environment variables / docker-compose env (PoC) | NOTE: Q7=A means credentials may be inline — flagged risk, move to a secrets manager during hardening |

## Deployment Target (Q1=D)
Local, containerized via **docker-compose** for the proof of concept. Cloud provider deliberately deferred (Req D3=D). The compose topology is designed to translate cleanly to a managed container platform later (same images, same env contract).

## Environments
- **Local/PoC**: docker-compose (app x2, postgres, reverse-proxy).
- **Future**: dev/staging/prod on a managed container platform + managed Postgres (out of MVP scope; noted for extensibility).

## Extension Compliance
- Security baseline: DISABLED — N/A (inline secrets accepted per Q7=A, flagged as hardening item).
- Resiliency baseline: DISABLED — N/A (single-region, no failover; basic 2-replica redundancy only).
- PBT (Partial): N/A at infrastructure layer.
