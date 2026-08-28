"""Deterministic shared-segment detection and consolidation feasibility.

This module does not choose a portfolio plan. It identifies concrete scheduled
transport instances that multiple already-feasible candidate paths can share
and evaluates the aggregate constraints/economics for that opportunity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from routemind.domain.models import Package, Shipment, TransportOption, TransportSchedule

from .models import CandidatePath


@dataclass(frozen=True, slots=True)
class SharedSegment:
    """A concrete scheduled transport instance shared by candidate paths."""

    option_id: str
    origin_id: str
    destination_id: str
    departure_at: datetime
    arrival_at: datetime

    @classmethod
    def from_leg(cls, leg) -> "SharedSegment":
        return cls(leg.option_id, leg.origin.id, leg.destination.id, leg.departure_at, leg.arrival_at)


class ConsolidationRejectionReason(str):
    CAPACITY = "capacity"
    VOLUME_CAPACITY = "volume_capacity"
    CARGO_RESTRICTION = "cargo_restriction"
    DEADLINE = "deadline"
    SCHEDULE = "schedule"
    CURRENCY = "currency"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ConsolidationRejection:
    reason: str
    message: str


@dataclass(frozen=True, slots=True)
class ConsolidationOpportunity:
    """Feasible sharing opportunity for one scheduled transport segment."""

    segment: SharedSegment
    shipment_ids: tuple[str, ...]
    total_weight_kg: float
    total_volume_m3: float
    capacity_utilization: float
    baseline_segment_cost: Decimal
    consolidated_segment_cost: Decimal
    savings: Decimal
    currency: str
    feasible: bool = True
    rejection: ConsolidationRejection | None = None


class ConsolidationEngine:
    """Find and validate capacity-sharing opportunities across candidate paths."""

    def __init__(self, options: list[TransportOption]) -> None:
        self._options = {option.id: option for option in options}
        if len(self._options) != len(options):
            raise ValueError("Duplicate transport option IDs are not allowed")

    def detect_shared_segments(
        self,
        paths_by_shipment: dict[str, list[CandidatePath]],
    ) -> dict[SharedSegment, tuple[tuple[str, CandidatePath], ...]]:
        """Return concrete scheduled segments appearing in at least two paths."""
        occurrences: dict[SharedSegment, list[tuple[str, CandidatePath]]] = {}
        for shipment_id, paths in paths_by_shipment.items():
            seen_for_shipment: set[SharedSegment] = set()
            for path in paths:
                for leg in path.legs:
                    segment = SharedSegment.from_leg(leg)
                    if segment in seen_for_shipment:
                        continue
                    seen_for_shipment.add(segment)
                    occurrences.setdefault(segment, []).append((shipment_id, path))
        return {segment: tuple(items) for segment, items in occurrences.items() if len(items) >= 2}

    def evaluate(
        self,
        segment: SharedSegment,
        shipment_ids: tuple[str, ...],
        shipments: dict[str, Shipment],
    ) -> ConsolidationOpportunity:
        """Evaluate aggregate constraints and segment-level consolidation economics."""
        if len(shipment_ids) < 2:
            raise ValueError("A consolidation opportunity requires at least two shipments")
        missing = tuple(shipment_id for shipment_id in shipment_ids if shipment_id not in shipments)
        if missing:
            raise ValueError(f"Unknown shipment IDs: {', '.join(missing)}")
        try:
            option = self._options[segment.option_id]
        except KeyError as exc:
            raise ValueError(f"Unknown transport option: {segment.option_id}") from exc

        if not option.available:
            return self._rejected(segment, shipment_ids, "", ConsolidationRejectionReason.UNAVAILABLE, "Transport option is unavailable")
        schedule = self._matching_schedule(option, segment)
        if schedule is None:
            return self._rejected(segment, shipment_ids, "", ConsolidationRejectionReason.SCHEDULE, "Shared segment does not match an available schedule")

        selected = [shipments[item] for item in shipment_ids]
        total_weight = sum(item.weight_kg for item in selected)
        total_volume = sum(item.volume_m3 for item in selected)
        weight_capacity = min(option.capacity.max_weight_kg, schedule.available_weight_kg or option.capacity.max_weight_kg)
        volume_capacity = option.capacity.max_volume_m3
        if schedule.available_volume_m3 is not None:
            volume_capacity = schedule.available_volume_m3 if volume_capacity is None else min(volume_capacity, schedule.available_volume_m3)
        if total_weight > weight_capacity:
            return self._rejected(segment, shipment_ids, option.price.currency, ConsolidationRejectionReason.CAPACITY, "Combined shipment weight exceeds shared schedule capacity", total_weight, total_volume, weight_capacity)
        if volume_capacity is not None and total_volume > volume_capacity:
            return self._rejected(segment, shipment_ids, option.price.currency, ConsolidationRejectionReason.VOLUME_CAPACITY, "Combined shipment volume exceeds shared schedule capacity", total_weight, total_volume, volume_capacity, volume=True)
        if any(not self._cargo_compatible(shipment, option) for shipment in selected):
            return self._rejected(segment, shipment_ids, option.price.currency, ConsolidationRejectionReason.CARGO_RESTRICTION, "At least one shipment is incompatible with the shared transport restrictions", total_weight, total_volume, weight_capacity)
        if any(shipment.deadline is not None and segment.arrival_at > shipment.deadline for shipment in selected):
            return self._rejected(segment, shipment_ids, option.price.currency, ConsolidationRejectionReason.DEADLINE, "Shared segment arrival exceeds at least one shipment deadline", total_weight, total_volume, weight_capacity)

        currencies = {option.price.currency}
        if len(currencies) != 1:
            return self._rejected(segment, shipment_ids, option.price.currency, ConsolidationRejectionReason.CURRENCY, "Shared segment prices must use one currency", total_weight, total_volume, weight_capacity)
        baseline = sum((self._segment_price(option, shipment) for shipment in selected), Decimal("0"))
        consolidated = self._consolidated_price(option, selected)
        utilization = max(total_weight / weight_capacity, (total_volume / volume_capacity) if volume_capacity else 0.0)
        return ConsolidationOpportunity(segment, shipment_ids, total_weight, total_volume, utilization, baseline, consolidated, baseline - consolidated, option.price.currency)

    def _rejected(self, segment, shipment_ids, currency, reason, message, total_weight=0.0, total_volume=0.0, capacity=1.0, *, volume=False):
        utilization = (total_volume / capacity) if volume else (total_weight / capacity)
        return ConsolidationOpportunity(segment, shipment_ids, total_weight, total_volume, utilization, Decimal("0"), Decimal("0"), Decimal("0"), currency or "", False, ConsolidationRejection(reason, message))

    @staticmethod
    def _matching_schedule(option: TransportOption, segment: SharedSegment) -> TransportSchedule | None:
        for schedule in option.schedules:
            if schedule.departure_at == segment.departure_at and schedule.arrival_at == segment.arrival_at:
                return schedule
        return None

    @staticmethod
    def _cargo_compatible(shipment: Shipment, option: TransportOption) -> bool:
        restrictions = {item.lower() for item in option.restrictions}
        return not (
            ("no_fragile" in restrictions and any(package.fragile for package in shipment.packages))
            or ("no_temperature_controlled" in restrictions and any(package.temperature_controlled for package in shipment.packages))
            or ("fragile_only" in restrictions and not all(package.fragile for package in shipment.packages))
            or ("temperature_controlled_only" in restrictions and not all(package.temperature_controlled for package in shipment.packages))
        )

    @staticmethod
    def _segment_price(option: TransportOption, shipment: Shipment) -> Decimal:
        amount = option.price.amount
        model = option.price.model.value
        if model in {"fixed", "quoted"}:
            return amount
        if model == "per_kg":
            return amount * Decimal(str(shipment.weight_kg))
        if model == "per_volume":
            return amount * Decimal(str(shipment.volume_m3))
        if model == "per_km":
            if option.distance_km is None:
                raise ValueError("distance_km is required for per_km pricing")
            return amount * Decimal(str(option.distance_km))
        if model == "per_kg_km":
            if option.distance_km is None:
                raise ValueError("distance_km is required for per_kg_km pricing")
            return amount * Decimal(str(option.distance_km)) * Decimal(str(shipment.weight_kg))
        raise ValueError(f"Unsupported pricing model: {model}")

    @classmethod
    def _consolidated_price(cls, option: TransportOption, shipments: list[Shipment]) -> Decimal:
        model = option.price.model.value
        if model in {"fixed", "quoted"}:
            return option.price.amount
        if model == "per_kg":
            return option.price.amount * Decimal(str(sum(item.weight_kg for item in shipments)))
        if model == "per_volume":
            return option.price.amount * Decimal(str(sum(item.volume_m3 for item in shipments)))
        if model == "per_km":
            if option.distance_km is None:
                raise ValueError("distance_km is required for per_km pricing")
            return option.price.amount * Decimal(str(option.distance_km))
        if model == "per_kg_km":
            if option.distance_km is None:
                raise ValueError("distance_km is required for per_kg_km pricing")
            return option.price.amount * Decimal(str(option.distance_km)) * Decimal(str(sum(item.weight_kg for item in shipments)))
        raise ValueError(f"Unsupported pricing model: {model}")
