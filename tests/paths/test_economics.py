from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location, Package, Shipment, TransportCapacity, TransportMode,
    TransportOption, TransportPrice, TransportSchedule,
)
from routemind.paths import PathSearchEngine


def make_option(model: str, amount: str, distance_km: float | None, carbon: float | None = None) -> TransportOption:
    origin = Location(id="a", name="A")
    destination = Location(id="b", name="B")
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    return TransportOption(
        id="service", provider_id="provider", provider_name="Provider", mode=TransportMode.TRUCK,
        origin=origin, destination=destination,
        capacity=TransportCapacity(max_weight_kg=100),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=departure + timedelta(hours=2))],
        price=TransportPrice(model=model, amount=Decimal(amount), currency="KES"),
        reliability=.95, distance_km=distance_km, carbon_kg_co2e_per_km=carbon,
    )


def shipment() -> Shipment:
    origin = Location(id="a", name="A")
    destination = Location(id="b", name="B")
    return Shipment(
        id="S", origin=origin, destination=destination,
        packages=[Package(id="P", weight_kg=10, length_m=1, width_m=1, height_m=.1)],
        ready_at=datetime(2026, 8, 27, 7, tzinfo=UTC),
    )


def test_per_km_price_uses_service_distance():
    path = PathSearchEngine([make_option("per_km", "5", 100)]).discover(shipment())
    assert path is not None
    assert path.total_cost == Decimal("500")


def test_per_kg_km_price_uses_weight_and_distance():
    path = PathSearchEngine([make_option("per_kg_km", "2", 100)]).discover(shipment())
    assert path is not None
    assert path.total_cost == Decimal("2000")


def test_distance_based_pricing_without_distance_is_rejected():
    engine = PathSearchEngine([make_option("per_km", "5", None)])
    assert engine.discover_paths(shipment()) == []
    assert engine.last_diagnostics.by_reason() == {"unsupported_pricing": 1}


def test_emissions_are_propagated_to_candidate_path():
    path = PathSearchEngine([make_option("fixed", "500", 100, carbon=0.8)]).discover(shipment())
    assert path is not None
    assert path.emissions_kg_co2e == 80
