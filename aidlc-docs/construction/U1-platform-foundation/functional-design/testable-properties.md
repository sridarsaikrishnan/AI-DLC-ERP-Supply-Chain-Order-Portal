# Testable Properties (PBT-01) — U1 Platform Foundation

Property identification for the property-based testing extension (full enforcement, jqwik). Each property maps to a category and the rule/mechanism it guards. Example-based tests still pin business-critical cases (PBT-10); these state the general invariants.

| # | Property | Category | Guards |
|---|---|---|---|
| P-U1-01 | **ID round-trip**: parse(format(id)) == id for every prefixed ULID/UUIDv7 id; prefixes are stable per type | Round-trip | BR-U1-08 |
| P-U1-02 | **Money invariants**: sum of line totals == subtotal; totals never negative; currency preserved across arithmetic; no precision loss (BigDecimal) | Invariant | BR-U1-09 |
| P-U1-03 | **Event sourcing replay determinism**: for any valid command sequence, folding the resulting `Order` event stream yields identical state regardless of replay batching | Oracle / Induction | BR-U1-16 |
| P-U1-04 | **Snapshot-equivalence (future-proof)**: state from (snapshot + tail) == state from full replay (property holds even though snapshotting is off in MVP) | Oracle | BR-U1-17 |
| P-U1-05 | **Projection consistency**: a projection rebuilt from scratch equals the incrementally-updated projection for the same event stream | Oracle | CQRS, NFR-13 |
| P-U1-06 | **Idempotent event handling**: applying the same event (same `eventId`) twice to a projector yields the same read model as applying it once | Idempotence | BR-U1-18 |
| P-U1-07 | **Tenant-scope invariant**: for any generated multi-tenant dataset and query, results contain only rows of the caller's tenant (app filter and, separately, RLS) | Invariant | BR-U1-01/02 |
| P-U1-08 | **No-ERP-identity invariant**: for any canonical entity, its reseller DTO serialization contains none of {connectionId, erpCustomerId, erpOrderId, instanceLabel, ERP type} | Invariant | BR-U1-06 |
| P-U1-09 | **Sealed error totality**: every failure maps to exactly one `CanonicalError` code; reseller messages never contain raw ERP text (checked over generated error inputs) | Invariant | BR-U1-07 |
| P-U1-10 | **Binding uniqueness**: no generated sequence of binding operations can create two bindings for the same (tenant, connection) or bind one ERP customer to two tenants | Invariant (stateful) | BR-U1-11, AC-05 |
| P-U1-11 | **Item single-owner**: after any sync sequence, each sku has at most one owner or is flagged conflict — never silently two owners | Invariant (stateful) | BR-U1-13, AC-06 |
| P-U1-12 | **Credential encryption round-trip**: decrypt(encrypt(secret, keyId)) == secret; ciphertext never equals plaintext; keyId recoverable | Round-trip | BR-U1-20 |
| P-U1-13 | **Concurrency safety**: concurrent optimistic-locked updates to a reference aggregate never lose an update silently (one wins, others retry/fail) | Invariant (stateful) | BR-U1-15 |

Notes:
- Generators must be domain-aware (PBT-07): valid currencies, positive quantities, structurally-valid orders, realistic tenant/connection graphs.
- Shrinking enabled; seed logged every run; PBT runs in CI (PBT-08).
- Stateful properties (P-U1-10/11/13) use a simplified model compared against the real component over random command sequences (PBT-06).
