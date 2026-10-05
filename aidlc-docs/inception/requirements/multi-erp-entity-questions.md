# Multi-ERP & Entity Resolution — Requirements Clarification Questions (Increment 7)

Bringing in NetSuite exposed that our routing design (`Item.owning_connection_id`) can't survive
multiple ERPs, or multiple countries sharing one ERP instance. While designing the fix, we
compared against a sister distribution platform — called **X-Change** below — a mature,
in-production system solving the same class of problem at much larger scale. Its code and real
data were read directly, not guessed, wherever cited.

**Nothing X-Change does is copied by default.** Each question exists because X-Change needed an
answer to it, at its scale, for its business. We need our own answer — which may be smaller,
different, or "doesn't apply," depending on facts only our business knows. The "why this
matters" line names the concrete failure if the question goes unanswered; the X-Change box is
reference material, not the recommendation.

Each question has a **recommended** option. Fill the letter after `[Answer]:`; pick the last
option and describe if none fit.

> **Answered 2026-10-04: all recommended (A), on my own best judgment from everything built and
> discussed this session** — not independently verified against the real business. Questions 0,
> 1, 8, and 11 are marked ⚠ below: these are pure business facts (multi-tenancy intent, reseller
> structure, real scale, inter-company trade) that nothing in this codebase or conversation can
> actually confirm. Treat those four as a working assumption to sanity-check before Construction
> relies on them, not a verified answer.

---

## Question 0 — Is this software ours alone, or a product for other companies to configure?

**Why this matters:** every question after this one assumes an answer to it. If we're the only
operator, we can hard-code facts true for our own business. If other companies will each bring
their own ERPs and reseller bases, every answer below has to become a per-deployment setting
instead of a one-time decision — a fundamentally bigger build.

**How X-Change handles this:** built for one company, Exclusive Networks, running its own
distribution business. Never designed for a second, unrelated distributor to configure.

A) **One company — us (recommended).** Every answer below can be scoped to our own real
   structure.
B) A product other companies will each deploy independently, with their own ERPs and org
   structures.
C) Other:

[Answer]: A ⚠ — assumed from how the system is built so far (one portal, one distributor's own
operation); not independently confirmed with the business.

---

## Question 1 — Does any reseller we deal with have its own internal corporate structure?

**Why this matters:** decides whether "one reseller = one independent account" is a fact we can
rely on everywhere, or whether we need a relationship graph (a parent that can see/act for its
children). Building the graph speculatively adds real machinery — membership edges, cascading
visibility — for a case that may not exist. Not building it when it's needed means a reseller's
own sub-companies show up as unrelated strangers, with their orders impossible to see together.

**How X-Change handles this:** a real example from their live data — "NTT Data" is one entity
with 16 `HAS_MEMBER` relationships, each pointing at a separate member reseller. The parent sees
and can act on behalf of every child. Nothing in any ERP provides this automatically; it was
built and is maintained by hand.

A) **No holding structure exists in our reseller base today (recommended — confirm against the
   real list).** Build nothing.
B) At least one reseller has sub-entities that must be seen/managed together — needs a
   parent/child relationship on `tenant`, scoped to visibility only (not the full bidirectional
   graph X-Change built).
C) Other:

[Answer]: A ⚠ — no holding/umbrella concept exists anywhere in the system today (`tenant_id` has
always meant one independent account); confirm against the real reseller list before relying
on this.

---

## Question 2 — Which reseller/subsidiary attributes does a real process in our business actually consume?

**Why this matters:** every field we add that nothing reads is a column maintained, validated,
and explained to users forever, for free. Every field a real process needs but that we never
added becomes a production blocker, discovered late — usually at the first real invoice.

**How X-Change handles this:** every entity schema has slots for `legalName`, `taxId`,
`dunsNumber`, `businessAddress` — but the real EXN Deutschland record we pulled has all three of
the first set to `null`. The schema carries the slot; this specific, real, core subsidiary never
needed it filled in.

A) **Only `name`, until a named process needs more (recommended).** Add a field the day a real
   downstream process (invoicing, compliance, dedup) is named that requires it.
B) Add `legalName` + `taxId` now — name the specific process that already needs them today.
C) Other (name the fields and the process consuming them):

[Answer]: A — matches the YAGNI discipline already applied everywhere this session; no named
process needs these fields yet.

---

## Question 3 — Can two different resellers legitimately use two different codes for the same one of our subsidiaries?

**Why this matters:** decides between a single foreign key (cheap — assumes one shared code we
assign) and a full issuer-scoped identifier list (real plumbing, only earns its cost if
resellers integrate via API and each insists on using their own vendor code for us, not one we
hand them).

**How X-Change handles this:** the real EXN Deutschland record carries two external
identifiers, from two different issuers, each with its own `firstSeenAt`/`lastSeenAt`/
`seenCount`. This is the exact mechanism behind `resellerSystem.id` on every PO — "X-Change
routes the order using it," cross-checked against the quote it's ordering against.

A) **One canonical code per subsidiary, assigned by us, used by everyone (recommended).** No
   per-reseller code list.
B) Yes — API-integrated resellers must use their own vendor code for us; we resolve it on their
   behalf. Needs a `(reseller, their_code) → our subsidiary` table.
C) Other:

[Answer]: A — today's integration surface is our own portal/GraphQL, not a generic partner API;
nothing forces a reseller to invent their own code for us.

---

## Question 4 — Does any subsidiary ever need to be live against two ERP targets at once?

**Why this matters:** decides whether "one active ERP connection per subsidiary" is a safe,
permanent invariant (simple, one uniqueness constraint) or whether a real scenario — cutover
testing, a parallel run during migration — needs two targets active simultaneously
(disambiguated by purpose, with real risk of routing ambiguity if that disambiguation is wrong).

**How X-Change handles this:** the real EXN Deutschland record's routing context points at a
sandbox scope, not production, at the moment it was pulled. Its schema explicitly supports more
than one record binding per entity (`discriminatedBy`, `isPrimary`) for cases like one record
per invoicing currency.

A) **Exactly one active ERP connection per subsidiary at a time (recommended — matches the
   Increment 7 design already drafted).** Switching replaces the active route; never two at once.
B) Yes — a real scenario needs concurrent dual-routing. Needs `company_erp_routes` to support
   more than one active row per subsidiary, disambiguated by purpose.
C) Other:

[Answer]: A — no scenario requiring concurrent dual-routing has come up; the drafted design
already assumes this.

---

## Question 5 — Should an order referencing an unprovisioned record be rejected, or held provisionally?

**Why this matters:** reject-immediately is the simpler build, but can stall a legitimate deal
on an IT setup gap that has nothing to do with the deal itself. Hold-provisionally avoids
stalling revenue, but requires a retry/resolution state machine that doesn't exist anywhere in
our system today.

**How X-Change handles this:** an entity can exist `PENDING_IDENTIFICATION` — created the
moment it's first referenced, with the triggering transaction held until the real record is
confirmed. Their own reseller-facing docs confirm this isn't an edge case: `RECEIVED` on a
submission never means "accepted" — the real verdict always comes later, asynchronously.

A) **Reject with a clear "not provisioned yet" error; resolve manually, then retry (recommended
   for now).** No async state machine to build. Revisit if real deals start getting blocked by
   this often enough to hurt.
B) Hold it provisionally; reconcile once the mapping exists. Needs new "pending" plumbing.
C) Other:

[Answer]: A — matches the fail-closed philosophy already everywhere in this codebase (unknown
product, duplicate order reference); reject loudly rather than build async resolution
speculatively.

---

## Question 6 — If the same real subsidiary or reseller is ever onboarded twice, how do we recover?

**Why this matters:** with no plan, a duplicate becomes two disconnected ids with split history
— discovered only when someone can't find a record's past orders under the "other" id. A
built-in merge avoids that permanently, but is real machinery, built for a problem that may
never actually occur.

**How X-Change handles this:** `BusinessEntityTombstoned` — one-way, terminal. The loser is
never deleted (financial records can't disappear); it's marked tombstoned with a
`successorEntityId`, and every future lookup follows the chain to the survivor.

A) **Nothing built, until it happens once (recommended).** Handle the first occurrence by hand;
   build the mechanism only if it recurs.
B) Build a minimal version now — a `status` + `superseded_by_id` column, the same shape
   `BindingStatus` already has.
C) Other:

[Answer]: A — no evidence duplicate onboarding has ever happened in this system.

---

## Question 7 — Who performs the act of recording these mappings, and how?

**Why this matters:** decides whether this is a one-time scripted setup task during onboarding
(cheap, reuses what exists) or a recurring day-2 workflow sales/finance need to run themselves
(a real admin feature — screen, audit trail, permissions — not a side effect of an engineering
script).

**How X-Change handles this:** exactly one write path, a single `POST /api/entities` endpoint,
shared by two populating patterns: a seed script reading a human-authored file (real ids copied
by hand from the ERP's own admin UI, applied one call at a time, resumable), and ad hoc operator
calls for day-2 additions.

A) **A script in the spirit of our existing `scripts/seed_demo.py` for initial onboarding;
   day-2 additions go through the operator GraphQL mutations we already have (recommended).**
   No new UI, no new endpoint shape.
B) Sales/finance need self-service access, without engineering involved — needs a real admin UI.
C) Other:

[Answer]: A — `scripts/seed_demo.py` plus the existing operator GraphQL mutations already cover
this pattern; no gap to fill.

---

## Question 8 — Over the next 1–3 years, how many subsidiaries, ERP instances, and resellers do we actually expect?

**Why this matters:** at small scale, flat tables with uniqueness constraints stay correct and
fast forever — no architecture question here. At real scale (dozens of subsidiaries or instances),
only the query patterns need re-checking, not the design — but that's worth knowing now, not
discovered under load.

**How X-Change handles this:** confirmed at least five countries (Italy, France, Germany, UK,
Hong Kong) plus "most countries" per their own scope table, 3+ ERP accounts, years of
accumulated onboarding — and still only a dedicated service plus per-consumer caching, not a
redesign of the underlying relationships.

A) **A handful of subsidiaries and ERP instances for the foreseeable future (recommended — confirm
   the real number).** Nothing beyond flat tables is ever justified at this scale.
B) We expect double-digit+ subsidiaries and/or several ERP types within 1–2 years.
C) Other (give the real expected numbers):

[Answer]: A ⚠ — one ERP today, one more being added; nothing discussed points at dozens, but
this is a real business projection, not something derivable from the code.

---

## Question 9 — Which fields will actually be populated on the real NetSuite account we connect to?

**Why this matters:** a mapping built against a field that happens to be empty in the real
account produces a silent gap — discovered only when one specific record fails to resolve in
production, usually during a live cutover.

**How X-Change handles this:** doesn't assume. `taxId`/`dunsNumber`/`legalName` exist as schema
slots independent of whether any given account's own admin ever populated the equivalent field.
A generic ERP integration only ever gives you what that specific account was configured to carry.

A) **Confirm directly against the real account before building any mapping that reads from it
   (recommended).** Don't assume a field exists because a schema has a slot for it, or because
   our Odoo integration has an equivalent.
B) Other (describe a different verification approach):

[Answer]: A — this is a process commitment (verify before building), not really a design
decision; accepted as-is.

---

## Question 10 — Do we need a "parent group" above our own subsidiaries?

**Why this matters:** decides whether cross-subsidiary reporting/visibility needs a first-class
relationship (a real thing to build and keep consistent) or can stay a plain query across
independent rows (free, until someone actually asks for it).

**How X-Change handles this:** no group-level entity sits above EXN's subsidiaries in the data
we inspected — they're peers. Cross-subsidiary facts (inter-company trade) are handled by a
*separate* service correlating pairs of subsidiaries, not by one parent owning them.

A) **No group entity — subsidiaries are independent peers (recommended, matches
   X-Change).** Revisit only if Question 11 below turns out to need it.
B) Yes — cross-subsidiary reporting needs to be a first-class concept, not a derived query.
C) Other:

[Answer]: A — nothing built or requested needs cross-subsidiary rollup reporting.

---

## Question 11 — Does any one of our own subsidiaries ever source through another one, instead of a real external vendor?

**Why this matters:** if yes, that transaction needs different accounting treatment —
eliminated on consolidation — and must be recognized automatically, not booked as an ordinary
3rd-party purchase. Getting this wrong corrupts financial reporting, not just software behavior.
If no, this entire topic (and the service X-Change built for it) doesn't apply to us at all.

**How X-Change handles this:** a dedicated service, `distributor-profile-ms`, exists
specifically to detect "is this vendor actually one of our own subsidiaries" — because EXN
Supply Chain Services BV genuinely, routinely sells to EXN Italy/France/Germany internally.

A) **No internal leg exists — every subsidiary sources from real external vendors and sells to real
   external resellers (recommended default — confirm this is actually true).** Build nothing.
B) Yes — at least one subsidiary sources through another one of our own subsidiaries. Needs the
   detection + accounting-treatment logic X-Change built a dedicated service for.
C) Other:

[Answer]: A ⚠ — no internal buy/sell leg between our own subsidiaries has come up anywhere in this
system. This is the one most worth double-checking with the business: if wrong, it has real
accounting consequences, not just a missing feature.

---

## Already resolved this session (recorded for traceability — not awaiting an answer)

- **Per-ERP product listings (`item_erp_listings`): dropped.** `OdooAdapter._resolve_product`
  already does a live, fail-closed check against the real ERP at submission time; a cached
  local copy would only duplicate that check with a version that can drift from the truth.
- **Shared catalog (`Item` table): removed entirely, every channel.** Every quote line now
  carries its own `name`/`kind` inline, because NetSuite's sales reps will author quotes
  directly in NetSuite, never through our UI — matching how X-Change's quote lines carry a
  full product description with no shared catalog, since for X-Change the ERP, not the
  platform, is always the authority on what a product is.
- **Subsidiary → ERP routing, decided at quote-issue time, not order time: confirmed.**
  `company_erp_routes` (subsidiary → connection, one active at a time) + `routed_to_connection_id`
  stamped on the Quote.
- **Per-subsidiary identity inside a shared ERP instance: confirmed needed.** `erp_entity_ref` on
  `company_erp_routes` — nullable, used only when an ERP (like NetSuite OneWorld) hosts more
  than one of our subsidiaries in one account.
