# ADR-0012: ERP connection credentials are a generic bag, not fixed fields

| | |
|---|---|
| Status | Accepted — implemented |
| Affects | `connections` module, `integration` module |

## In one sentence
`ErpConnection`/`ErpTarget` carry a generic `credentials: dict[str, str]` instead of
fixed `database`/`username` fields — Odoo's own login shape, which every future ERP was
otherwise forced to fit whether it needed those fields or not.

## Why this needed a decision

| Problem | Detail |
|---|---|
| "Generic" connection shape was actually Odoo-shaped | `database` + `username` are exactly what Odoo's `common.authenticate` needs. NetSuite's OAuth (token-based auth or OAuth2) has no database name and no username/password at all; ERPNext uses an API key/secret pair. A fixed-field struct has no natural slot for either. |
| This was discovered by inspection, not theory | Found while reviewing the adapter seam for Odoo-specific leakage (alongside the status-mapper signature, fixed separately — see ADR-0003's note on the field-bag mapper). |

## The decision
`ErpConnection.credentials` and `ErpTarget.credentials` are both `dict[str, str]`.
`secret_ref`/`secret` (the one value that's always actually secret) stay separate, named
fields — resolved via Secrets Manager, never put in the generic bag. Each adapter defines
what keys it expects: Odoo reads `credentials["database"]`/`credentials["username"]`; a
future NetSuite adapter might read `credentials["account_id"]` and nothing else.

Storage: `erp_connections.credentials` is a JSONB column (migration `0006`), replacing
the old `database`/`username` text columns — existing rows' values are moved into the new
column by the migration itself, not dropped.

API/UI: the GraphQL `registerConnection` mutation takes `credentials: JSON` instead of
named `database`/`username` arguments. The UI's connection form still shows "Database"/
"Username" labeled inputs today (the only reason: Odoo is the only registered ERP) but
packs them into a `credentials` object before calling the mutation — a future ERP's
connection form sends whatever keys it actually needs, no schema change required.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Keep `database`/`username`, add new optional fields per future ERP as needed | Each new ERP with a different auth shape adds more unused nullable columns to every connection row, forever — the problem compounds instead of resolving |
| A `credentials` column, but keep `database`/`username` too, both populated | Two sources of truth for the same information; an adapter reading the "wrong" one is a real bug waiting to happen |

## Consequences

| | |
|---|---|
| ✅ | A future ERP's auth shape is never blocked by this struct — it just uses different dict keys |
| ✅ | `erp_connections` doesn't accumulate unused nullable columns as more ERP types are added |
| ⚠️ | Lost compile-time field names — `credentials["database"]` typos fail at runtime, not at the type-checker. Acceptable: each adapter is the only reader of its own keys, and this trades a small, local risk for not re-fixing the schema every time a new ERP's auth shape doesn't match Odoo's. |

## Revisit when
A credential shape needs structure beyond flat string key-value pairs (e.g. a nested
OAuth token-refresh state machine) — at that point a per-adapter credential object is a
real option, not just a dict.
