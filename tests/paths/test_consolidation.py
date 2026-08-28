from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import Location, Package, Shipment, TransportCapacity, TransportLeg, TransportMode, TransportOption, TransportPrice, TransportSchedule
from routemind.paths import CandidatePath
from routemind.paths.consolidation import ConsolidationEngine, ConsolidationRejectionReason, SharedSegment


def _fixtures(weight_capacity=100.0, restrictions=None):
    t = datetime(2026, 8, 28, 8, tzinfo=UTC)
    n, k, e = (Location(id=i, name=i) for i in ("NBO", "NKR", "ELD"))
    option = TransportOption(id="bus-1", provider_id="p1", provider_name="P1", mode=TransportMode.BUS, origin=n, destination=k, capacity=TransportCapacity(max_weight_kg=weight_capacity, max_volume_m3=10), schedules=[TransportSchedule(departure_at=t, arrival_at=t + timedelta(hours=3), available_weight_kg=weight_capacity)], price=TransportPrice(model="fixed", amount=Decimal("1000"), currency="KES"), reliability=.95, restrictions=restrictions or set())
    return t, n, k, e, option


def shipment(sid, origin, destination, t, weight, *, deadline=None, fragile=False):
    return Shipment(id=sid, origin=origin, destination=destination, packages=[Package(id=f"{sid}-pkg", weight_kg=weight, length_m=1, width_m=1, height_m=.1, fragile=fragile)], ready_at=t, deadline=deadline)


def path(sid, origin, destination, option, t, weight):
    return CandidatePath(shipment_id=sid, legs=(TransportLeg(option_id=option.id, origin=origin, destination=destination, departure_at=t, arrival_at=t + timedelta(hours=3), allocated_weight_kg=weight, allocated_volume_m3=.1),), total_cost=option.price.amount, currency="KES", transit_seconds=10800, waiting_seconds=0, number_of_transfers=0, reliability=.95, modes=(TransportMode.BUS,), providers=(option.provider_id,), capacity_utilization=weight / option.capacity.max_weight_kg, deadline_feasible=True)


def test_detects_same_scheduled_segment_across_different_destinations():
    t, n, k, e, option = _fixtures()
    p1 = path("S1", n, k, option, t, 10)
    p2 = path("S2", n, k, option, t, 20)
    engine = ConsolidationEngine([option])
    found = engine.detect_shared_segments({"S1": [p1], "S2": [p2]})
    segment = SharedSegment.from_leg(p1.legs[0])
    assert segment in found
    assert tuple(item[0] for item in found[segment]) == ("S1", "S2")


def test_consolidation_aggregates_capacity_and_fixed_cost_savings():
    t, n, k, _, option = _fixtures()
    engine = ConsolidationEngine([option])
    result = engine.evaluate(SharedSegment.from_leg(path("S1", n, k, option, t, 10).legs[0]), ("S1", "S2"), {"S1": shipment("S1", n, k, t, 10), "S2": shipment("S2", n, k, t, 20)})
    assert result.feasible
    assert result.total_weight_kg == 30
    assert result.baseline_segment_cost == Decimal("2000")
    assert result.consolidated_segment_cost == Decimal("1000")
    assert result.savings == Decimal("1000")


def test_capacity_rejects_aggregate_weight():
    t, n, k, _, option = _fixtures(weight_capacity=25)
    engine = ConsolidationEngine([option])
    segment = SharedSegment.from_leg(path("S1", n, k, option, t, 10).legs[0])
    result = engine.evaluate(segment, ("S1", "S2"), {"S1": shipment("S1", n, k, t, 10), "S2": shipment("S2", n, k, t, 20)})
    assert not result.feasible
    assert result.rejection.reason == ConsolidationRejectionReason.CAPACITY


def test_deadline_rejects_shared_service():
    t, n, k, _, option = _fixtures()
    engine = ConsolidationEngine([option])
    segment = SharedSegment.from_leg(path("S1", n, k, option, t, 10).legs[0])
    deadline = t + timedelta(hours=2)
    result = engine.evaluate(segment, ("S1", "S2"), {"S1": shipment("S1", n, k, t, 10, deadline=deadline), "S2": shipment("S2", n, k, t, 10)})
    assert not result.feasible
    assert result.rejection.reason == ConsolidationRejectionReason.DEADLINE


def test_cargo_restriction_rejects_incompatible_shipment():
    t, n, k, _, option = _fixtures(restrictions={"no_fragile"})
    engine = ConsolidationEngine([option])
    segment = SharedSegment.from_leg(path("S1", n, k, option, t, 10).legs[0])
    result = engine.evaluate(segment, ("S1", "S2"), {"S1": shipment("S1", n, k, t, 10, fragile=True), "S2": shipment("S2", n, k, t, 10)})
    assert not result.feasible
    assert result.rejection.reason == ConsolidationRejectionReason.CARGO_RESTRICTION


def test_detects_only_actual_scheduled_service_identity():
    t, n, k, _, option = _fixtures()
    other = option.model_copy(update={"id": "bus-2"})
    p1 = path("S1", n, k, option, t, 10)
    p2 = path("S2", n, k, other, t, 10)
    assert ConsolidationEngine([option, other]).detect_shared_segments({"S1": [p1], "S2": [p2]}) == {}
