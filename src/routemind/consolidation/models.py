"""Domain objects for deterministic shipment consolidation analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class ConsolidationRejectionReason(StrEnum):
    """Machine-readable reasons a consolidation group cannot use a shared segment."""

    NO_SHARED_SEGMENT = "no_shared_segment"
    UNKNOWN_SHIPMENT = "unknown_shipment"
    UNKNOWN_TRANSPORT_SERVICE = "unknown_transport_service"
    CAPACITY_WEIGHT = "capacity_weight"
    CAPACITY_VOLUME = "capacity_volume"
    CARGO_INCOMPATIBILITY = "cargo_incompatibility"
    CURRENCY_MISMATCH = "currency_mismatch"
    MISSING_DISTANCE = "missing_distance"
    INVALID_PRICING = "invalid_pricing"
    PATH_NOT_DEADLINE_FEASIBLE = "path_not_deadline_feasible"


@dataclass(frozen=True, slots=True)
class SharedTransportSegment:
    """A concrete scheduled transport instance that can carry multiple shipments."""

    option_id: str
    provider_id: str
    provider_name: str
    origin_id: str
    destination_id: str
    departure_at: datetime
    arrival_at: datetime

    @property
    def identity(self) -> tuple[str, str, datetime, datetime]:
        """Stable capacity identity: the actual scheduled service instance."""
        return (self.option_id, self.origin_id, self.departure_at, self.arrival_at)


@dataclass(frozen=True, slots=True)
class ConsolidationRejection:
    """Structured explanation for an infeasible consolidation opportunity."""

    reason: ConsolidationRejectionReason
    message: str
    segment: SharedTransportSegment | None = None


@dataclass(frozen=True, slots=True)
class ConsolidationOpportunity:
    """Deterministic feasibility and economics result for a shipment group."""

    shipment_ids: tuple[str, ...]
    shared_segments: tuple[SharedTransportSegment, ...]
    total_weight_kg: float
    total_volume_m3: float
    total_package_count: int
    weight_capacity_kg: float | None
    volume_capacity_m3: float | None
    standalone_shared_segment_cost: Decimal
    consolidated_shared_segment_cost: Decimal
    savings: Decimal
    currency: str
    feasible: bool
    rejections: tuple[ConsolidationRejection, ...] = ()

    @property
    def savings_is_positive(self) -> bool:
        return self.savings > Decimal("0")
