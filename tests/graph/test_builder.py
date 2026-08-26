from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from routemind.domain.models import (
    Location,
    PricingModel,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)
from routemind.graph import build_transport_graph
from routemind.scenarios.generator import generate_scenario


def test_synthetic_scenario_builds_into_graph():
    scenario = generate_scenario(seed=42, shipment_count=20)
    graph = build_transport_graph(scenario.locations, scenario.transport_options)

    assert len(graph.nodes) == len(scenario.locations)
    assert len(graph.edges) == sum(len(option.schedules) for option in scenario.transport_options)
    assert graph.outgoing("nbo")


def test_graph_preserves_multimodal_edges():
    scenario = generate_scenario(seed=42, shipment_count=5)
    graph = build_transport_graph(scenario.locations, scenario.transport_options)
    modes = {edge.mode for edge in graph.edges}

    assert TransportMode.BUS in modes
    assert TransportMode.TRUCK in modes
    assert TransportMode.RAIL in modes
    assert TransportMode.MOTORCYCLE in modes


def test_graph_preserves_time_capacity_and_price():
    origin = Location(id="a", name="A")
    destination = Location(id="b", name="B")
    departure = datetime(2026, 8, 26, 8, tzinfo=UTC)
    option = TransportOption(
        id="svc",
        provider_id="p",
        provider_name="Provider",
        mode=TransportMode.BUS,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=100, max_volume_m3=2),
        schedules=[
            TransportSchedule(
                departure_at=departure,
                arrival_at=departure + timedelta(hours=2),
                available_weight_kg=40,
                available_volume_m3=1,
            )
        ],
        price=TransportPrice(
            model=PricingModel.FIXED,
            amount=Decimal("500"),
            currency="KES",
        ),
        reliability=0.9,
    )

    edge = build_transport_graph([origin, destination], [option]).edges[0]
    assert edge.max_weight_kg == 40
    assert edge.max_volume_m3 == 1
    assert edge.price_amount == Decimal("500")
    assert edge.transit_seconds == 7200


def test_graph_rejects_invalid_schedule():
    origin = Location(id="a", name="A")
    destination = Location(id="b", name="B")
    moment = datetime(2026, 8, 26, 8, tzinfo=UTC)
    option = TransportOption(
        id="bad",
        provider_id="p",
        provider_name="Provider",
        mode=TransportMode.VAN,
        origin=origin,
        destination=destination,
        capacity=TransportCapacity(max_weight_kg=10),
        schedules=[TransportSchedule(departure_at=moment, arrival_at=moment)],
        price=TransportPrice(
            model=PricingModel.FIXED,
            amount=Decimal("10"),
            currency="KES",
        ),
        reliability=0.9,
    )

    with pytest.raises(ValueError, match="Invalid schedule"):
        build_transport_graph([origin, destination], [option])
