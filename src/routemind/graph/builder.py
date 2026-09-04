"""Convert domain transport services into graph edges."""

from __future__ import annotations

from routemind.domain.models import Location, TransportOption, TransportSchedule

from .models import GraphEdge, GraphNode, TransportGraph


def build_transport_graph(
    locations: list[Location],
    transport_options: list[TransportOption],
) -> TransportGraph:
    """Build a graph while preserving every scheduled transport service."""
    graph = TransportGraph()

    for location in locations:
        graph.add_node(GraphNode(id=location.id, location=location))

    for option in transport_options:
        if option.origin.id not in {node.id for node in graph.nodes}:
            raise ValueError(f"Transport origin is missing from graph: {option.origin.id}")
        if option.destination.id not in {node.id for node in graph.nodes}:
            raise ValueError(
                f"Transport destination is missing from graph: {option.destination.id}"
            )

        for schedule_index, schedule in enumerate(option.schedules):
            if not schedule_is_valid(schedule):
                raise ValueError(f"Invalid schedule for transport option {option.id}")
            graph.add_edge(
                GraphEdge(
                    id=f"{option.id}@{schedule_index}",
                    origin_id=option.origin.id,
                    destination_id=option.destination.id,
                    provider_id=option.provider_id,
                    provider_name=option.provider_name,
                    mode=option.mode,
                    departure_at=schedule.departure_at,
                    arrival_at=schedule.arrival_at,
                    max_weight_kg=min(
                        option.capacity.max_weight_kg,
                        schedule.available_weight_kg
                        if schedule.available_weight_kg is not None
                        else option.capacity.max_weight_kg,
                    ),
                    max_volume_m3=(
                        min(option.capacity.max_volume_m3, schedule.available_volume_m3)
                        if option.capacity.max_volume_m3 is not None
                        and schedule.available_volume_m3 is not None
                        else schedule.available_volume_m3
                        or option.capacity.max_volume_m3
                    ),
                    price_amount=option.price.amount,
                    currency=option.price.currency,
                    reliability=option.reliability,
                    restrictions=frozenset(option.restrictions),
                )
            )
    return graph


def schedule_is_valid(schedule: TransportSchedule) -> bool:
    return schedule.arrival_at > schedule.departure_at
