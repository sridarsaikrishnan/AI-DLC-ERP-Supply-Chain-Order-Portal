# Unit Test Execution

## Run Unit Tests
```bash
pip install -r requirements.txt
pytest
```

## Test Inventory (DB-free — run anywhere with Python 3.11+)
- `tests/foundation/test_validator.py` — canonical validation (BR-1)
- `tests/foundation/test_routing.py` — routing precedence / no-match / operators
- `tests/foundation/test_property_based.py` — Hypothesis: validation invariant + canonical JSON round-trip (partial PBT scope)
- `tests/identity/test_token_and_authz.py` — token round-trip, TOTP, authorization matrix, context resolution
- `tests/integration/test_mapping_and_routing.py` — mapping (value map + nested), adapter registry/submit, cancel-after-shipped
- `tests/ordering/test_ordering.py` — catalog seed, canonical validation gate
- `tests/admin/test_admin_service.py` — mapping completeness report

## Expected
- All listed unit tests pass with no external services (they exercise pure logic and in-memory stubs).
- Coverage target: not enforced for MVP (best-effort).

## If Tests Fail
1. Review pytest output.
2. Fix code; rerun `pytest`.
