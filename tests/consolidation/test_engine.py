from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.consolidation import (
    ConsolidationRejectionReason,
    detect_shared_segments,
    evaluate_consolidation,
)
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
from routemind.paths.models import CandidatePath


def loc(id_: str, name: str) -> Location:
    return Location(id=id_, name=name)


def shipment(id_: str, origin: Location, destination: Location, weight: float = 10) -> Shipment:
    return Shipment(
        id=id_,
        origin=origin,
        destination=destination,
        packages=[Package(id=f"P-{id_}", weight_kg=weight, length_m=0.2, width_m=0.2, height_m=0.2)],
        ready_at=datetime(2026, 8, 27, 7, tzinfo=UTC),
        deadline=datetime(2026, 8, 27, 20, tzinfo=UTC),
    )


def option(
    id_: str,
    origin: Location,
    destination: Location,
    departure: datetime,
    arrival: datetime,
    *,
    weight: float = 100,
    volume: float = 10,
    price_model: str = "fixed",
    amount: str = "100",
    restrictions: set[str] | None = None,
) -> TransportOption:
    return TransportOption(
        id=id_,
        provider_id=f"PROVIDER-{id_}",
        provider_name=f"Provider {id_}",
        mode=TransportMode.TRUCK,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=weight, max_volume_m3=volume),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=arrival)],
        price=TransportPrice(model=price_model, amount=Decimal(amount), currency="KES"),
        reliability=0.95,
        restrictions=restrictions or set(),
    )


def path(shipment_id: str, legs: list[TransportLeg], cost: str = "100") -> CandidatePath:
    return CandidatePath(
        shipment_id=shipment_id,
        legs=tuple(legs),
        total_cost=Decimal(cost),
        currency="KES",
        transit_seconds=sum((leg.arrival_at - leg.departure_at).total_seconds() for leg in legs),
        waiting_seconds=0,
        number_of_transfers=len(legs) - 1,
        reliability=0.95,
        modes=tuple(TransportMode.TRUCK for _ in legs),
        providers=tuple("P" for _ in legs),
        capacity_utilization=0.2,
        deadline_feasible=True,
    )


def leg(option_id: str, origin: Location, destination: Location, departure: datetime, arrival: datetime, weight: float = 10) -> TransportLeg:
    return TransportLeg(
        option_id=option_id,
        origin=origin,
        destination=destination,
        departure_at=departure,
        arrival_at=arrival,
        allocated_weight_kg=weight,
        allocated_volume_m3=0.008,
    )


def test_same_scheduled_service_is_detected_and_capacity_is_aggregated():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, ksm = loc("nbo", "Nairobi"), loc("ksm", "Kisumu")
    service = option("BUS-001", nbo, ksm, t, t + timedelta(hours=5), weight=30)
    a, b = shipment("A", nbo, ksm, 10), shipment("B", nbo, ksm, 15)
    paths = [path("A", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))]), path("B", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))])]

    detected = detect_shared_segments(paths)
    result = evaluate_consolidation(paths, {"A": a, "B": b}, {service.id: service})

    assert len(detected) == 1
    assert len(next(iter(detected.values()))) == 2
    assert result.feasible
    assert result.total_weight_kg == 25
    assert result.weight_capacity_kg == 30


def test_different_destinations_can_share_first_segment_but_keep_paths_distinct():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku, ksm, eld = [loc(i, n) for i, n in [("nbo", "Nairobi"), ("nku", "Nakuru"), ("ksm", "Kisumu"), ("eld", "Eldoret")]]
    shared = option("TRUCK-001", nbo, nku, t, t + timedelta(hours=3))
    p_a = path("A", [leg("TRUCK-001", nbo, nku, t, t + timedelta(hours=3)), leg("KSM", nku, ksm, t + timedelta(hours=4), t + timedelta(hours=7))])
    p_b = path("B", [leg("TRUCK-001", nbo, nku, t, t + timedelta(hours=3)), leg("ELD", nku, eld, t + timedelta(hours=4), t + timedelta(hours=7))])

    detected = detect_shared_segments([p_a, p_b])

    assert len(detected) == 1
    assert next(iter(detected.values()))[0].destination_id == "nku"
    assert p_a.option_ids != p_b.option_ids
    assert shared.id in p_a.option_ids and shared.id in p_b.option_ids


def test_capacity_rejects_overweight_group_with_structured_reason():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    service = option("TRUCK-001", nbo, nku, t, t + timedelta(hours=3), weight=20)
    shipments = {"A": shipment("A", nbo, nku, 12), "B": shipment("B", nbo, nku, 12)}
    paths = [path("A", [leg("TRUCK-001", nbo, nku, t, t + timedelta(hours=3))]), path("B", [leg("TRUCK-001", nbo, nku, t, t + timedelta(hours=3))])]

    result = evaluate_consolidation(paths, shipments, {service.id: service})

    assert not result.feasible
    assert result.savings == Decimal("100")
    assert result.rejections[0].reason == ConsolidationRejectionReason.CAPACITY_WEIGHT


def test_schedule_specific_capacity_is_used():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    service = option("BUS-001", nbo, nku, t, t + timedelta(hours=3), weight=100)
    service.schedules[0].available_weight_kg = 15
    shipments = {"A": shipment("A", nbo, nku, 8), "B": shipment("B", nbo, nku, 8)}
    paths = [path("A", [leg("BUS-001", nbo, nku, t, t + timedelta(hours=3))]), path("B", [leg("BUS-001", nbo, nku, t, t + timedelta(hours=3))])]

    result = evaluate_consolidation(paths, shipments, {service.id: service})

    assert not result.feasible
    assert result.weight_capacity_kg == 15


def test_cargo_restrictions_are_reused_from_domain_policy():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    service = option("BUS-001", nbo, nku, t, t + timedelta(hours=3), restrictions={"no_fragile"})
    fragile = shipment("A", nbo, nku)
    fragile.packages[0].fragile = True
    normal = shipment("B", nbo, nku)
    paths = [path("A", [leg("BUS-001", nbo, nku, t, t + timedelta(hours=3))]), path("B", [leg("BUS-001", nbo, nku, t, t + timedelta(hours=3))])]

    result = evaluate_consolidation(paths, {"A": fragile, "B": normal}, {service.id: service})

    assert not result.feasible
    assert any(r.reason == ConsolidationRejectionReason.CARGO_INCOMPATIBILITY for r in result.rejections)


def test_fixed_price_consolidation_creates_savings():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, ksm = loc("nbo", "Nairobi"), loc("ksm", "Kisumu")
    service = option("BUS-001", nbo, ksm, t, t + timedelta(hours=5), price_model="fixed", amount="100")
    shipments = {"A": shipment("A", nbo, ksm), "B": shipment("B", nbo, ksm)}
    paths = [path("A", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))]), path("B", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))])]

    result = evaluate_consolidation(paths, shipments, {service.id: service})

    assert result.feasible
    assert result.standalone_shared_segment_cost == Decimal("200")
    assert result.consolidated_shared_segment_cost == Decimal("100")
    assert result.savings == Decimal("100")


def test_variable_pricing_remains_additive_and_can_have_zero_savings():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, ksm = loc("nbo", "Nairobi"), loc("ksm", "Kisumu")
    service = option("BUS-001", nbo, ksm, t, t + timedelta(hours=5), price_model="per_kg", amount="10")
    shipments = {"A": shipment("A", nbo, ksm, 10), "B": shipment("B", nbo, ksm, 5)}
    paths = [path("A", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))]), path("B", [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))])]

    result = evaluate_consolidation(paths, shipments, {service.id: service})

    assert result.feasible
    assert result.savings == Decimal("0")


def test_three_shipments_are_aggregated_as_a_group_not_pairwise_only():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, ksm = loc("nbo", "Nairobi"), loc("ksm", "Kisumu")
    service = option("BUS-001", nbo, ksm, t, t + timedelta(hours=5), weight=40)
    shipments = {item: shipment(item, nbo, ksm, 10) for item in ("A", "B", "C")}
    paths = [path(item, [leg("BUS-001", nbo, ksm, t, t + timedelta(hours=5))]) for item in shipments]

    result = evaluate_consolidation(paths, shipments, {service.id: service})

    assert result.feasible
    assert result.shipment_ids == ("A", "B", "C")
    assert result.total_weight_kg == 30
    assert result.total_package_count == 3
