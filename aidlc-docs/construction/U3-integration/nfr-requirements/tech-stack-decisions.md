# Tech Stack Decisions — U3 Integration

Inherits U0 fully. No new mandatory libraries for MVP (stub adapters).

| Concern | Decision | Rationale |
|---|---|---|
| ERP transport (MVP) | In-process stub/simulator adapters | PoC runs end-to-end without live ERPs (Q2=B) |
| ERP transport (future) | httpx-based real adapters behind ErpAdapter interface | Drop-in later; interface unchanged |
| Routing/mapping | Reuse U0 evaluate_routing + mapping models | No duplication |
