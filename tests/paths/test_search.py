from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location,
    Package,
    Shipment,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.paths import PathSearchConfig, PathSearchEngine


def loc(id_: str, name: str) -> Location:
    return Location(id=id_, name=name)


def service(
    id_: str,
    origin: Location,
    destination: Location,
    mode: TransportMode,
    departure: datetime,
    hours: int,
    weight: float = 100,
    *,
    price: Decimal = Decimal("100"),
    restrictions: set[str] | None = None,
    provider_id: str | None = None,
    schedule_weight: float | None = None,
) -> TransportOption:
    return TransportOption(
        id=id_,
        provider_id=provider_id or f"P-{id_}",
        provider_name=f"Provider {id_}",
        mode=mode,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=weight, max_volume_m3=2),
        schedules=[
            TransportSchedule(
                departure_at=departure,
                arrival_at=departure + timedelta(hours=hours),
                available_weight_kg=schedule_weight,
            )
        ],
        price=TransportPrice(model="fixed", amount=price, currency="KES"),
        reliability=0.95,
        restrictions=restrictions or set(),
    )


def shipment(origin: Location, destination: Location, ready: datetime, deadline: datetime) -> Shipment:
    return Shipment(
        id="S1",
        origin=origin,
        destination=destination,
        packages=[Package(id="P1", weight_kg=10, length_m=0.2, width_m=0.2, height_m=0.2)],
        ready_at=ready,
        deadline=deadline,
    )


def test_discovers_direct_path_and_metrics():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t, 3)])

    paths = engine.discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6)))

    assert len(paths) == 1
    path = paths[0]
    assert path.option_ids == ("BUS",)
    assert path.total_cost == Decimal("100")
    assert path.transit_seconds == 3 * 3600
    assert path.waiting_seconds == 0
    assert path.number_of_transfers == 0
    assert path.reliability == 0.95
    assert path.modes == (TransportMode.BUS,)
    assert path.providers == ("P-BUS",)
    assert path.capacity_utilization == 0.1
    assert path.deadline_feasible


def test_initial_wait_is_explicitly_measured():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t + timedelta(hours=2), 3)])

    path = engine.discover_paths(shipment(nbo, nku, t, t + timedelta(hours=8)))[0]

    assert path.waiting_seconds == 2 * 3600
    assert path.elapsed_seconds == 5 * 3600


def test_discovers_multimodal_path_with_transfer_wait():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku, ksm = loc("nbo", "Nairobi"), loc("nku", "Nakuru"), loc("ksm", "Kisumu")
    services = [
        service("BUS-NKU", nbo, nku, TransportMode.BUS, t, 3, weight=100),
        service("TRUCK-KSM", nku, ksm, TransportMode.TRUCK, t + timedelta(hours=4), 5, weight=20),
    ]
    engine = PathSearchEngine(services)

    paths = engine.discover_paths(shipment(nbo, ksm, t, t + timedelta(hours=12)))

    assert paths
    path = paths[0]
    assert path.option_ids == ("BUS-NKU", "TRUCK-KSM")
    assert path.number_of_transfers == 1
    assert path.waiting_seconds == 4 * 3600
    assert path.transit_seconds == 8 * 3600
    assert path.total_cost == Decimal("200")


def test_minimum_transfer_time_is_respected():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku, ksm = loc("nbo", "Nairobi"), loc("nku", "Nakuru"), loc("ksm", "Kisumu")
    services = [
        service("A", nbo, nku, TransportMode.BUS, t, 3),
        service("B", nku, ksm, TransportMode.TRUCK, t + timedelta(hours=3, minutes=30), 3),
        service("C", nku, ksm, TransportMode.TRUCK, t + timedelta(hours=4), 3),
    ]
    engine = PathSearchEngine(services, PathSearchConfig(min_transfer_seconds=30 * 60))

    paths = engine.discover_paths(shipment(nbo, ksm, t, t + timedelta(hours=10)))

    assert paths
    assert paths[0].option_ids == ("A", "C")


def test_transfer_handling_cost_is_added_per_transfer():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku, ksm = loc("nbo", "Nairobi"), loc("nku", "Nakuru"), loc("ksm", "Kisumu")
    services = [
        service("A", nbo, nku, TransportMode.BUS, t, 3),
        service("B", nku, ksm, TransportMode.TRUCK, t + timedelta(hours=4), 3),
    ]
    engine = PathSearchEngine(services, PathSearchConfig(transfer_handling_cost=Decimal("25")))

    path = engine.discover_paths(shipment(nbo, ksm, t, t + timedelta(hours=10)))[0]

    assert path.total_cost == Decimal("225")


def test_schedule_specific_capacity_is_respected():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    option = service("BUS", nbo, nku, TransportMode.BUS, t, 3, schedule_weight=5)

    assert PathSearchEngine([option]).discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6))) == []


def test_cargo_restrictions_are_respected():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    option = service("BUS", nbo, nku, TransportMode.BUS, t, 3, restrictions={"no_fragile"})
    cargo = Shipment(
        id="S1",
        origin=nbo,
        destination=nku,
        packages=[Package(id="P1", weight_kg=10, length_m=0.2, width_m=0.2, height_m=0.2, fragile=True)],
        ready_at=t,
        deadline=t + timedelta(hours=6),
    )

    assert PathSearchEngine([option]).discover_paths(cargo) == []


def test_provider_and_mode_policies_filter_options():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    bus = service("BUS", nbo, nku, TransportMode.BUS, t, 3, provider_id="BUSCO")
    truck = service("TRUCK", nbo, nku, TransportMode.TRUCK, t, 3, provider_id="TRUCKCO")
    config = PathSearchConfig(
        allowed_modes=frozenset({TransportMode.TRUCK}),
        allowed_provider_ids=frozenset({"TRUCKCO"}),
    )

    paths = PathSearchEngine([bus, truck], config).discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6)))

    assert len(paths) == 1
    assert paths[0].option_ids == ("TRUCK",)


def test_max_transfers_is_enforced():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    a, b, c = loc("a", "A"), loc("b", "B"), loc("c", "C")
    services = [
        service("AB", a, b, TransportMode.BUS, t, 1),
        service("BC", b, c, TransportMode.RAIL, t + timedelta(hours=2), 1),
    ]
    config = PathSearchConfig(max_transfers=0)

    assert PathSearchEngine(services, config).discover_paths(shipment(a, c, t, t + timedelta(hours=6))) == []


def test_unsupported_distance_pricing_is_not_silently_treated_as_total_price():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    option = service("TRUCK", nbo, nku, TransportMode.TRUCK, t, 3)
    option = option.model_copy(update={"price": TransportPrice(model="per_km", amount=Decimal("10"), currency="KES")})

    assert PathSearchEngine([option]).discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6))) == []


def test_dominated_paths_are_removed_but_tradeoffs_remain():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    cheap_fast = service("A", nbo, nku, TransportMode.BUS, t, 2, price=Decimal("100"))
    dominated = service("B", nbo, nku, TransportMode.BUS, t, 3, price=Decimal("150"))
    slow_reliable = service("C", nbo, nku, TransportMode.TRUCK, t, 4, price=Decimal("80"))
    slow_reliable = slow_reliable.model_copy(update={"reliability": 0.99})

    paths = PathSearchEngine([cheap_fast, dominated, slow_reliable]).discover_paths(
        shipment(nbo, nku, t, t + timedelta(hours=6))
    )

    ids = {path.option_ids for path in paths}
    assert ("B",) not in ids
    assert {("A",), ("C",)} <= ids
