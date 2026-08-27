from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.consolidation import (
    CapacityReservationLedger,
    ConsolidationOpportunity,
    SharedTransportSegment,
    reserve_opportunities,
)
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


def shipment(id_: str, origin: Location, destination: Location, weight: float) -> Shipment:
    return Shipment(
        id=id_, origin=origin, destination=destination,
        packages=[Package(id=f"P-{id_}", weight_kg=weight, length_m=0.2, width_m=0.2, height_m=0.2)],
        ready_at=datetime(2026, 8, 27, 7, tzinfo=UTC), deadline=datetime(2026, 8, 27, 20, tzinfo=UTC),
    )


def service(
    origin: Location,
    destination: Location,
    *,
    option_id: str = "BUS-001",
    available_weight_kg: float = 70,
) -> tuple[TransportOption, SharedTransportSegment]:
    departure = datetime(2026, 8, 27, 8, tzinfo=UTC)
    arrival = departure + timedelta(hours=3)
    option = TransportOption(
        id=option_id,
        provider_id="P1",
        provider_name="Synthetic Bus",
        mode=TransportMode.BUS,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=100, max_volume_m3=10),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=arrival, available_weight_kg=available_weight_kg)],
        price=TransportPrice(model="fixed", amount=Decimal("100"), currency="KES"),
        reliability=0.95,
    )
    segment = SharedTransportSegment(
        option_id=option.id,
        provider_id=option.provider_id,
        provider_name=option.provider_name,
        origin_id=origin.id,
        destination_id=destination.id,
        departure_at=departure,
        arrival_at=arrival,
    )
    return option, segment


def opportunity(*shipment_ids: str, segment: SharedTransportSegment, weight: float) -> ConsolidationOpportunity:
    return ConsolidationOpportunity(
        shipment_ids=shipment_ids,
        shared_segments=(segment,),
        total_weight_kg=weight,
        total_volume_m3=0.01,
        total_package_count=len(shipment_ids),
        weight_capacity_kg=70,
        volume_capacity_m3=10,
        standalone_shared_segment_cost=Decimal("100") * len(shipment_ids),
        consolidated_shared_segment_cost=Decimal("100"),
        savings=Decimal("100") * (len(shipment_ids) - 1),
        currency="KES",
        feasible=True,
    )


def test_competing_opportunities_cannot_double_reserve_shared_capacity():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    option, segment = service(nbo, nku)
    shipments = {
        "A": shipment("A", nbo, nku, 40),
        "B": shipment("B", nbo, nku, 20),
        "C": shipment("C", nbo, nku, 30),
    }
    first = opportunity("A", "B", segment=segment, weight=60)
    second = opportunity("B", "C", segment=segment, weight=50)

    ledger, results = reserve_opportunities((first, second), shipments, {option.id: option})

    assert results[0].accepted
    assert not results[1].accepted
    assert results[1].rejections[0].reason == "shipment_already_reserved"
    assert ledger.reserved_weight_kg(segment) == 60
    assert ledger.reserved_volume_m3(segment) == 0.016


def test_distinct_opportunities_share_capacity_until_remaining_capacity_is_exhausted():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    option, segment = service(nbo, nku)
    shipments = {
        "A": shipment("A", nbo, nku, 40),
        "B": shipment("B", nbo, nku, 30),
        "C": shipment("C", nbo, nku, 40),
    }
    first = opportunity("A", segment=segment, weight=40)
    second = opportunity("B", segment=segment, weight=30)
    third = opportunity("C", segment=segment, weight=40)

    ledger, results = reserve_opportunities((first, second, third), shipments, {option.id: option})

    assert results[0].accepted
    assert results[1].accepted
    assert not results[2].accepted
    assert results[2].rejections[0].reason == "capacity_weight"
    assert ledger.reserved_weight_kg(segment) == 70


def test_failed_reservation_is_atomic_across_multiple_shared_segments():
    nbo = Location(id="nbo", name="Nairobi")
    nku = Location(id="nku", name="Nakuru")
    ksm = Location(id="ksm", name="Kisumu")
    first_option, first_segment = service(nbo, nku, available_weight_kg=70)
    second_option, second_segment = service(nku, ksm, option_id="BUS-002", available_weight_kg=70)
    shipments = {"A": shipment("A", nbo, ksm, 80)}
    opportunity_with_two_segments = ConsolidationOpportunity(
        shipment_ids=("A",),
        shared_segments=(first_segment, second_segment),
        total_weight_kg=80,
        total_volume_m3=0.01,
        total_package_count=1,
        weight_capacity_kg=70,
        volume_capacity_m3=10,
        standalone_shared_segment_cost=Decimal("200"),
        consolidated_shared_segment_cost=Decimal("200"),
        savings=Decimal("0"),
        currency="KES",
        feasible=True,
    )

    ledger = CapacityReservationLedger()
    result = ledger.reserve(
        opportunity_with_two_segments,
        shipments,
        {first_option.id: first_option, second_option.id: second_option},
    )

    assert not result.accepted
    assert not ledger.reservations
    assert ledger.reserved_weight_kg(first_segment) == 0
    assert ledger.reserved_weight_kg(second_segment) == 0
