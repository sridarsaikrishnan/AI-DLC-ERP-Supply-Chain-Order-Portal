# ADR-0015: `ErpCapabilities` is declared now, gated later

| | |
|---|---|
| Status | Accepted — implemented (declaration only) |
| Affects | `integration` module |

## In one sentence
Every `ErpAdapter` declares a `capabilities: frozenset[str]` — what it actually uses from
the canonical payload — but nothing reads it to change behavior yet; that's deferred
until a second real adapter exists to actually differ from Odoo.

## Why this needed a decision
With only one adapter ever registered, a capability-gating system designed now would be
guessing its axes from a sample size of one — exactly the over-engineering this platform
has otherwise avoided (ADR-0003 rejected a declarative mapping engine for the same
reason). But leaving the *concept* undeclared means every future adapter's "what do I
support" stays implicit in its own code, unreadable without reading that adapter.

## The decision
`ErpAdapter.capabilities` is a required attribute (not yet a gating mechanism). `OdooAdapter`
declares `{"tax", "uom", "idempotency", "fail_closed_product"}` — matching exactly what it
does today (ADR-0011, ADR-0013, and the idempotency/fail-closed work). `StubErpAdapter`
declares `frozenset()` — it's a deterministic fake, not a real integration, and says so.
`DeliveryHandler` logs the capability set at submit time (`log.debug`), so a gap is
visible in context, but the full canonical payload is still built and handed to every
adapter regardless — no field is withheld because an adapter "doesn't support" it.

## Alternatives considered

| Option | Rejected because |
|---|---|
| Build real gating logic now (e.g. skip building tax fields if `"tax" not in capabilities`) | There's no second adapter to prove the gating actually fits a real different shape — building it now is designing against a hypothesis, not a requirement |
| Skip declaring capabilities until gating is built | Leaves "what does this adapter support" as tribal knowledge locked in each adapter's source — the declaration costs one line per adapter and is useful on its own as documentation |

## Consequences

| | |
|---|---|
| ✅ | A capability gap is now a one-line, inspectable fact (`OdooAdapter.capabilities`) instead of something only discoverable by reading `submit()` end to end |
| ✅ | Zero behavioral risk — nothing changed for Odoo; this is additive |
| ⚠️ | Not load-bearing yet — a future adapter could declare capabilities incorrectly and nothing would catch the mismatch, since nothing checks it against actual behavior |

## Revisit when
A second real adapter is registered — that's the point this ADR itself named as the
trigger to design real gating logic, informed by an actual second shape instead of a guess.
