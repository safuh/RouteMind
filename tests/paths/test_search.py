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
) -> TransportOption:
    return TransportOption(
        id=id_,
        provider_id=f"P-{id_}",
        provider_name=f"Provider {id_}",
        mode=mode,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=weight, max_volume_m3=2),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=departure + timedelta(hours=hours))],
        price=TransportPrice(model="fixed", amount=Decimal("100"), currency="KES"),
        reliability=0.95,
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


def test_discovers_direct_path():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t, 3)])

    paths = engine.discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6)))

    assert len(paths) == 1
    assert [leg.option_id for leg in paths[0]] == ["BUS"]


def test_discovers_multimodal_path_when_direct_service_is_absent():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku, ksm = loc("nbo", "Nairobi"), loc("nku", "Nakuru"), loc("ksm", "Kisumu")
    services = [
        service("BUS-NKU", nbo, nku, TransportMode.BUS, t, 3),
        service("TRUCK-KSM", nku, ksm, TransportMode.TRUCK, t + timedelta(hours=4), 5),
    ]
    engine = PathSearchEngine(services)

    paths = engine.discover_paths(shipment(nbo, ksm, t, t + timedelta(hours=12)))

    assert paths
    assert [leg.option_id for leg in paths[0]] == ["BUS-NKU", "TRUCK-KSM"]


def test_missed_departure_is_not_feasible():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t, 3)])

    ready = t + timedelta(minutes=1)
    assert engine.discover_paths(shipment(nbo, nku, ready, t + timedelta(hours=6))) == []


def test_capacity_is_respected():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t, 3, weight=5)])

    assert engine.discover_paths(shipment(nbo, nku, t, t + timedelta(hours=6))) == []


def test_deadline_is_respected():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    nbo, nku = loc("nbo", "Nairobi"), loc("nku", "Nakuru")
    engine = PathSearchEngine([service("BUS", nbo, nku, TransportMode.BUS, t, 3)])

    assert engine.discover_paths(shipment(nbo, nku, t, t + timedelta(hours=2))) == []
