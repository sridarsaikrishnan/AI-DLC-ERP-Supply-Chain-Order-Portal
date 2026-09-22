# Business Rules — U3 Integration

## BR-U3-1: Routing at Runtime
- BR-U3-1.1: Use U0 `evaluate_routing` (ordered, first-match-wins). U3 does not re-implement precedence.
- BR-U3-1.2: The selected target instance must be active; if not, treat as configuration error -> order Failed with reason.

## BR-U3-2: No-Match / Failure Handling (Q4=A)
- BR-U3-2.1: NoMatch -> order Failed, reason "no route matched" (FR-3.4). No auto-fallback.
- BR-U3-2.2: Terminal adapter failure -> order Failed with the adapter's error reason.
- BR-U3-2.3: Transient adapter failure -> raise so U0 applies bounded retry with backoff; after exhaustion the job is FAILED and the order left in its last state (a later STATUS_SYNC or manual resubmit can recover).

## BR-U3-3: Corrective Actions (Q5=A)
- BR-U3-3.1: CANCEL is rejected by the ERP (stub) if the order is already Shipped/Invoiced; the portal surfaces the reason and preserves prior state.
- BR-U3-3.2: AMEND on a non-amendable state is rejected similarly.
- BR-U3-3.3: RESUBMIT re-runs the submission pipeline; only valid from Failed state.

## BR-U3-4: Mapping Application (Q1=A)
- BR-U3-4.1: field_entries copy source->target; value_map translates discrete values; unknown values flagged.
- BR-U3-4.2: expressions treated as direct/renamed copies for MVP (no transform engine).
- BR-U3-4.3: A required target field with no mapping is a configuration error (surfaced; order Failed if it blocks submission).

## BR-U3-5: Status Reconciliation
- BR-U3-5.1: Native ERP status mapped to canonical LifecycleState via FROM_ERP value_map.
- BR-U3-5.2: Apply latest-wins; preserve full history (U0 behavior).

## BR-U3-6: Idempotency
- BR-U3-6.1: Handlers are idempotent via U0 dedupe_key (e.g., order_id + action + attempt-version) so retries never double-submit to the ERP.
