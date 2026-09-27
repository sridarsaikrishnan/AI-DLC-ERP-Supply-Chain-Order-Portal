# Infrastructure Design — Target Architecture (Phase 3: full E2E)

Maps the logical components (from `application-design/target-architecture.md` and
`messaging-topology.md`) to real infrastructure, provisioned by **Terraform**, runnable
locally on **floci** and deployable to **AWS**. Prior decisions are inherited (single
Postgres, ES on Order, SNS FIFO→SQS FIFO, Cognito, Secrets Manager, ECS Fargate); this
doc fixes the concrete resources and the local↔cloud parity.

## Service → infrastructure mapping
| Logical component | AWS resource | Local (floci/compose) |
|---|---|---|
| `api` host (GraphQL + webhooks) | ECS Fargate service behind ALB | container / uvicorn |
| `worker` host (consumers + relay + scheduler) | ECS Fargate service | container / process |
| Event store + outbox + projections + config | Aurora Serverless v2 PostgreSQL | `postgres:16` container |
| Domain event topic | SNS FIFO `platform-domain-events.fifo` | floci SNS |
| Work queues + DLQs | SQS FIFO ×4 (+4 DLQ) | floci SQS |
| Secrets (Odoo creds, webhook keys) | Secrets Manager + KMS | floci Secrets Manager |
| Identity | Cognito user pools (reseller, operator) | stub / floci (partial) |
| Scheduler (reconcile) | EventBridge Scheduler | worker in-process loop |
| Observability | CloudWatch Logs/Metrics, OTel, X-Ray | stdout + logs |
| ERP | external Odoo/ERPNext | `odoo:17` container |
| Container registry | ECR | local image build |
| Network | VPC, private subnets, SGs, VPC endpoints | compose network |

## What floci provisions vs. what it can't
- **floci-emulated (Terraform, `-var use_floci=true`)**: SNS FIFO, SQS FIFO + DLQs, subscriptions + filter policies, Secrets Manager. This is everything the running app needs locally.
- **AWS-only (Terraform, real provider)**: Aurora, ECS/Fargate, ALB, Cognito, IAM, VPC, ECR, CloudWatch, EventBridge Scheduler. Locally these are replaced by containers (Postgres, the app/worker containers) and in-process loops — floci does not meaningfully emulate them.

## Terraform layout
```
infra/terraform/
  providers.tf         # aws provider; endpoints{} + dummy creds when use_floci=true
  variables.tf         # use_floci, region, db_password, odoo_secret, ...
  messaging.tf         # SNS FIFO topic, SQS FIFO queues + DLQs, subscriptions, queue policies   (floci + AWS)
  secrets.tf           # Secrets Manager secrets + versions                                       (floci + AWS)
  data_aws.tf          # count = use_floci ? 0 : 1 : Aurora, ECS, ALB, Cognito, VPC, IAM, ECR      (AWS only)
  outputs.tf           # topic arn, queue urls, secret arns, db endpoint
  envs/local.tfvars    # use_floci=true, endpoint=http://localhost:4566
  envs/aws.tfvars      # use_floci=false, real region
```
The messaging/secrets modules are identical for floci and AWS (same AWS APIs); the
AWS-only file is gated by `count = var.use_floci ? 0 : 1`.

## Messaging resources (must match messaging-topology.md)
- SNS FIFO topic `platform-domain-events.fifo` (`content_based_deduplication=false`).
- SQS FIFO: `order-processing.fifo`, `order-delivery.fifo`, `projections.fifo`, `webhook-dispatch.fifo`, each with a `-dlq.fifo` and `redrive_policy(maxReceiveCount=5)`.
- Subscriptions: topic→each queue, `raw_message_delivery=true`, `filter_policy` on `eventType` (scope `MessageAttributes`) per the topology table.
- Queue policy allowing SNS to `sqs:SendMessage`.

## Security (SECURITY baseline)
- Secrets in Secrets Manager (`secret_ref` only in DB); KMS at rest; TLS in transit.
- IAM least-privilege task roles (api: read config + publish SNS + read secrets; worker: consume SQS + write DB + read secrets). No wildcards.
- Private subnets for Aurora + Fargate; ALB the only public ingress on 443; VPC endpoints for SNS/SQS/Secrets.
- Cognito JWT validated at the api; RLS on reseller-readable tables.
- Inbound ERP webhook auth: **shared-secret-in-path** for Odoo (Automation Rules can't HMAC) + IP allowlist; HMAC for ERPNext; reconcile sweeper as the safety net.

## Resiliency
- SQS visibility-timeout retries + DLQ (maxReceive=5); per-connection circuit breaker on ERP calls; outbox relay at-least-once with consumer dedup; reconcile fallback.

## Open items
- O-INFRA-1: Aurora Serverless v2 vs plain RDS (default: Serverless v2).
- O-INFRA-2: ALB + Fargate vs API Gateway (HTTP API) + Fargate (default: ALB).
- O-INFRA-3: Cognito emulation on floci is partial — local uses the JWT/header stub; real Cognito only on AWS.
