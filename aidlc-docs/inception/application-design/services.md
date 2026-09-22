# Services — ERP & Supply Chain Order Portal

Service layer defines orchestration across components. In the modular monolith, these are internal application services with clean boundaries; they map to the coarse-grained module groups that are the future microservice extraction seams.

---

## S1. Order Service (Portal/Order group)
- **Responsibility**: Orchestrate order placement, lookups, and corrective actions from the client's perspective.
- **Coordinates**: C2 Order Intake API, C3 Canonical Model (validation), C4 Lifecycle Manager, C8 Async Queue, C10 Persistence, C1 Identity (context/authorization).
- **Key orchestrations**:
  - **Place order**: authorize -> validate canonical -> persist as Submitted -> enqueue submission job -> return ack.
  - **Corrective action**: authorize -> validate state/payload -> enqueue corrective job -> return ack.
  - **Read**: authorize + tenant-scope -> read from persistence.

## S2. Integration Service (Integration group)
- **Responsibility**: Execute the async pipeline that turns a queued job into an ERP interaction and a lifecycle update.
- **Coordinates**: C5 Routing Engine, C6 Mapping Engine, C7 ERP Adapters, C8 Workers, C4 Lifecycle Manager (update), C10 Persistence.
- **Key orchestrations**:
  - **Process submission**: dequeue -> route (C5) -> if NoMatch, mark order Failed with "no route matched" -> else map canonical->ERP (C6) -> adapter.submit (C7) -> record outcome via C4.
  - **Process corrective action**: dequeue -> map -> adapter.sendCorrectiveAction -> record outcome.
  - **Status sync**: on schedule or webhook -> adapter.fetchStatus / receiveWebhook -> map ERP->canonical (C6) -> C4.applyStatusUpdate.

## S3. Admin/Config Service (Admin/Config group)
- **Responsibility**: Manage platform configuration used by the Integration Service.
- **Coordinates**: C9 Admin Configuration, C10 Persistence, C7 Adapters (connectivity checks), C6 Mapping (validate mapping).
- **Key orchestrations**:
  - **Onboard/adjust ERP instance**: register/update instance -> optional connectivity check.
  - **Manage routing**: define rules -> set precedence.
  - **Manage mappings**: define mapping DSL -> validate (report unmapped required fields).
  - **View config**: aggregate instances + rules + mappings into a read view.

## S4. Identity Service (Identity group)
- **Responsibility**: Authentication, MFA, security context resolution, authorization.
- **Coordinates**: C1 Identity & Access, C10 Persistence (user/tenant records).
- **Key orchestrations**:
  - **Login**: authenticate -> MFA challenge -> verify -> issue token.
  - **Context resolution**: validate token -> return `SecurityContext` used by S1 and S3.

---

## Orchestration Patterns
- **Command/async pipeline**: Client-facing writes (submit/corrective) are accepted synchronously (validation + persist + enqueue) and completed asynchronously by workers. This satisfies Q2=C (fully async) and keeps the client responsive.
- **Tenant scoping**: Every S1 operation resolves `SecurityContext` first (via S4) and passes `tenantId` to persistence for row-level filtering (NFR-3).
- **Fail-closed routing**: When routing yields NoMatch, the order is marked Failed with an actionable reason rather than being sent anywhere (FR-3.4).
- **Idempotency intent**: Corrective actions and status updates are designed to be safely re-applied (latest-known-state-wins for status), supporting basic retry.
