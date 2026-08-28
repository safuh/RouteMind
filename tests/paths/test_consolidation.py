from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location, Package, PricingModel, Shipment, TransportCapacity, TransportLeg,
    TransportMode, TransportOption, TransportPrice, TransportSchedule,
)
from routemind.paths import CandidatePath, ConsolidationEngine, ConsolidationRejectionReason


def _fixture():
    t = datetime(2026, 8, 28, 8, tzinfo=UTC)
    nairobi = Location(id="nbo", name="Nairobi")
    nakuru = Location(id="nkr", name="Nakuru")
    option = TransportOption(
        id="bus-1", provider_id="busco", provider_name="BusCo", mode=TransportMode.BUS,
        origin=nairobi, destination=nakuru,
        capacity=TransportCapacity(max_weight_kg=100, max_volume_m3=2),
        schedules=[TransportSchedule(departure_at=t, arrival_at=t + timedelta(hours=3), available_weight_kg=100, available_volume_m3=2)],
        price=TransportPrice(model=PricingModel.FIXED, amount=Decimal("1000"), currency="KES"),
        reliability=.95,
    )
    def shipment(sid, kg, deadline=None):
        return Shipment(id=sid, origin=nairobi, destination=nakuru,
                        packages=[Package(id=f"p-{sid}", weight_kg=kg, length_m=.5, width_m=.5, height_m=.5)],
                        ready_at=t - timedelta(hours=1), deadline=deadline or t + timedelta(hours=6))
    def path(sh):
        return CandidatePath(shipment_id=sh.id, legs=(TransportLeg(option_id="bus-1", origin=nairobi, destination=nakuru, departure_at=t, arrival_at=t + timedelta(hours=3), allocated_weight_kg=sh.weight_kg, allocated_volume_m3=sh.volume_m3),), total_cost=Decimal("1000"), currency="KES", transit_seconds=10800, waiting_seconds=0, number_of_transfers=0, reliability=.95, modes=(TransportMode.BUS,), providers=("busco",), capacity_utilization=sh.weight_kg/100, deadline_feasible=True)
    a, b = shipment("a", 20), shipment("b", 30)
    return t, option, a, b, path(a), path(b)


def test_shared_scheduled_service_is_feasible_and_aggregates_capacity():
    _, option, a, b, pa, pb = _fixture()
    result = ConsolidationEngine().evaluate([a, b], [pa, pb], [option])[0]
    assert result.rejection is None
    assert result.opportunity is not None
    assert result.opportunity.total_weight_kg == 50
    assert result.opportunity.weight_utilization == .5
    assert result.opportunity.savings == Decimal("1000")


def test_capacity_rejects_overloaded_consolidation():
    _, option, a, b, pa, pb = _fixture()
    b = b.model_copy(update={"packages": [Package(id="p-b", weight_kg=90, length_m=.5, width_m=.5, height_m=.5)]})
    pb = pb.model_copy(update={"shipment_id": "b"})
    result = ConsolidationEngine().evaluate([a, b], [pa, pb], [option])[0]
    assert result.rejection is not None
    assert result.rejection.reason == ConsolidationRejectionReason.CAPACITY_WEIGHT


def test_deadline_rejects_shared_segment():
    _, option, a, b, pa, pb = _fixture()
    b = b.model_copy(update={"deadline": datetime(2026, 8, 28, 10, tzinfo=UTC)})
    result = ConsolidationEngine().evaluate([a, b], [pa, pb], [option])[0]
    assert result.rejection is not None
    assert result.rejection.reason == ConsolidationRejectionReason.DEADLINE
