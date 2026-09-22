# Unit of Work → Story Map — ERP & Supply Chain Order Portal

Maps every user story to its owning unit. Stories that require cross-unit collaboration note the supporting unit(s).

| Story | Title | Owning Unit | Supporting Unit(s) |
|---|---|---|---|
| US-1.1 | Client user login | U1 Identity | U0 |
| US-1.2 | Multi-factor authentication | U1 Identity | U0 |
| US-1.3 | Tenant-scoped access | U1 Identity | U0 (row-level filtering) |
| US-2.1 | Create and submit a sales order | U2 Ordering & Lifecycle | U0, U1, U3 (async fulfillment) |
| US-2.2 | See submission outcome / ERP ack | U2 Ordering & Lifecycle | U3 (adapter result), U0 |
| US-3.1 | Browse product catalog | U2 (lookup API) | U3 (fetch+map), U0 |
| US-3.2 | Check inventory availability | U2 (lookup API) | U3 (fetch+map), U0 |
| US-4.1 | View current order status | U2 Ordering & Lifecycle | U0 |
| US-4.2 | View order status history | U2 Ordering & Lifecycle | U0 |
| US-4.3 | Status reflects ERP updates | U2 (lifecycle apply) | U3 (status sync/map), U0 |
| US-5.1 | Resubmit a failed order | U2 (initiate) | U3 (execute), U0 |
| US-5.2 | Cancel an order | U2 (initiate) | U3 (execute), U0 |
| US-5.3 | Amend an order | U2 (initiate) | U3 (execute), U0 |
| US-6.1 | Register an ERP instance | U4 Admin & Config | U0 (config model), U3 (connectivity check) |
| US-6.2 | Define content-based routing rules | U4 (authoring) | U0 (config model); U3 (runtime evaluation) |
| US-6.3 | Manage canonical↔ERP mappings | U4 (authoring) | U0 (config model); U3 (runtime translation + validation) |
| US-6.4 | View current routing/mapping config | U4 Admin & Config | U0 |

## Coverage Check
- **All 17 stories assigned.** ✔
- **Every unit has stories or shared responsibility**:
  - U0 Foundation: no direct stories (shared foundation) — supports all
  - U1 Identity: US-1.1, US-1.2, US-1.3
  - U2 Ordering & Lifecycle: US-2.1, US-2.2, US-3.1, US-3.2, US-4.1, US-4.2, US-4.3, US-5.1, US-5.2, US-5.3
  - U3 Integration: runtime fulfillment for E2–E5 + US-6.2/US-6.3 execution
  - U4 Admin & Config: US-6.1, US-6.2, US-6.3, US-6.4

## Split-Story Notes
- **US-6.2 / US-6.3** have an **authoring** side (U4: define rules/mappings via admin UI) and a **runtime** side (U3: evaluate routing / apply mapping). Both units carry acceptance criteria in construction.
- **E3 (US-3.1/US-3.2)**: client-facing API in U2; ERP fetch+map in U3 (per Q2=A).
- **US-4.3 / US-5.x**: initiated/tracked in U2, executed against the ERP by U3 workers.
