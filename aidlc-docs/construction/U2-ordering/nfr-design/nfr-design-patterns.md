# NFR Design Patterns — U2 Ordering & Lifecycle

Inherits U0/U1 patterns. U2-specific:
- **P-U2-1 Command-then-async**: writes (submit/corrective) validate + persist + enqueue synchronously; fulfillment async (U3).
- **P-U2-2 Tenant-scoped reads/writes**: via U0 TenantScopedRepository; tenantId from U1 context.
- **P-U2-3 Auth guards**: routes depend on U1 `current_context` / `require_role`.

## Compliance Summary
- Security: DISABLED — N/A. Resiliency: DISABLED — N/A. PBT (Partial): validation is exercised via U0 validator tests; U2 adds API/integration tests. Compliant.
