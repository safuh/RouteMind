from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.consolidation.grouping import (
    generate_coexisting_opportunity_combinations,
    generate_consolidation_opportunities,
)
from routemind.consolidation.models import ConsolidationOpportunity, SharedTransportSegment
from routemind.domain.models import (
    Location,
    Package,
    Shipment,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
    PricingModel,
)
from routemind.paths.models import CandidatePath


NOW = datetime(2026, 8, 28, 8, tzinfo=UTC)
NBO = Location(id="NBO", name="Nairobi")
KIS = Location(id="KIS", name="Kisumu")
ELD = Location(id="ELD", name="Eldoret")


def shipment(id_: str, destination: Location = KIS, weight: float = 2) -> Shipment:
    return Shipment(
        id=id_,
        origin=NBO,
        destination=destination,
        packages=[
            Package(
                id=f"P-{id_}",
                weight_kg=weight,
                length_m=0.2,
                width_m=0.2,
                height_m=0.2,
            )
        ],
        ready_at=NOW,
        deadline=NOW + timedelta(hours=12),
    )


def option(id_: str, destination: Location, capacity: float = 20) -> TransportOption:
    departure = NOW + timedelta(hours=1)
    return TransportOption(
        id=id_,
        provider_id="PROVIDER",
        provider_name="Synthetic Carrier",
        mode=TransportMode.TRUCK,
        origin=NBO,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=capacity),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=departure + timedelta(hours=3))],
        price=TransportPrice(model=PricingModel.FIXED, amount=Decimal("100"), currency="KES"),
        reliability=0.95,
    )


def candidate(shipment_id: str, option_id: str, destination: Location) -> CandidatePath:
    departure = NOW + timedelta(hours=1)
    return CandidatePath(
        shipment_id=shipment_id,
        legs=(),
        total_cost=Decimal("100"),
        currency="KES",
        transit_seconds=10800,
        waiting_seconds=3600,
        number_of_transfers=0,
        reliability=0.95,
        modes=(TransportMode.TRUCK,),
        providers=("Synthetic Carrier",),
        capacity_utilization=0.1,
        deadline_feasible=True,
    ).model_copy(
        update={
            "legs": (
                {
                    "option_id": option_id,
                    "origin": NBO,
                    "destination": destination,
                    "departure_at": departure,
                    "arrival_at": departure + timedelta(hours=3),
                    "allocated_weight_kg": 2,
                    "allocated_volume_m3": 0.008,
                },
            )
        }
    )


def opportunity(*shipment_ids: str, option_id: str = "SHARED", capacity: float = 20) -> ConsolidationOpportunity:
    departure = NOW + timedelta(hours=1)
    segment = SharedTransportSegment(
        option_id=option_id,
        provider_id="PROVIDER",
        provider_name="Synthetic Carrier",
        origin_id="NBO",
        destination_id="KIS",
        departure_at=departure,
        arrival_at=departure + timedelta(hours=3),
    )
    weight = 2 * len(shipment_ids)
    return ConsolidationOpportunity(
        shipment_ids=shipment_ids,
        shared_segments=(segment,),
        total_weight_kg=weight,
        total_volume_m3=0.008 * len(shipment_ids),
        total_package_count=len(shipment_ids),
        weight_capacity_kg=capacity,
        volume_capacity_m3=None,
        standalone_shared_segment_cost=Decimal("200") * len(shipment_ids),
        consolidated_shared_segment_cost=Decimal("100"),
        savings=Decimal("100") * (len(shipment_ids) - 1),
        currency="KES",
        feasible=True,
    )


def test_generate_consolidation_opportunities_expands_paths_and_filters_non_shared_groups():
    shipments = {"A": shipment("A"), "B": shipment("B")}
    options = {"SHARED": option("SHARED", KIS)}
    paths = (candidate("A", "SHARED", KIS), candidate("B", "SHARED", KIS))

    opportunities = generate_consolidation_opportunities(paths, shipments, options)

    assert len(opportunities) == 1
    assert opportunities[0].shipment_ids == ("A", "B")
    assert opportunities[0].feasible


def test_coexisting_combinations_include_empty_and_disjoint_groups():
    shipments = {key: shipment(key) for key in ("A", "B", "C", "D")}
    options = {"SHARED": option("SHARED", KIS)}
    opportunities = (
        opportunity("A", "B"),
        opportunity("C", "D"),
        opportunity("A", "C"),
    )

    combinations = generate_coexisting_opportunity_combinations(opportunities, shipments, options)
    groups = [tuple(item.shipment_ids for item in combination) for combination in combinations]

    assert groups[0] == ()
    assert (("A", "B"), ("C", "D")) in groups
    assert (("A", "B"), ("A", "C")) not in groups


def test_coexisting_combinations_enforce_shared_capacity():
    shipments = {key: shipment(key) for key in ("A", "B", "C", "D")}
    options = {"SHARED": option("SHARED", KIS, capacity=6)}
    opportunities = (opportunity("A", "B", capacity=6), opportunity("C", "D", capacity=6))

    combinations = generate_coexisting_opportunity_combinations(opportunities, shipments, options)
    groups = [tuple(item.shipment_ids for item in combination) for combination in combinations]

    assert (("A", "B"), ("C", "D")) not in groups
    assert (("A", "B"),) in groups
    assert (("C", "D"),) in groups
