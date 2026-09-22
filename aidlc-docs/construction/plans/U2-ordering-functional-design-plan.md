# Functional Design Plan — U2 Ordering & Lifecycle

## Unit Context
U2 is the client-facing surface: order placement, catalog/inventory lookup API, order list/detail, lifecycle views, and corrective-action initiation. It validates canonical orders (U0), persists them, enqueues fulfillment jobs (U0 queue -> U3), and reads status/history. Auth/context via U1. Stories: E2, E3 (client API), E4, E5.

## Artifacts
- [ ] `business-logic-model.md` (place order, lookups, list/detail, corrective initiation)
- [ ] `business-rules.md` (submission rules, corrective-state rules, tenant scoping)
- [ ] `domain-entities.md` (request/response DTOs; reuses U0 canonical + order tables)

---

## Questions

## Question 1
Catalog & inventory lookups (US-3.1/3.2) in MVP — how are they served, given stub ERPs?

A) On-demand: U2 enqueues/asks U3 to fetch from the routed ERP instance live (adds latency, most "real") 
B) Served from a simple portal-side cache/seed for the PoC (fast, deterministic), with a note that live fetch is the target (recommended for PoC)
C) Recommend

[Answer]: 

## Question 2
For catalog/inventory, which ERP instance do we query when the client hasn't placed an order yet (no routing context)?

A) Require the client to pick/scope by a context (e.g., region) that routing can use
B) Query a default/primary instance for catalog/inventory in MVP (simplest)
C) Recommend

[Answer]: 

## Question 3
Corrective actions from the client — synchronous ack then async execution (consistent with the async pipeline)?

A) Yes: validate + enqueue CORRECTIVE_ACTION job, return "accepted"; execution + result via lifecycle (recommended, matches U3)
B) Synchronous: call U3 inline and return the final result
C) Recommend

[Answer]: 

## Question 4
Amend validation — re-validate the full amended canonical order?

A) Yes, full canonical re-validation (BR-1) before enqueueing the amend (recommended)
B) Validate only changed fields
C) Recommend

[Answer]: 

---

Fill in the `[Answer]:` tags and let me know (or reply "recommended").
