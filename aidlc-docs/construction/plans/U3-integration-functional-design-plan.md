# Functional Design Plan — U3 Integration

## Unit Context
U3 is the async engine: it consumes jobs (from U0 queue), routes orders (using U0's routing evaluation), executes the mapping DSL (canonical <-> ERP), calls ERP adapters (ERP Next, Odoo), and records outcomes back to the order lifecycle. It also runs status sync. Depends on U0. Registers job handlers with U0's HandlerRegistry.

Stories: runtime fulfillment of E2–E5; execution side of US-6.2 (routing) and US-6.3 (mapping).

## Artifacts
- [ ] `business-logic-model.md` (submission pipeline, status sync, corrective actions, mapping execution, adapter contract)
- [ ] `business-rules.md` (mapping application rules, adapter behavior, status reconciliation)
- [ ] `domain-entities.md` (adapter interface, ERP payloads, mapping execution model)

---

## Questions

## Question 1
The mapping DSL (hybrid: structured field entries + optional expressions). For MVP, how much expression power do we build?

A) Field entries + value maps only for MVP; expressions parsed but treated as simple direct/renamed field copies (no complex transform engine yet) (recommended — keeps MVP lean)

B) Field entries + a small safe expression evaluator (e.g., limited arithmetic/string ops)

C) Recommend

[Answer]: 

## Question 2
For the two ERP adapters in MVP (ERP Next, Odoo), what should they actually talk to?

A) Real ERP APIs (ERP Next REST, Odoo JSON-RPC) — requires live/sandbox instances + credentials

B) Stub/simulator adapters that emulate the ERP APIs (accept orders, return ids/statuses) so the PoC runs end-to-end without live ERPs (recommended for PoC)

C) Both: a real adapter interface with a stub implementation now, real HTTP calls behind a flag/config

D) Recommend

[Answer]: 

## Question 3
Status sync mechanism for MVP?

A) Polling only — a scheduled STATUS_SYNC job periodically fetches status for open orders (recommended; simplest)

B) Webhook endpoint only — ERPs push status

C) Both polling and webhook

D) Recommend

[Answer]: 

## Question 4
When routing returns NoMatch or an adapter call fails permanently, what's the order outcome?

A) Mark order Failed with a reason; rely on the U0 retry for transient errors, no auto-fallback (recommended — cross-system failover is deferred)

B) Attempt an alternate instance automatically (this is the deferred failover feature — would pull it into MVP)

C) Recommend

[Answer]: 

## Question 5
Corrective actions (cancel/amend/resubmit) against ERPs — how faithfully for MVP?

A) Implement against the stub/simulator with realistic accept/reject behavior (e.g., cancel rejected if already shipped); real ERP wiring later (recommended, pairs with Q2=B)

B) Full real-ERP corrective action wiring now

C) Recommend

[Answer]: 

---

Fill in the `[Answer]:` tags and let me know when done (or reply "recommended").
