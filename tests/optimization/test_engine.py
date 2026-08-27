from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location,
    OptimizationPolicy,
    Package,
    Shipment,
    TransportCapacity,
    TransportLeg,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.optimization import optimize_portfolio
from routemind.paths.models import CandidatePath


def shipment(id_: str, origin: Location, destination: Location, weight: float) -> Shipment:
    return Shipment(
        id=id_,
        origin=origin,
        destination=destination,
        packages=[
            Package(id=f"P-{id_}", weight_kg=weight, length_m=.2, width_m=.2, height_m=.2)
        ],
        ready_at=datetime(2026, 8, 27, 7, tzinfo=UTC),
        deadline=datetime(2026, 8, 27, 20, tzinfo=UTC),
    )


def option(
    id_: str,
    origin: Location,
    destination: Location,
    departure: datetime,
    cost: str,
    capacity: float,
) -> TransportOption:
    return TransportOption(
        id=id_,
        provider_id="P",
        provider_name="Synthetic",
        mode=TransportMode.BUS,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=capacity, max_volume_m3=10),
        schedules=[
            TransportSchedule(
                departure_at=departure,
                arrival_at=departure + timedelta(hours=3),
                available_weight_kg=capacity,
            )
        ],
        price=TransportPrice(model="fixed", amount=Decimal(cost), currency="KES"),
        reliability=.95,
    )


def path(
    shipment_id: str,
    option_id: str,
    origin: Location,
    destination: Location,
    departure: datetime,
    weight: float,
    cost: str,
) -> CandidatePath:
    arrival = departure + timedelta(hours=3)
    leg = TransportLeg(
        option_id=option_id,
        origin=origin,
        destination=destination,
        departure_at=departure,
        arrival_at=arrival,
        allocated_weight_kg=weight,
        allocated_volume_m3=.008,
    )
    return CandidatePath(
        shipment_id=shipment_id,
        legs=(leg,),
        total_cost=Decimal(cost),
        currency="KES",
        transit_seconds=10800,
        waiting_seconds=0,
        number_of_transfers=0,
        reliability=.95,
        modes=(TransportMode.BUS,),
        providers=("P",),
        capacity_utilization=weight / 100,
        deadline_feasible=True,
    )


def test_optimizer_assigns_one_path_per_shipment_and_minimizes_cost():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    bus1 = option("BUS-1", nbo, nku, t, "100", 100)
    bus2 = option("BUS-2", nbo, nku, t, "40", 100)
    shipments = {"A": shipment("A", nbo, nku, 10), "B": shipment("B", nbo, nku, 10)}
    paths = [
        path("A", "BUS-1", nbo, nku, t, 10, "100"),
        path("A", "BUS-2", nbo, nku, t, 10, "40"),
        path("B", "BUS-1", nbo, nku, t, 10, "100"),
        path("B", "BUS-2", nbo, nku, t, 10, "40"),
    ]

    result = optimize_portfolio(paths, {"BUS-1": bus1, "BUS-2": bus2})

    assert result.feasible
    assert {plan.shipment_id for plan in result.plans} == {"A", "B"}
    assert all(plan.legs[0].option_id == "BUS-2" for plan in result.plans)
    assert result.metrics["total_cost"] == 80


def test_optimizer_enforces_shared_scheduled_capacity():
    nbo, nku = Location(id="nbo", name="Nairobi"), Location(id="nku", name="Nakuru")
    t = datetime(2026, 8, 27, 8, tzinfo=UTC)
    shared = option("BUS-1", nbo, nku, t, "50", 15)
    fallback = option("BUS-2", nbo, nku, t, "100", 100)
    paths = [
        path("A", "BUS-1", nbo, nku, t, 10, "50"),
        path("A", "BUS-2", nbo, nku, t, 10, "100"),
        path("B", "BUS-1", nbo, nku, t, 10, "50"),
        path("B", "BUS-2", nbo, nku, t, 10, "100"),
    ]

    result = optimize_portfolio(paths, {"BUS-1": shared, "BUS-2": fallback})

    assert result.feasible
    assert sum(plan.legs[0].option_id == "BUS-1" for plan in result.plans) == 1
    assert result.metrics["total_cost"] == 150
