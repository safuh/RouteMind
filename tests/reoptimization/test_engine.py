from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location,
    Package,
    Shipment,
    TransportCapacity,
    TransportLeg,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.optimization import optimize_portfolio
from routemind.paths.models import CandidatePath
from routemind.reoptimization import DisruptionEvent, DisruptionType, reoptimize_portfolio


def _option(id_: str, origin: Location, destination: Location, departure: datetime, cost: str, capacity: float = 100) -> TransportOption:
    return TransportOption(
        id=id_, provider_id="P", provider_name="Synthetic", mode=TransportMode.BUS,
        origin=origin, destination=destination,
        capacity=TransportCapacity(max_weight_kg=capacity, max_volume_m3=10),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=departure + timedelta(hours=3), available_weight_kg=capacity)],
        price=TransportPrice(model="fixed", amount=Decimal(cost), currency="KES"), reliability=.95,
    )


def _path(shipment_id: str, option_id: str, origin: Location, destination: Location, departure: datetime, cost: str, weight: float = 10) -> CandidatePath:
    leg = TransportLeg(option_id=option_id, origin=origin, destination=destination, departure_at=departure, arrival_at=departure + timedelta(hours=3), allocated_weight_kg=weight, allocated_volume_m3=.008)
    return CandidatePath(
        shipment_id=shipment_id, legs=(leg,), total_cost=Decimal(cost), currency="KES",
        transit_seconds=10800, waiting_seconds=0, number_of_transfers=0, reliability=.95,
        modes=(TransportMode.BUS,), providers=("P",), capacity_utilization=weight / 100,
        deadline_feasible=True,
    )


def _shipment(id_: str, origin: Location, destination: Location, ready_at: datetime) -> Shipment:
    return Shipment(
        id=id_, origin=origin, destination=destination,
        packages=[Package(id=f"P-{id_}", weight_kg=10, length_m=.2, width_m=.2, height_m=.2)],
        ready_at=ready_at - timedelta(hours=1), deadline=ready_at + timedelta(hours=8),
    )


def test_cancellation_replaces_only_impacted_plan_and_preserves_other_assignments():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    options = {
        "CANCELLED": _option("CANCELLED", nbo, nku, departure, "10"),
        "A-ALT": _option("A-ALT", nbo, nku, departure, "20"),
        "B-KEEP": _option("B-KEEP", nbo, nku, departure, "30"),
    }
    original_paths = [_path("A", "CANCELLED", nbo, nku, departure, "10"), _path("B", "B-KEEP", nbo, nku, departure, "30")]
    current = optimize_portfolio(original_paths, options)
    recovery = reoptimize_portfolio(
        current, original_paths, options,
        DisruptionEvent(id="E-1", occurred_at=departure, type=DisruptionType.SERVICE_CANCELLATION, option_id="CANCELLED"),
        shipments=[_shipment("A", nbo, nku, departure), _shipment("B", nbo, nku, departure)],
    )

    assert recovery.result.feasible
    assert {plan.shipment_id: plan.legs[0].option_id for plan in recovery.result.plans} == {"A": "A-ALT", "B": "B-KEEP"}
    assert recovery.impact.impacted_shipment_ids == ["A"]
    assert recovery.impact.preserved_shipment_ids == ["B"]
    assert recovery.impact.invalidated_candidate_count == 1
    assert any(entry.action == "recovery_candidates_discovered" for entry in recovery.audit_trail)


def test_schedule_delay_rediscovers_a_path_with_the_updated_schedule():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    options = {"BUS": _option("BUS", nbo, nku, departure, "10")}
    paths = [_path("A", "BUS", nbo, nku, departure, "10")]
    current = optimize_portfolio(paths, options)

    recovery = reoptimize_portfolio(
        current, paths, options,
        DisruptionEvent(
            id="E-DELAY", occurred_at=departure, type=DisruptionType.SCHEDULE_DELAY,
            option_id="BUS", schedule_departure_at=departure, delay_seconds=3600,
        ),
        shipments=[_shipment("A", nbo, nku, departure)],
    )

    assert recovery.result.feasible
    assert recovery.result.plans[0].legs[0].departure_at == departure + timedelta(hours=1)


def test_capacity_reduction_requires_recovery_when_no_replacement_path_exists():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    options = {"BUS": _option("BUS", nbo, nku, departure, "10", capacity=20)}
    paths = [_path("A", "BUS", nbo, nku, departure, "10")]
    current = optimize_portfolio(paths, options)

    recovery = reoptimize_portfolio(
        current, paths, options,
        DisruptionEvent(id="E-2", occurred_at=departure, type=DisruptionType.CAPACITY_REDUCTION, option_id="BUS", available_weight_kg=5),
    )

    assert not recovery.result.feasible
    assert recovery.result.warnings == ["Recovery requires replacement candidate paths for: A."]


def test_new_order_is_inserted_with_existing_assignment_and_shared_capacity_enforced():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    options = {
        "SHARED": _option("SHARED", nbo, nku, departure, "10", capacity=15),
        "FALLBACK": _option("FALLBACK", nbo, nku, departure, "30"),
    }
    original = [_path("A", "SHARED", nbo, nku, departure, "10")]
    current = optimize_portfolio(original, options)
    all_paths = original + [_path("B", "SHARED", nbo, nku, departure, "10"), _path("B", "FALLBACK", nbo, nku, departure, "30")]

    recovery = reoptimize_portfolio(
        current, all_paths, options,
        DisruptionEvent(id="E-3", occurred_at=departure, type=DisruptionType.NEW_ORDER, new_shipment_id="B"),
    )

    assert recovery.result.feasible
    assert {plan.shipment_id: plan.legs[0].option_id for plan in recovery.result.plans} == {"A": "SHARED", "B": "FALLBACK"}
    assert recovery.impact.impacted_shipment_ids == []
    assert recovery.impact.preserved_shipment_ids == ["A"]
