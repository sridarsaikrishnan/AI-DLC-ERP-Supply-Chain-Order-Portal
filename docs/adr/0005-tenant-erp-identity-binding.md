# ADR-0005: Tenant↔ERP identity via a binding table, not a resolver service

| | |
|---|---|
| Status | Accepted |
| Affects | `tenancy`, `catalog` modules |

## In one sentence
Two fixed 1:1 relationships (tenant↔ERP-customer, item↔connection) are resolved by a
foreign key with a database uniqueness constraint — not a dedicated identity-resolution
service.

## Why this needed a decision

| Problem | Detail |
|---|---|
| A reseller needs matching to their ERP customer record | And an inbound ERP webhook needs to route back to the right tenant unambiguously |
| A product needs matching to the one ERP that owns it | So an order for that SKU goes to exactly one connection |

## The decision
`tenant_connection_bindings` links `tenant_id` ↔ `connection_id` ↔ `erp_customer_id`, with
two DB-level uniqueness rules:

| Rule | What it guarantees |
|---|---|
| A tenant has at most one binding per connection | No ambiguity about which customer record a tenant's order maps to |
| An ERP customer ID maps to at most one tenant | An inbound webhook always resolves to exactly one reseller |

`Item.owning_connection_id` does the same job for products — which connection owns a given SKU.

## Alternatives considered

| Option | Rejected because |
|---|---|
| A dedicated identity-resolution service | Only two relationships ever need resolving (tenant↔ERP-customer, item↔connection), both naturally 1:1 — a foreign key with a uniqueness constraint already **is** the resolution, no service needed |

## Consequences

| | |
|---|---|
| ✅ | Resolution is enforced at the database level, not application logic — can't drift out of sync |
| ✅ | Zero extra infrastructure or network hop to resolve an identity |
| ⚠️ | Only works because there are exactly two fixed relationship types — doesn't generalize to an arbitrary graph of systems each knowing an entity by their own ID |

## Revisit when
A tenant's ERP customer ID becomes genuinely ambiguous, or identity needs resolving across
more than two systems for the same order.
