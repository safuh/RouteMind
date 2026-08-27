from datetime import UTC, datetime
from decimal import Decimal

from routemind.consolidation.time_windows import check_group_time_windows, check_path_time_window
from routemind.domain.models import Location, Package, Shipment, TransportLeg, TransportMode
from routemind.paths.models import CandidatePath


def make_shipment(ready: datetime, deadline: datetime | None) -> Shipment:
    location = Location(id="A", name="A")
    return Shipment(
        id="S1", origin=location, destination=location,
        packages=[Package(id="P1", weight_kg=1, length_m=.1, width_m=.1, height_m=.1)],
        ready_at=ready, deadline=deadline,
    )


def make_path(departure: datetime, arrival: datetime, deadline_feasible: bool = True) -> CandidatePath:
    location_a = Location(id="A", name="A")
    location_b = Location(id="B", name="B")
    leg = TransportLeg(
        option_id="T1", origin=location_a, destination=location_b,
        departure_at=departure, arrival_at=arrival,
    )
    return CandidatePath(
        shipment_id="S1", legs=(leg,), total_cost=Decimal("10"), currency="KES",
        transit_seconds=(arrival - departure).total_seconds(), waiting_seconds=0,
        number_of_transfers=0, reliability=1, modes=(TransportMode.TRUCK,),
        providers=("P1",), capacity_utilization=0, deadline_feasible=deadline_feasible,
    )


def test_ready_time_must_precede_departure():
    ready = datetime(2026, 8, 27, 10, tzinfo=UTC)
    path = make_path(datetime(2026, 8, 27, 9, tzinfo=UTC), datetime(2026, 8, 27, 11, tzinfo=UTC))
    assert len(check_path_time_window(path, make_shipment(ready, None))) == 1


def test_arrival_must_not_exceed_deadline():
    departure = datetime(2026, 8, 27, 9, tzinfo=UTC)
    path = make_path(departure, datetime(2026, 8, 27, 13, tzinfo=UTC))
    shipment = make_shipment(datetime(2026, 8, 27, 8, tzinfo=UTC), datetime(2026, 8, 27, 12, tzinfo=UTC))
    assert len(check_path_time_window(path, shipment)) == 1


def test_valid_path_has_no_time_window_rejections():
    departure = datetime(2026, 8, 27, 9, tzinfo=UTC)
    path = make_path(departure, datetime(2026, 8, 27, 11, tzinfo=UTC))
    shipment = make_shipment(datetime(2026, 8, 27, 8, tzinfo=UTC), datetime(2026, 8, 27, 12, tzinfo=UTC))
    assert check_group_time_windows((path,), {"S1": shipment}) == ()


def test_preexisting_deadline_infeasible_flag_is_preserved():
    departure = datetime(2026, 8, 27, 9, tzinfo=UTC)
    path = make_path(departure, datetime(2026, 8, 27, 11, tzinfo=UTC), deadline_feasible=False)
    shipment = make_shipment(datetime(2026, 8, 27, 8, tzinfo=UTC), datetime(2026, 8, 27, 12, tzinfo=UTC))
    assert len(check_group_time_windows((path,), {"S1": shipment})) == 1
