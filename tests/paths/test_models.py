from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from routemind.domain.models import Location, TransportLeg, TransportMode
from routemind.paths import CandidatePath


def leg(option_id: str, origin: Location, destination: Location, departure: datetime, arrival: datetime) -> TransportLeg:
    return TransportLeg(
        option_id=option_id,
        origin=origin,
        destination=destination,
        departure_at=departure,
        arrival_at=arrival,
        allocated_weight_kg=1,
        allocated_volume_m3=0.01,
    )


def candidate(legs: tuple[TransportLeg, ...]) -> CandidatePath:
    return CandidatePath(
        shipment_id="S1",
        legs=legs,
        total_cost=Decimal("100"),
        currency="KES",
        transit_seconds=sum((item.arrival_at - item.departure_at).total_seconds() for item in legs),
        waiting_seconds=0,
        number_of_transfers=len(legs) - 1,
        reliability=0.95,
        modes=tuple(TransportMode.BUS for _ in legs),
        providers=tuple("P1" for _ in legs),
        capacity_utilization=0.5,
        deadline_feasible=True,
    )


def test_candidate_requires_continuous_legs():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    a, b, c = Location(id="a", name="A"), Location(id="b", name="B"), Location(id="c", name="C")

    with pytest.raises(ValueError, match="continuous"):
        candidate((leg("AB", a, b, t, t + timedelta(hours=1)), leg("AC", a, c, t + timedelta(hours=2), t + timedelta(hours=3))))


def test_candidate_rejects_overlapping_legs():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    a, b, c = Location(id="a", name="A"), Location(id="b", name="B"), Location(id="c", name="C")

    with pytest.raises(ValueError, match="overlap"):
        candidate((leg("AB", a, b, t, t + timedelta(hours=2)), leg("BC", b, c, t + timedelta(hours=1), t + timedelta(hours=3))))


def test_candidate_rejects_incorrect_transfer_count():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    a, b = Location(id="a", name="A"), Location(id="b", name="B")

    with pytest.raises(ValueError, match="number_of_transfers"):
        CandidatePath(
            shipment_id="S1",
            legs=(leg("AB", a, b, t, t + timedelta(hours=1)),),
            total_cost=Decimal("100"),
            currency="KES",
            transit_seconds=3600,
            waiting_seconds=0,
            number_of_transfers=1,
            reliability=0.95,
            modes=(TransportMode.BUS,),
            providers=("P1",),
            capacity_utilization=0.5,
            deadline_feasible=True,
        )
