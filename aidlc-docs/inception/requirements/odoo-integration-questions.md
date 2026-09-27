# Requirements Clarification — Real Odoo Integration (Increment 2)

Goal: replace the Odoo **mock** (`OdooStubAdapter`) with a **real** Odoo integration, stand up a **local Odoo development environment**, and wire it into the running portal. Fix the existing architecture where required (e.g., how connection credentials reach the adapter).

Please answer each question by filling in the letter after the `[Answer]:` tag. If none fit, choose the last option (Other) and describe. My recommended default is marked **(recommended)**. If you're happy with all recommendations, you can just write "all recommended" here and I'll proceed: ____________

---

## Question 1
Which protocol should the real Odoo adapter use to talk to Odoo?

A) JSON-RPC via Odoo's external API (`/jsonrpc`) — works with stock Odoo, no server-side add-on needed, same approach already proven in the quickstart consumer **(recommended)**

B) XML-RPC via Odoo's external API (`/xmlrpc/2`)

C) A custom Odoo addon module exposing REST endpoints (more work, requires maintaining an Odoo module)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2  (architecture)
Odoo needs connection details the current model doesn't hold: base URL, database name, username, and password/API key. Today `ErpInstance.connection_ref` is a single opaque string. How should connection details be stored and reach the adapter?

A) Extend the `ErpInstance` config model + `erp_instances` table with structured fields (`base_url`, `database`, `username`, `secret`) plus a migration; admin-manageable — cleanest and matches the "admin registers ERP instances" design **(recommended)**

B) Encode everything inside the existing `connection_ref` string (a URL or small JSON blob) — no schema/migration change, minimal

C) Keep `connection_ref` as a key/name and resolve the actual credentials from environment variables (secrets never stored in the DB)

X) Other (please describe after [Answer]: tag below)

[Answer]: A  (determined by AI after reviewing the docker POC + main branch: matches the config-driven "operator registers ERP instances/connections" design in the portal screens; secret stored inline per the existing PoC posture since security is OFF (Q9=B); the local Odoo's URL/db/user/password are supplied via seed data so the dev loop stays as easy as the env-based POC)

---

## Question 3
How deep should the canonical Sales Order → Odoo `sale.order` mapping go for this MVP?

A) Full: resolve/create the customer (`res.partner`), map line items to products (look up `product.product` by code, create if missing), and create a real `sale.order` with order lines and amounts — most realistic demo **(recommended)**

B) Minimal: create a `sale.order` against one pre-provisioned demo partner, put the line items into a note/description field, no product resolution

C) Rely only on the existing admin-defined mapping definitions (no special partner/product logic in the adapter)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
When a customer (partner) or product referenced by an order does not yet exist in Odoo, the adapter should:

A) Auto-create missing partners and products on submit — keeps the dev/demo loop frictionless **(recommended)**

B) Fail the order as a terminal error if the partner/product is not found (strict)

C) Auto-create partners, but require products to pre-exist (fail if product missing)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
How should Odoo's states map back to the portal's canonical lifecycle (Submitted → Accepted → Processing → Shipped → Invoiced → Cancelled)?

A) The adapter translates Odoo's state (`draft`/`sent`/`sale`/`done`/`cancel` plus delivery/invoice status) into the native tokens the existing handler already understands (`Accepted`/`Processing`/`Shipped`/`Invoiced`/`Cancelled`), so the handler's reconciliation map stays unchanged **(recommended)**

B) Extend the portal's canonical reconciliation map to accept raw Odoo state strings directly

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
How do we choose between the real adapter and the stub?

A) Real Odoo adapter becomes the default; keep the stub for unit tests only; select via a config/env flag so CI without Odoo still works **(recommended)**

B) Replace the stub entirely and delete it

C) Keep both and choose per `ErpInstance` (a "mode" flag on each instance)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7
How should the local Odoo dev environment be wired to the portal?

A) Add an `odoo` service (+ its Postgres) to the **root** `docker-compose.yml`, pre-initialized with the Sales app, and seed a matching ERP instance/connection in the portal so a single `docker compose up` runs portal + Odoo end-to-end **(recommended)**

B) Keep Odoo separate in `docker/odoo-quickstart/` and just point the portal at it via env/config

C) Both: integrated root compose for the dev loop, and retain the quickstart for standalone API exploration

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 8
Which corrective actions should the real adapter support against Odoo?

A) Cancel (`action_cancel`), Amend (update order lines while the order is still `draft`/`sent`), and Resubmit (create a new order) — mirrors the current handler semantics **(recommended)**

B) Cancel only; treat Amend/Resubmit as unsupported (terminal) for now

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 9 — Security Extension
Should security extension rules be enforced for this increment? (It introduces real credentials and outbound network calls, so this is worth reconsidering — it was OFF for the original PoC.)

A) Yes — enforce all SECURITY rules as blocking constraints (recommended once this talks to real ERP systems with real credentials)

B) No — keep security rules off (fine while this stays a local dev/PoC against a throwaway Odoo)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 10 — Resiliency Extension
Should the resiliency baseline (directional Well-Architected Reliability best practices) be applied to this increment?

A) Yes — apply the resiliency baseline as design-time guidance (external calls fail; retries/backoff/timeouts/circuit-breaking matter)

B) No — skip it (rely on the existing bounded-retry queue; suitable for a local dev/PoC)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 11 — Property-Based Testing Extension
Should property-based testing rules be enforced for this increment?

A) Yes — enforce PBT as blocking constraints

B) Partial — PBT only for pure functions and serialization round-trips (matches the current project setting; e.g., status-mapping and payload-mapping round-trips) **(recommended)**

C) No — skip PBT for this thin integration layer

X) Other (please describe after [Answer]: tag below)

[Answer]: B
