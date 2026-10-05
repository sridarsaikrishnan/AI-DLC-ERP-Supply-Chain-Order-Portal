# Application Design — Multiple ERPs: routing, no shared catalog, ERP-authored quotes (Increment 7)

**Status:** proposed, awaiting review. Nothing in this document is built yet.

**Who this is for:** everyone — the architect, the product owner, and the developer who
will build it. It's written so all three can read the same pages and agree on the same
thing. Where a word needs a precise technical meaning, it's introduced in plain English
first.

**Why now:** today the platform talks to one ERP (Odoo), and every quote is built by an
operator inside our own portal. NetSuite is coming next, and NetSuite is used by sales
people who already do their job inside NetSuite — they are not going to start using our
portal. That single fact changes three things, not one, and this document covers all
three together because they're the same underlying shift, seen from three angles.

**Revision history:**
- *Draft 1:* proposed fixing ERP routing (subsidiary → ERP, decided at quote time) and letting
  one product be listed for sale through more than one ERP.
- *Draft 2:* dropped the "list a product under several ERPs" idea — the ERP adapter
  already checks live, at submission time, whether a product exists in the target ERP; a
  second, our-side copy of that fact would only add a way to be wrong.
- *Draft 3 (this one):* the user asked "why do we even have a catalog?" and pointed out
  that future ERPs (NetSuite) are used by sales reps who will never touch our UI. That
  reframes the problem — see §1. **Decision: remove the shared catalog table entirely, and
  treat the ERP as the author of the quote for ERP-driven sales channels.**

---

## 1. The reframing: who actually decides what's on a quote?

Every earlier draft of this document assumed one thing without saying it out loud: **an
operator, using our screens, decides what's on a quote.** That's where "a shared product
catalog" comes from — if people are going to repeatedly pick products from a list in our
UI, it's natural to store that list once and let them pick from it.

That assumption is true for Odoo today. It will not be true for NetSuite. A NetSuite sales
rep already builds the quote — in NetSuite, with NetSuite's own product list, the way
they've always worked. By the time our platform hears about that quote, every product on
it has already been chosen by someone who was never going to open our UI at all.

Once that's true, a shared catalog in *our* system stops making sense for that quote. There
is nothing for an operator to "pick from our list," because nobody is picking from a list —
the deal already exists, somewhere else, fully described. Our job becomes **receiving**
that description, not **collecting** it.

This is also why a sister distribution platform (referenced earlier in this project's
design discussion) has no catalog at all: its quotes are authored inside the ERP by sales
reps, not inside the platform's own UI. Every line on its quotes just carries the product's
full description inline — code, name, price — copied straight from the ERP's own record,
every time. Nothing is "looked up" from a shared table on that platform's side, because
nothing needs to be — the ERP already said what the product is.

**Decision: adopt that shape here too, for every channel, not just the ERP-authored ones.**
Drop the shared `Item` table. Every quote line carries its own product description
directly on the line — whether that line was typed in by an operator (today's Odoo-style
flow) or copied in from an ERP's own quote (NetSuite-style). One consistent shape, not two.

---

## 2. What this means concretely

### Today

```
Operator picks a SKU from the catalog  →  Quote line stores just the SKU
                                             (+ price, UoM, tax — already quote-level)
Order placement looks the SKU back up in the catalog, just to find "box or license"
```

### Proposed

```
Whoever builds the quote (operator, or the ERP that authored it) supplies the
product's full description directly on the line — SKU, name, box-or-license,
price, UoM, tax. Nothing is looked up anywhere else, ever, for any channel.
```

The `Item` table currently answers exactly one remaining question system-wide: *"is this
SKU a box or a license?"* (pricing and tax already moved onto the Quote back in
Increment 5/ADR-0016). Removing it means that one fact moves from "looked up from a shared
table" to "supplied directly, on the line, by whoever is building the quote" — an operator
typing it in for Odoo, or an ERP's own item record for NetSuite.

---

## 3. Two ways a quote comes to exist — both produce the same shape

### Portal-authored (today's Odoo flow — unchanged in spirit)

An operator still uses our quote screen. They still type in each line: SKU, name,
box-or-license, price, unit of measure, tax. The only change from today is *where* that
typing happens — directly on the quote line, not via a dropdown backed by a shared table.
Mechanically simpler for the operator, not harder: one screen, no separate "manage the
catalog first" step.

### ERP-authored (the NetSuite shape, and any future ERP whose sales reps work in the
ERP itself)

The sales rep builds the quote in NetSuite, the way they already do. Our platform receives
a copy of it — the same pattern already used for order status today (an ERP tells us
something changed, we go fetch or receive the detail), extended to cover quotes:

```
NetSuite rep builds quote (in NetSuite)
        │
        ▼
NetSuite tells us: "quote X exists / changed"   (webhook, same shape as today's order
        │                                         status webhook — or polled, same
        ▼                                         fallback the reconciliation sweeper
A NetSuite-specific adapter translates            already provides for orders)
NetSuite's own quote lines into our Quote
shape — SKU, name, price, box-or-license,
copied straight off NetSuite's record
        │
        ▼
Our Quote exists, reseller can see/order against it in our portal,
exactly as if an operator had typed it in
```

This is **new scope, not yet detailed** — today's ERP adapters only ever send orders *to*
the ERP and read status *back*; none of them has ever been the *source* of a quote. The
detailed shape (which NetSuite fields map to which of our fields, webhook vs. polling,
how often) is deliberately left for when NetSuite integration work actually starts — we
don't know NetSuite's real field names yet, and guessing them now would just be
wrong later. What's decided now is the *shape* of the answer: one more thing an ERP
adapter can do (hand us a quote), reusing the inbound-webhook-plus-reconciliation-poll
pattern that already exists for order status, not a new mechanism invented from scratch.

### Routing is trivial for the ERP-authored path

The earlier parts of this design (subsidiary → ERP routing, §4 below) exist to answer "which
ERP does this order go to" when a human in *our* portal is building the quote and doesn't
otherwise know. For an ERP-authored quote, that question never comes up — the quote
arrived *from* a specific ERP connection, so that's obviously where any resulting order
goes back to. No routing decision is needed at all for this path.

---

## 4. Subsidiary → ERP routing (unchanged from the previous draft — still needed for the
portal-authored path)

This part of the design is untouched by the catalog discussion above — it solves a
different problem (which ERP does a *portal-authored* quote belong to) and the fix still
applies to that case.

The platform already has a concept for "which part of the distributor's business is
running this deal" — the **subsidiary** (the "subsidiary record" on a quote: name,
country, language). This design gives it one more job: **saying which ERP its
portal-authored orders go to.**

One subsidiary routes to exactly one ERP connection at a time (switchable later — e.g. an
subsidiary migrating ERPs — but never two at once). When an operator issues a quote, it's
stamped with the ERP connection the issuing subsidiary currently routes to. **That stamp never
changes once the quote is issued.** Any order placed against it inherits the same target —
nothing left to figure out at order time, and the `mixed_erp`/per-line ownership check this
replaces is deleted, not kept as a fallback.

---

## 5. What changes, by role

### For the product owner

- **Operators type a product's basics directly onto each quote line** (SKU, name,
  box-or-license) instead of picking from a separately-managed catalog. One fewer screen
  ("manage items") to maintain; nothing gets harder for a one-off quote, and most quotes
  only ever use a line once anyway.
- **NetSuite-driven deals need no operator data entry at all.** A sales rep's NetSuite
  quote becomes visible to the reseller in our portal automatically — nobody re-types
  anything.
- **The ERP an order goes to is still decided once, early** — by the subsidiary for
  portal-authored quotes, or trivially by "wherever this quote came from" for
  ERP-authored ones. The reseller still never sees or picks an ERP, either way.

### For the architect

- This is a bigger move than the earlier routing fix: it removes a **shared reference
  table** (`Item`) in favor of a **denormalized, per-document copy** of product
  information — the same trade-off XChange made, and for the same reason: once the thing
  that "owns" product selection is outside our system for some channels, maintaining our
  own authoritative copy of "what a product is" stops paying for itself. For the channel
  where we're still the author (Odoo today), it costs nothing extra — an operator was
  already supplying this per quote in practice, just via a dropdown instead of a text
  field.
- **New capability, scoped but not detailed:** an ERP adapter must be able to act as a
  *source* of a quote, not just a destination for an order. This is additive to the
  `ErpAdapter` port, not a replacement — `submit`/`fetch_status`/`cancel` are unaffected;
  a new capability (something like "fetch or receive a quote") is added when NetSuite work
  actually starts, following the same inbound-webhook + reconciliation-poll shape already
  proven for order status.
- **What stays exactly as it is:** `tenant_connection_bindings`, the inbound-webhook
  reverse lookup for order status, the adapter registry, the reconciliation sweeper, and
  the subsidiary → ERP routing fix from §4 (still needed for the portal-authored path).
- **Deliberately not doing, and why:** no detailed NetSuite field mapping yet (don't know
  the real shape until that work starts); no event-sourced product/entity-resolution
  service; no attempt to keep a "cache" of what NetSuite's catalog contains on our side —
  every quote line is self-contained, so there's nothing to cache.

### For the developer

**Removed entirely:** the `reference/catalog` module — `Item`, `CatalogService`,
`ItemRepository` (memory + Postgres), `ItemOwnershipConflict`, the `items` table, the
GraphQL `syncItem` mutation and `ItemType`, and the operator UI's "Items" page.

**Changed: `QuoteLine` gains the fields `Item` used to own**

| field | today | proposed |
|---|---|---|
| `product_key` | already there | unchanged |
| `name` | — (lived on `Item`) | **new** — the product's display name, now on the line |
| `kind` | — (looked up from `Item` at order time) | **new** — `PHYSICAL`/`LICENSE`, supplied when the quote line is created |
| `unit_price`, `unit_of_measure`, `tax_rate`, `line_discount` | already there (Increment 5/ADR-0016) | unchanged |

**Changed: `OrderService._line_from_quote`**

Drops the `ItemKindLookup` dependency entirely — `kind` is copied straight from
`quote_line.kind` instead of a separate `self._items.find_by_sku(...)` call.
`OrderService.__init__` loses its `items` parameter.

**Changed: `issue_quote`**

The operator (or, later, the NetSuite adapter) supplies `name` and `kind` per line
directly, instead of referencing a pre-existing `item_id`/`sku` that had to be onboarded
first.

**New, scoped for later (not this increment):** an inbound path for ERP-authored quotes —
a new adapter method plus a webhook/reconciliation pair mirroring today's order-status
pattern. Left as a named follow-up, not designed in detail here, per §3.

**Unchanged:** the subsidiary → ERP routing fix from the previous draft (`company_erp_routes`,
`routed_to_connection_id` on `Quote`, deleting `resolve_owning_connection`/`OrderProcessor`'s
ownership-routing step) — still needed for the portal-authored path, described in full in
the previous revision and not repeated here.

---

## 6. Migration

1. Add `name` and `kind` to `QuoteLine`; `issue_quote` requires them per line.
2. Switch `OrderService._line_from_quote` to copy `kind` from the quote line; drop the
   `ItemKindLookup`/`items` dependency from `OrderService`.
3. Remove the `reference/catalog` module, its table, its GraphQL surface, and its UI page.
4. (Separately, previously scoped, independent of the above) add `company_erp_routes`,
   stamp `routed_to_connection_id` on `Quote` at issue time, delete
   `resolve_owning_connection`/`OrderProcessor`'s ownership-routing step and
   `owning_connection_id` — see the routing section (§4) for the full migration detail
   already written for this part.
5. *(Future increment, not this one)* design and build the ERP-authored quote ingestion
   path once NetSuite integration starts for real.

Steps 1–2 must land before step 3 (nothing may depend on the catalog once it's deleted).
Step 4 is independent and can land in any order relative to 1–3.

---

## 7. Review gate — RESOLVED 2026-10-05

All four open questions answered. **Construction may begin.**

1. **Backfill existing quote lines' `name`/`kind` from `items` before dropping the table?
   → No.** Only new quotes (issued after this ships) carry `name`/`kind`. Existing quotes
   show those fields blank — an accepted, explicit data-loss call, not an oversight, same
   stance already taken elsewhere in this codebase for pre-production data (e.g.
   `items.unit_price` shipped with no backfill for the same reason: this is pre-production
   tooling, not a system with real data to protect yet).
2. Does any single product ever genuinely need to be sold through more than one ERP? →
   **Moot.** The shared catalog (`Item`) was dropped entirely in a later revision of this
   same document (§4) — there's no table left for a product to be "assigned" to one ERP
   in the first place, so the question no longer applies.
3. Can one subsidiary ever need to route to **two** ERPs at once? → **No** (confirmed via the
   companion requirements doc, Question 4: `aidlc-docs/inception/requirements/multi-erp-entity-questions.md`).
   `company_erp_routes` stays one-active-route-per-subsidiary, as already designed.
4. When an subsidiary switches from one ERP to another, do quotes already issued under the old
   route keep working? → **Yes.** A quote's `routed_to_connection_id` stamp is permanent
   once issued; switching an subsidiary's active route only affects quotes issued *after* the
   switch.

Construction covers: steps 1–4 of §6 (the ERP-authored ingestion path in step 5 is its own
future increment, not blocked on this one), each with its own test, and a new ADR
recording this decision (superseding ADR-0005's item-ownership half and
ADR-0011/ADR-0016's remaining catalog-kind dependency).
