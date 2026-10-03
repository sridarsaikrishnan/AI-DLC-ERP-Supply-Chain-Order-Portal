# ADR-0009: One identity provider for humans and machine-to-machine

| | |
|---|---|
| Status | Accepted |
| Affects | `src/shared/identity`, `api` |

## In one sentence
Cognito is the single token issuer for both human logins and machine-to-machine clients —
one claims model, one validation path, for both audiences.

## Why this needed a decision

| Problem | Detail |
|---|---|
| Two kinds of caller hit the API | Human users (reseller/operator staff logging in) and machine clients (system-to-system integrations) |

## The decision

| | |
|---|---|
| Humans | Standard ID-token flow |
| Machines | OAuth2 `client_credentials` against the same Cognito user pool |
| Claims | Tenant from `custom:tenant_id`, roles from `cognito:groups` — one model for both |

## Alternatives considered

| Option | Rejected because |
|---|---|
| Separate issuers per audience (e.g. a different provider for M2M) | More moving parts (two sets of signing keys, two validation paths) for no current requirement that justifies the split |

## Consequences

| | |
|---|---|
| ✅ | One token validation path in the API — no branching on "which issuer signed this" |
| ✅ | One place to manage password policy, MFA, and lockout rules |
| ⚠️ | Couples human and machine auth lifecycle to the same provider — if M2M auth ever needs different guarantees (e.g. per-integration key rotation independent of user pool policy), splitting later is a bigger change than if they'd started separate |

## Revisit when
Machine-to-machine auth needs guarantees that would compromise the human-auth
configuration, or vice versa.
