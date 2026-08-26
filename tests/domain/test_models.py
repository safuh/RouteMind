from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from routemind.domain.models import (
    Location,
    Package,
    PricingModel,
    Shipment,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.domain.validation import (
    schedule_is_available_after,
    schedule_is_valid,
    shipment_timing_is_valid,
    transport_can_carry_shipment,
)


def locations() -> tuple[Location, Location]:
    return (
        Location(id="nbo", name="Nairobi", latitude=-1.2864, longitude=36.8172),
        Location(id="ksm", name="Kisumu", latitude=-0.0917, longitude=34.7680),
    )


def shipment(weight: float = 10, volume: float = 0.1) -> Shipment:
    origin, destination = locations()
    return Shipment(
        id="S1",
        origin=origin,
        destination=destination,
        packages=[
            Package(
                id="P1",
                weight_kg=weight,
                length_m=volume ** (1 / 3),
                width_m=volume ** (1 / 3),
                height_m=volume ** (1 / 3),
            )
        ],
        ready_at=datetime(2026, 8, 26, 8, tzinfo=UTC),
    )


def option(weight: float = 50, volume: float = 1) -> TransportOption:
    origin, destination = locations()
    departure = datetime(2026, 8, 26, 9, tzinfo=UTC)
    return TransportOption(
        id="BUS-1",
        provider_id="BUS-X",
        provider_name="Provider X",
        mode=TransportMode.BUS,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=weight, max_volume_m3=volume),
        schedules=[
            TransportSchedule(
                departure_at=departure,
                arrival_at=departure + timedelta(hours=6),
            )
        ],
        price=TransportPrice(
            model=PricingModel.PER_KG,
            amount=Decimal("20"),
            currency="KES",
        ),
        reliability=0.95,
    )


def test_package_volume_is_calculated():
    package = Package(id="P", weight_kg=5, length_m=2, width_m=1, height_m=0.5)
    assert package.volume_m3 == pytest.approx(1.0)


def test_shipment_aggregates_weight_and_volume():
    shipment_value = shipment(weight=10, volume=0.1)
    assert shipment_value.weight_kg == pytest.approx(10)
    assert shipment_value.volume_m3 == pytest.approx(0.1)


def test_invalid_weight_is_rejected():
    with pytest.raises(ValidationError):
        Package(id="P", weight_kg=0, length_m=1, width_m=1, height_m=1)


def test_schedule_must_have_positive_duration():
    start = datetime(2026, 8, 26, 8, tzinfo=UTC)
    invalid = TransportSchedule(departure_at=start, arrival_at=start)
    assert not schedule_is_valid(invalid)


def test_shipment_deadline_must_follow_readiness():
    shipment_value = shipment()
    shipment_value.deadline = shipment_value.ready_at - timedelta(minutes=1)
    assert not shipment_timing_is_valid(shipment_value)


def test_transport_capacity_accepts_feasible_shipment():
    assert transport_can_carry_shipment(shipment(), option())


def test_transport_capacity_rejects_overweight_shipment():
    assert not transport_can_carry_shipment(shipment(weight=60), option())


def test_transport_capacity_rejects_overvolume_shipment():
    assert not transport_can_carry_shipment(shipment(volume=2), option())


def test_schedule_can_be_used_after_shipment_is_ready():
    transport = option()
    assert schedule_is_available_after(transport.schedules[0], shipment().ready_at)
