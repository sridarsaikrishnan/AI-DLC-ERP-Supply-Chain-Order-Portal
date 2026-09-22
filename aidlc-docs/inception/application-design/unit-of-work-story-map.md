# Story → Unit Map — ERP & Supply Chain Order Portal

Every story from `stories.md` (US-001..US-038) is assigned a **primary unit** (where the story is chiefly built) and any **supporting units** it also touches (e.g., a UI story needs its API). Future-scope stories (US-F*) are noted at the end.

---

## Assignment

| Story | Title (short) | Primary unit | Also touches |
|---|---|---|---|
| US-001 | Operator onboards reseller + OAuth client | U5 | U1 (Cognito/identity) |
| US-002 | Operator creates & verifies customer binding | U5 | U2 (verify vs ERP) |
| US-003 | Reseller integrator M2M auth | U1 | U4 |
| US-004 | Reseller business user sign-in | U1 | U6 |
| US-005 | Onboarding match suggestions | U5 | U2 |
| US-006 | Reseller places an order | U3 (aggregate/commands) | U4 (API), U6 (form) |
| US-007 | Reseller views order list | U6 | U4 (query) |
| US-008 | Reseller views order detail & timeline | U6 | U4 (query), U3 (projection) |
| US-009 | Reseller updates an order | U3 | U4 |
| US-010 | Reseller cancels an order | U3 | U4 |
| US-011 | Reseller reads items (read-only) | U4 | U3/U2 (catalog sync) |
| US-012 | Reseller reads linked customer | U4 | U5 (binding) |
| US-013 | Platform routes order to one ERP | U3 | U2 |
| US-014 | Mixed-ERP order rejected safely | U3 | U4 (message) |
| US-015 | No ERP identity to resellers | U1 (structural: DTO separation) | U4, U5, U6 (verify) |
| US-016 | Tenant data isolation | U1 | all |
| US-017 | Guaranteed delivery through outage | U3 | U1 (SQS/outbox) |
| US-018 | Exactly-once effect (idempotent) | U3 | U1 |
| US-019 | Reads continue when ERP down | U3 (projections) | U4 |
| US-020 | ERP status changes appear in lifecycle | U3 (ingestion) | U2 |
| US-021 | Rejected order shows safe reason | U3 | U4 |
| US-022 | Reseller manages webhook endpoints | U4 | U6 (UI) |
| US-023 | Signed webhook delivery (proposed) | U4 | — |
| US-024 | Delivery log with attempts & replay | U4 | U6 (UI) |
| US-025 | Webhook event types (proposed) | U4 | — |
| US-026 | Signing-secret rotation (proposed) | U4 | — |
| US-027 | Add an ERP via configuration | U2 | U7 (fixtures) |
| US-028 | Declarative canonical↔native mappings | U2 | — |
| US-029 | Conformance suite for an ERP | U2 | U7 (CI) |
| US-030 | Ingest ERP changes into read model | U3 | U2 |
| US-031 | Encrypted ERP credential storage | U2 | U1 (crypto) |
| US-032 | Monitor connection health | U5 | U2 |
| US-033 | Resolve item-ownership conflicts | U5 | U3/U2 (detection) |
| US-034 | Triage failed / dead-lettered messages | U5 | U3 (delivery) |
| US-035 | Review the audit trail | U5 | U1 (audit infra) |
| US-036 | Manage field mappings (read-only viewer) | U5 | U2 |
| US-037 | One-command local environment | U7 | all |
| US-038 | Safe seed tool | U7 | U2 (connections), U5 (bindings) |

## Coverage check
- All 38 stories (US-001..US-038) are assigned a primary unit. ✅
- Every unit has stories: U1 (5), U2 (6), U3 (11), U4 (9), U5 (8), U6 (4 UI surfaces), U7 (2 + cross-cutting). Stories that span UI+API are counted at their primary unit with "also touches" noted.
- Cross-cutting Definition of Done (security, resiliency, PBT incl. ES/CQRS replay & projection properties, accessibility) applies to every unit.

## Future scope (not assigned to MVP units)
- **US-F1** self-service ERP onboarding, **US-F2** cross-ERP workflows, **US-F3** SAP, **US-F4** split orders, **US-F5** platform-created ERP customers, **US-F6** exports, **US-F7** AI/MCP-assisted ERP onboarding (extends U2's API-first onboarding surface).
