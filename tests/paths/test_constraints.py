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


def make_shipment(origin: Location, destination: Location, ready: datetime) -> Shipment:
    return Shipment(
        id="S1",
        origin=origin,
        destination=destination,
        packages=[Package(id="P1", weight_kg=1, length_m=1, width_m=1, height_m=1)],
        ready_at=ready,
        deadline=ready + timedelta(hours=12),
    )


def service(
    service_id: str,
    origin: Location,
    destination: Location,
    departure: datetime,
    *,
    schedule_volume: float | None = None,
    duration_hours: int = 1,
    price: str = "100",
) -> TransportOption:
    return TransportOption(
        id=service_id,
        provider_id=f"P-{service_id}",
        provider_name=service_id,
        mode=TransportMode.BUS,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=100, max_volume_m3=None),
        schedules=[
            TransportSchedule(
                departure_at=departure,
                arrival_at=departure + timedelta(hours=duration_hours),
                available_volume_m3=schedule_volume,
            )
        ],
        price=TransportPrice(model="fixed", amount=Decimal(price), currency="KES"),
        reliability=0.95,
    )


def test_schedule_volume_is_respected_even_without_static_volume_capacity():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    origin, destination = Location(id="a", name="A"), Location(id="b", name="B")
    option = service("BUS", origin, destination, t, schedule_volume=0.5)

    assert PathSearchEngine([option]).discover_paths(make_shipment(origin, destination, t)) == []


def test_candidate_limit_applies_after_dominance_filtering():
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    origin, destination = Location(id="a", name="A"), Location(id="b", name="B")
    options = [
        service("CHEAP", origin, destination, t, duration_hours=2, price="50"),
        service("DOMINATED", origin, destination, t, duration_hours=3, price="100"),
        service("FAST", origin, destination, t, duration_hours=1, price="150"),
    ]

    paths = PathSearchEngine(options, PathSearchConfig(max_candidates=2)).discover_paths(
        make_shipment(origin, destination, t)
    )

    assert len(paths) == 2
    assert {path.option_ids for path in paths} == {("CHEAP",), ("FAST",)}
