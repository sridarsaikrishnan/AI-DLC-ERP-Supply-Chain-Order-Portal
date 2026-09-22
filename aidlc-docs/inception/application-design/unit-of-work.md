# Units of Work — ERP & Supply Chain Order Portal

Decomposition of the system into 7 units of work (development/design units). This is a **modular monolith** with event sourcing + CQRS (Axon) for the `Order` aggregate — a "unit" is a logical grouping of capability modules and stories, **not** an independently deployed service. Based on approved answers: 7 units (Q1=A), thin end-to-end slice across **both ERPs** first (Q2=X), reseller UI as its own unit + operator UI bundled with operator API (Q3=A), single Platform Foundation unit (Q4=A), single mono-repo Gradle multi-module (Q5=A), single team sequential (Q6=A).

---

## Units

### U1 — Platform Foundation
- **Modules**: `canonical-model`, `platform-infrastructure`, `access-control`, plus the **Axon event store + CQRS projection framework**.
- **Responsibilities**: canonical types/events/DTOs; PostgreSQL persistence + Flyway; SQS/SNS + transactional outbox; **Axon config** (JPA event store, command/query buses, projection + snapshot framework); JWT validation, tenant-context, authorization; observability; credential crypto.
- **Why first**: every other unit depends on it.
- **Stories**: US-003, US-004, US-015 (structural, no-ERP-identity via DTO separation), US-016 (tenant isolation); the cross-cutting Definition of Done.

### U2 — ERP Integration
- **Modules**: `erp-integration`.
- **Responsibilities**: `ErpAdapter` seam + transport adapters — **Odoo (XML-RPC/JSON-RPC)** and **ERPNext (REST)**; `DeclarativeMappingEngine` (canonical↔native); `FileBackedConnectionRegistry`; encrypted credential handling; conformance suite; API-first onboarding surface (future US-F7).
- **Stories**: US-027, US-028, US-029, US-031.

### U3 — Ordering, Routing & Delivery
- **Modules**: `order-management` (**event-sourced `Order` aggregate + projectors**), `order-routing`, `item-catalog` (ownership), delivery/ingestion on `worker`.
- **Responsibilities**: order commands + lifecycle events (Axon); CQRS projections (`order_summary`, `order_detail`, `order_timeline`, `delivery_view`); routing at Validated; mixed-ERP rejection; guaranteed delivery (SQS FIFO, retry/DLQ, idempotency); status ingestion → canonical status derivation.
- **Stories**: US-006 (aggregate/commands), US-009, US-010, US-013, US-014, US-017, US-018, US-019, US-020, US-021, US-030.

### U4 — Reseller API & Webhooks
- **Modules**: reseller GraphQL on `api`, `webhook-delivery`, read sides of `customer-binding` and `item-catalog`.
- **Responsibilities**: reseller `/graphql` (queries backing order list/detail; item catalog; linked customer; mutations delegate to U3 commands); webhook endpoints + signing + delivery log + replay; reseller-safe error mapping.
- **Stories**: US-011, US-012, US-022, US-023, US-024, US-025, US-026 (and the query APIs backing US-007/US-008).

### U5 — Operator Admin (API + Web)
- **Modules**: operator GraphQL on `api`, `customer-binding`, `item-catalog` (conflicts), `audit-trail`, **operator React app**.
- **Responsibilities**: reseller onboarding (+ Cognito client), customer bindings + verification + match suggestions, connection health, item-ownership conflict resolution, failed-message triage, audit trail, read-only mapping viewer.
- **Stories**: US-001, US-002, US-005, US-032, US-033, US-034, US-035, US-036.

### U6 — Reseller Web App
- **Modules**: reseller React app.
- **Responsibilities**: `Main` (/orders), `OrderDetail`, `DeliveryLog`, `WebhookEndpoints` screens; OIDC sign-in; consumes U4; never renders ERP identity.
- **Stories**: US-007, US-008 (UI), US-022/US-024 (UI surfaces).

### U7 — Developer Enablement & Infrastructure
- **Modules**: Terraform (`infra/`), Docker Compose (`docker/`), seed CLI (`tools/seed`), CI pipeline.
- **Responsibilities**: one-command local stack (real PostgreSQL, Floci for Cognito/SQS/SNS, mock ERP, optional Odoo/ERPNext); allow-listed reversible seed tool; AWS IaC; CI (build, tests incl. jqwik + Testcontainers + ERP conformance).
- **Stories**: US-037, US-038.
- **Timing**: developed alongside U1 (needed early for local dev/CI).

---

## Code organization (greenfield mono-repo, Q5=A)

Single Git repository; Gradle multi-module backend + `ui/` + `infra/`. (Application code lives at the workspace root; `aidlc-docs/` holds documentation only.)

```
erp-platform/
  settings.gradle.kts          # includes all Gradle modules
  build.gradle.kts             # shared build config (Java 21, Spring Boot, Axon BOMs)
  platform/
    canonical-model/           # U1
    platform-infrastructure/   # U1 (persistence, messaging, Axon config, observability, crypto)
    access-control/            # U1 (JWT, tenant context, authz, Cognito admin)
  domain/
    order-management/          # U3 (event-sourced Order aggregate + projectors)
    order-routing/             # U3
    item-catalog/              # U3/U5
    customer-binding/          # U5 (+ read in U4)
    erp-integration/           # U2 (Odoo RPC + ERPNext REST adapters, mapping engine)
    webhook-delivery/          # U4
    audit-trail/               # U5
  app/
    api/                       # Spring Boot host: reseller /graphql + operator /admin/graphql
    worker/                    # Spring Boot host: listeners, projectors, schedulers, delivery, ingestion
  ui/
    reseller/                  # U6 React app
    operator/                  # U5 React app
  infra/                       # U7 Terraform (modules + one folder per environment)
  docker/                      # U7 docker-compose (Postgres, Floci, mock ERP, optional Odoo/ERPNext)
  tools/
    seed/                      # U7 seed CLI
```

Module dependency direction (enforced): `domain/*` → `canonical-model` only (define ports); `platform-infrastructure` implements ports; `app/*` compose everything; nothing depends on `app/*`. Reseller code depends only on reseller DTOs (FR-19).
