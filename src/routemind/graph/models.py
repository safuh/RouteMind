"""Graph primitives for multimodal logistics planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from routemind.domain.models import Location, TransportMode


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A physical location at which cargo can enter, leave, or transfer."""

    id: str
    location: Location


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A scheduled transportation service between two graph nodes.

    Edges retain operational facts needed later by time-dependent path search
    and optimization. The graph therefore does not reduce a service to a
    single distance or scalar weight.
    """

    id: str
    origin_id: str
    destination_id: str
    provider_id: str
    provider_name: str
    mode: TransportMode
    departure_at: datetime
    arrival_at: datetime
    max_weight_kg: float
    max_volume_m3: float | None
    price_amount: Decimal
    currency: str
    reliability: float
    restrictions: frozenset[str] = field(default_factory=frozenset)

    @property
    def transit_seconds(self) -> float:
        return (self.arrival_at - self.departure_at).total_seconds()


class TransportGraph:
    """Directed time-dependent transportation network."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._outgoing: dict[str, list[str]] = {}

    @property
    def nodes(self) -> tuple[GraphNode, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[GraphEdge, ...]:
        return tuple(self._edges.values())

    def add_node(self, node: GraphNode) -> None:
        existing = self._nodes.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(f"Conflicting graph node: {node.id}")
        self._nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.origin_id not in self._nodes:
            raise ValueError(f"Unknown origin node: {edge.origin_id}")
        if edge.destination_id not in self._nodes:
            raise ValueError(f"Unknown destination node: {edge.destination_id}")
        if edge.id in self._edges:
            raise ValueError(f"Duplicate graph edge: {edge.id}")
        if edge.arrival_at <= edge.departure_at:
            raise ValueError(f"Edge {edge.id} must arrive after departure")
        if edge.max_weight_kg <= 0:
            raise ValueError(f"Edge {edge.id} must have positive weight capacity")
        if edge.max_volume_m3 is not None and edge.max_volume_m3 <= 0:
            raise ValueError(f"Edge {edge.id} must have positive volume capacity")
        self._edges[edge.id] = edge
        self._outgoing[edge.origin_id].append(edge.id)

    def outgoing(self, node_id: str) -> tuple[GraphEdge, ...]:
        if node_id not in self._nodes:
            raise KeyError(node_id)
        return tuple(self._edges[edge_id] for edge_id in self._outgoing[node_id])

    def node(self, node_id: str) -> GraphNode:
        return self._nodes[node_id]

    def edge(self, edge_id: str) -> GraphEdge:
        return self._edges[edge_id]
