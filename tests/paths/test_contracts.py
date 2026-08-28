from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from routemind.domain.models import Location, TransportLeg, TransportMode
from routemind.paths import CandidatePath
from routemind.paths.contracts import CandidatePathContract, serialize_candidate_paths


def test_domain_candidate_serializes_to_complete_tool_contract():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    origin = Location(id="NBO", name="Nairobi")
    destination = Location(id="NKR", name="Nakuru")
    path = CandidatePath(
        shipment_id="S1",
        legs=(TransportLeg(option_id="bus-1", origin=origin, destination=destination, departure_at=t, arrival_at=t + timedelta(hours=3), allocated_weight_kg=10, allocated_volume_m3=.2),),
        total_cost=Decimal("500"), currency="KES", transit_seconds=10800, waiting_seconds=0,
        number_of_transfers=0, reliability=.95, modes=(TransportMode.BUS,), providers=("P1",),
        capacity_utilization=.1, deadline_feasible=True,
    )
    result = CandidatePathContract.from_domain(path)
    assert result.legs[0].origin.id == "NBO"
    assert result.legs[0].departure_at == t.isoformat()
    assert result.total_cost == Decimal("500")


def test_contract_rejects_legacy_partial_payload():
    with pytest.raises(ValidationError):
        CandidatePathContract.model_validate({
            "path_id": "path_courier_direct",
            "legs": [{"leg_id": "leg_courier", "origin": None, "destination": None}],
        })


def test_serialization_never_constructs_candidates_from_partial_tool_input():
    with pytest.raises(AttributeError):
        serialize_candidate_paths([{"path_id": "legacy"}])  # type: ignore[list-item]
