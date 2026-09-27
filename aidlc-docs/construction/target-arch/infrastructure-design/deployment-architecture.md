# Deployment Architecture — Target Architecture (Phase 3)

## Local (floci) — the full async E2E you can run on a laptop
```mermaid
flowchart TB
  subgraph HOST["Developer machine (docker compose)"]
    PG[("postgres:16 (portal DB)")]
    FLOCI["floci :4566 (SNS/SQS/Secrets)"]
    ODOO["odoo:17 :8069"]
    API["api container :8000 (GraphQL + webhooks)"]
    WORKER["worker container (consumers + relay + scheduler)"]
  end
  TF["terraform apply (use_floci=true)"] --> FLOCI
  API -->|"append events+outbox (1 tx)"| PG
  WORKER -->|"relay: outbox -> SNS"| FLOCI
  FLOCI -->|"SQS FIFO"| WORKER
  WORKER -->|"submit / poll"| ODOO
  ODOO -->|"webhook -> POST /erp/webhook/{conn}"| API
  WORKER -->|"projections"| PG
  API -->|"queries (read models)"| PG
```
Bring-up: `docker compose up -d` → `terraform -chdir=infra/terraform apply -var-file=envs/local.tfvars` → `alembic upgrade head` → `python -m scripts.seed_demo` → api+worker containers start → configure Odoo Automation Rule.

## AWS (production)
```mermaid
flowchart TB
  U["Reseller / Operator SPAs"] --> ALB["ALB (443)"]
  ALB --> COG["Cognito (JWT)"]
  ALB --> APIF["ECS Fargate: api"]
  APIF --> AUR[("Aurora Serverless v2 Postgres")]
  APIF --> SNS["SNS FIFO topic"]
  WRK["ECS Fargate: worker"] --> AUR
  SNS --> SQS["SQS FIFO queues + DLQ"]
  SQS --> WRK
  WRK --> ERP["Odoo / ERPNext"]
  ERP --> ALB
  SCH["EventBridge Scheduler"] --> WRK
  APIF --> SM["Secrets Manager + KMS"]
  WRK --> SM
  ALLLOGS["CloudWatch / OTel / X-Ray"]
```
Provisioned by Terraform (`use_floci=false`): VPC + private subnets, Aurora, ECS cluster/services/task-defs, ALB + target groups, Cognito user pools + app clients, SNS/SQS, Secrets Manager, IAM roles, ECR, CloudWatch log groups, EventBridge Scheduler.

## Parity: what changes local → prod
| Concern | Local (floci) | AWS |
|---|---|---|
| Messaging | floci SNS/SQS via `AWS_ENDPOINT_URL` | real SNS/SQS |
| Secrets | floci Secrets Manager | Secrets Manager + KMS |
| DB | postgres container | Aurora Serverless v2 |
| Compute | api/worker containers | ECS Fargate |
| Ingress | api :8000 direct | ALB :443 |
| Identity | JWT/header stub | Cognito |
| Provisioning | `terraform … local.tfvars` | `terraform … aws.tfvars` |

Only endpoints + credentials + the AWS-only module toggle differ — application code is identical (ports + `AWS_ENDPOINT_URL`).
