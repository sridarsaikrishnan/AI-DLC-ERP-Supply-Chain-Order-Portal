# Requirements Clarification (Round 2)

I found a few points in your answers that need tightening before I write the requirements. Please fill in the `[Answer]:` tags.

---

## Clarification 1: MVP boundary for "dynamic ERP onboarding"
Your answer to C1 said adding the next ERP should be dynamic and not take months. Combined with B3=D (AI-assisted connector generation from API specs) and B4=D (protocols undecided), I need to know how much must actually WORK in this first release versus be designed-for-now-built-later.

Which best describes the MVP target?

A) MVP hard-codes/hand-builds the two ERP adapters (ERPNext + Odoo), but the architecture is explicitly designed so a 3rd ERP is added via config + a thin generated adapter later. AI-assisted generation is a documented future capability, not built in MVP.

B) MVP must include a working AI-assisted adapter generator (ingest an ERP API spec, generate the adapter with human review) proven on the two ERPs from day one.

C) MVP includes a config-driven canonical mapping layer that works for the two ERPs; adding a new ERP means writing a config/mapping (days of work), no AI generation in MVP.

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Clarification 2: Access model for the mix of clients (A4=D vs D2=A)
You said clients are a mix of B2B customers and partner organizations (A4=D), but chose simple username/password + MFA for auth (D2=A). I want to confirm the access-control expectation.

A) Username/password + MFA is fine; each user belongs to one client organization, and org-level data separation is handled by tenant filtering (consistent with D4=B). No programmatic/API login needed for MVP.

B) Username/password + MFA for humans, PLUS API keys for partner organizations that integrate programmatically.

C) Keep it simplest for MVP: username/password + MFA only, single client org type; defer partner/programmatic access.

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Clarification 3: Confirming lightweight quality posture
You opted OUT of the security baseline (E1=B), OUT of the resiliency baseline (E2=B), and PARTIAL property-based testing (E3=B). Since this portal routes real orders into live ERP systems and handles multi-tenant order data, I want to confirm this is intentional for the MVP.

A) Yes — intentional. Treat this as a proof-of-concept MVP; keep it lightweight. I'll harden security/resiliency in a later phase.

B) Reconsider — actually enable the SECURITY baseline (order data + credentials to ERP systems warrant it), keep resiliency off and PBT partial.

C) Reconsider — enable BOTH security and resiliency baselines; this will run against real systems.

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

Fill in the answers above and let me know when done.
