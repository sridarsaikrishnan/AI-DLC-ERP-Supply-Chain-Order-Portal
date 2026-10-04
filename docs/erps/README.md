# ERP knowledge base

One file per ERP this platform talks to — everything about *that specific ERP* in one
place: how its API works, how our adapter drives it, what its status values mean, what
we've learned the hard way, and where the rest of its documentation lives.

This folder is concrete facts about each ERP. It is deliberately **not** where the
generic, ERP-agnostic process lives — that stays put, and these files link to it instead
of repeating it:

- **`docs/adding-an-erp.md`** — the 4-step checklist for registering any new ERP type.
- **`docs/erp-integration-patterns.md`** — webhook shapes (rich vs. thin) and how
  multiple instances/tenants get routed, as concepts that apply to every ERP.

The canonical-field ↔ ERP-field mapping tables live **in each ERP's own page here** (e.g.
`odoo.md`'s outbound/inbound tables), not in a separate `mapping/` folder.

## Files

| ERP | Status | File |
|---|---|---|
| Odoo | Live, real adapter | [`odoo.md`](./odoo.md) |
| ERPNext | Not registered (removed pending clean re-add — see `docs/adding-an-erp.md`) | — |
| NetSuite | Not registered | — |

## Adding a new ERP's page

Copy `odoo.md`'s section headings. At minimum, cover:
1. What the ERP is and how connections to it are configured (which fields on
   `ErpConnection` map to what).
2. How authentication works against its API.
3. What our adapter actually does for `submit` / `fetch_status` / `cancel` — in plain
   English, not just "see the code".
4. The outbound/inbound field-mapping tables (canonical ↔ this ERP's fields).
5. Every quirk, gap, or surprising behavior discovered while building or running it
   against a real instance — this is the part that has no other home. If you find out
   something the hard way, it belongs here so the next person doesn't re-discover it.
6. Links out: the webhook setup doc (if any), local dev setup.
