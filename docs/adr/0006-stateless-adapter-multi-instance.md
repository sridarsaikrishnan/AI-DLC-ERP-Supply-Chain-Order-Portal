# ADR-0006: Multiple instances of one ERP are data, not code

| | |
|---|---|
| Status | Accepted |
| Affects | `integration`, `connections` modules |

## In one sentence
A second instance of an already-registered ERP type (e.g. a second Odoo database) is a
new database row, not a new adapter — every adapter is stateless and reused across every
instance of its ERP type.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Resellers commonly need more than one instance of the same ERP | e.g. a separate Odoo database per region — and a tenant can be a customer in more than one instance at once |

## The decision

| | |
|---|---|
| One instance | One row in `erp_connections` — not one adapter object per instance |
| Adapters | Stateless between calls — every method takes an `ErpTarget` (`base_url`, `database`, `username`, `secret`) resolved fresh from the connection row right before the call |
| Registry | Keyed by **ERP type**, not by connection — one `OdooAdapter` instance serves every Odoo connection configured |

## Alternatives considered

| Option | Rejected because |
|---|---|
| One adapter object per connection | Unnecessary state to manage; the adapter has no reason to remember which instance it's talking to between calls |

## Consequences

| | |
|---|---|
| ✅ | Adding a second instance of an already-registered ERP type is a **pure data change** (new `erp_connections` row + binding) — zero code changes |
| ✅ | Order routing already decides *which instance* from the order's line items (`owning_connection_id`), and rejects orders that span two connections (`mixed_erp`) — one order can never straddle two ERP instances |
| ⚠️ | Assumes each instance is reachable over its own `base_url`/`database`/credentials — doesn't cover ERPs where multi-instance means something structurally different (e.g. one API endpoint, tenant-scoped by header) |

## Revisit when
A new ERP type's "multiple instances" don't fit the `base_url` + `database` + credential shape.
