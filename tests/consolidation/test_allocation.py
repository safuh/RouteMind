from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.consolidation.allocation import allocate_consolidation
from routemind.domain.models import (
    Location,
    Package,
    PricingModel,
    Shipment,
    TransportCapacity,
    TransportLeg,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.paths.models import CandidatePath


def _locations():
    return {name: Location(id=name, name=name) for name in ("NBO", "KLA", "KGL", "GOM")}


def _shipment(id_: str, destination: str, locations):
    return Shipment(
        id=id_,
        origin=locations["NBO"],
        destination=locations[destination],
        packages=[
            Package(
                id=f"p-{id_}",
                weight_kg=10,
                length_m=0.1,
                width_m=0.1,
                height_m=0.1,
            )
        ],
        ready_at=datetime(2026, 8, 27, 6, tzinfo=UTC),
        deadline=datetime(2026, 8, 28, tzinfo=UTC),
    )


def _option(id_: str, origin, destination, departure, arrival, price):
    return TransportOption(
        id=id_,
        provider_id="carrier",
        provider_name="Carrier",
        mode=TransportMode.TRUCK,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=1000),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=arrival)],
        price=TransportPrice(model=PricingModel.FIXED, amount=Decimal(str(price)), currency="KES"),
        reliability=0.99,
    )


def _path(shipment_id, legs):
    return CandidatePath(
        shipment_id=shipment_id,
        legs=tuple(legs),
        total_cost=Decimal("100"),
        currency="KES",
        transit_seconds=sum(
            (leg.arrival_at - leg.departure_at).total_seconds() for leg in legs
        ),
        waiting_seconds=0,
        number_of_transfers=len(legs) - 1,
        reliability=0.99,
        modes=tuple(TransportMode.TRUCK for _ in legs),
        providers=tuple("carrier" for _ in legs),
        capacity_utilization=0.1,
        deadline_feasible=True,
    )


def test_shared_upstream_leg_and_private_downstream_legs_are_separated():
    loc = _locations()
    t0 = datetime(2026, 8, 27, 8, tzinfo=UTC)
    t1 = t0 + timedelta(hours=2)
    t2 = t1 + timedelta(hours=1)
    shared = _option("NBO-KLA-1", loc["NBO"], loc["KLA"], t0, t1, 100)
    a_down = _option("KLA-KGL-1", loc["KLA"], loc["KGL"], t2, t2 + timedelta(hours=2), 60)
    b_down = _option("KLA-GOM-1", loc["KLA"], loc["GOM"], t2, t2 + timedelta(hours=3), 80)
    legs_a = [
        TransportLeg(
            option_id=shared.id,
            origin=loc["NBO"],
            destination=loc["KLA"],
            departure_at=t0,
            arrival_at=t1,
        ),
        TransportLeg(
            option_id=a_down.id,
            origin=loc["KLA"],
            destination=loc["KGL"],
            departure_at=t2,
            arrival_at=t2 + timedelta(hours=2),
        ),
    ]
    legs_b = [
        TransportLeg(
            option_id=shared.id,
            origin=loc["NBO"],
            destination=loc["KLA"],
            departure_at=t0,
            arrival_at=t1,
        ),
        TransportLeg(
            option_id=b_down.id,
            origin=loc["KLA"],
            destination=loc["GOM"],
            departure_at=t2,
            arrival_at=t2 + timedelta(hours=3),
        ),
    ]
    shipments = {"A": _shipment("A", "KGL", loc), "B": _shipment("B", "GOM", loc)}
    allocation = allocate_consolidation(
        (_path("A", legs_a), _path("B", legs_b)),
        shipments,
        {shared.id: shared, a_down.id: a_down, b_down.id: b_down},
    )
    assert len(allocation.shared) == 1
    assert allocation.shared[0].shipment_ids == ("A", "B")
    assert allocation.shared[0].weight_kg == 20
    assert {x.segment.option_id for x in allocation.private["A"]} == {a_down.id}
    assert {x.segment.option_id for x in allocation.private["B"]} == {b_down.id}
    assert allocation.total_cost == Decimal("240")


def test_same_downstream_schedule_is_shared_too():
    loc = _locations()
    t0 = datetime(2026, 8, 27, 8, tzinfo=UTC)
    t1 = t0 + timedelta(hours=2)
    t2 = t1 + timedelta(hours=1)
    shared1 = _option("NBO-KLA-1", loc["NBO"], loc["KLA"], t0, t1, 100)
    shared2 = _option("KLA-KGL-1", loc["KLA"], loc["KGL"], t2, t2 + timedelta(hours=2), 60)

    def legs():
        return [
            TransportLeg(
                option_id=shared1.id,
                origin=loc["NBO"],
                destination=loc["KLA"],
                departure_at=t0,
                arrival_at=t1,
            ),
            TransportLeg(
                option_id=shared2.id,
                origin=loc["KLA"],
                destination=loc["KGL"],
                departure_at=t2,
                arrival_at=t2 + timedelta(hours=2),
            ),
        ]

    shipments = {"A": _shipment("A", "KGL", loc), "B": _shipment("B", "KGL", loc)}
    allocation = allocate_consolidation(
        (_path("A", legs()), _path("B", legs())),
        shipments,
        {shared1.id: shared1, shared2.id: shared2},
    )
    assert [x.segment.option_id for x in allocation.shared] == [shared1.id, shared2.id]
    assert allocation.private["A"] == ()
    assert allocation.private["B"] == ()
    assert allocation.total_cost == Decimal("160")
