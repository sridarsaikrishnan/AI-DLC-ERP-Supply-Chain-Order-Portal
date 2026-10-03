"""Property-based tests for the delivered-fact rule (Increment 5, FR-D2 / Q7=A PBT).

The rule (`line_is_delivered`) is pure and shared by the aggregate and the projection, so
it's the natural PBT target: a license is always delivered on ship; a physical good is
delivered iff a carrier or proof-of-delivery is present.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from src.modules.ordering.domain.models import KIND_LICENSE, KIND_PHYSICAL, line_is_delivered

_evidence = st.one_of(st.none(), st.text(min_size=1, max_size=8))
_empty_or_none = st.one_of(st.none(), st.just(""))


@given(carrier=_evidence, pod=_evidence)
def test_license_is_always_delivered_on_ship(carrier, pod) -> None:
    assert line_is_delivered(KIND_LICENSE, carrier, pod) is True


@given(carrier=_empty_or_none, pod=_empty_or_none)
def test_physical_without_evidence_is_not_delivered(carrier, pod) -> None:
    assert line_is_delivered(KIND_PHYSICAL, carrier, pod) is False


@given(
    carrier=st.text(min_size=1, max_size=8),
    pod=_evidence,
)
def test_physical_with_a_carrier_is_delivered(carrier, pod) -> None:
    assert line_is_delivered(KIND_PHYSICAL, carrier, pod) is True


@given(pod=st.text(min_size=1, max_size=8))
def test_physical_with_proof_of_delivery_is_delivered(pod) -> None:
    assert line_is_delivered(KIND_PHYSICAL, None, pod) is True
