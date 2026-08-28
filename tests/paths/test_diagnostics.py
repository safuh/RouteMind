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
from routemind.paths import PathSearchEngine, RejectionReason


def shipment():
    now = datetime(2026, 8, 27, 8, tzinfo=UTC)
    a, b = Location(id="a", name="A"), Location(id="b", name="B")
    return Shipment(
        id="S1",
        origin=a,
        destination=b,
        packages=[Package(id="p", weight_kg=2, length_m=1, width_m=1, height_m=1)],
        ready_at=now,
        deadline=now + timedelta(hours=2),
    )


def option(shipment, *, available=True, schedule_volume=None):
    return TransportOption(
        id="O1",
        provider_id="P1",
        provider_name="Provider",
        mode=TransportMode.BUS,
        origin=shipment.origin,
        destination=shipment.destination,
        capacity=TransportCapacity(max_weight_kg=100),
        schedules=[
            TransportSchedule(
                departure_at=shipment.ready_at,
                arrival_at=shipment.ready_at + timedelta(hours=1),
                available_volume_m3=schedule_volume,
            )
        ],
        price=TransportPrice(model="fixed", amount=Decimal("100"), currency="KES"),
        reliability=0.95,
        available=available,
    )


def test_diagnostics_capture_unavailable_option():
    s = shipment()
    engine = PathSearchEngine([option(s, available=False)])
    assert engine.discover_paths(s) == []
    assert engine.last_diagnostics.by_reason() == {RejectionReason.UNAVAILABLE.value: 1}
    assert engine.last_diagnostics.rejection_count == 1


def test_diagnostics_capture_capacity_rejection():
    s = shipment()
    engine = PathSearchEngine([option(s, schedule_volume=0.5)])
    assert engine.discover_paths(s) == []
    assert engine.last_diagnostics.rejection_count == 1
    assert engine.last_diagnostics.rejected[0].reason is RejectionReason.VOLUME_CAPACITY
