"""Deterministic shipment consolidation primitives.

This module identifies opportunities for shipments to consume the same
scheduled transport instance. It intentionally does not choose a portfolio
solution; that decision belongs to the later optimization layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from itertools import combinations
from typing import Iterable

from routemind.domain.models import Shipment, TransportLeg, TransportOption
from routemind.paths.models import CandidatePath


class ConsolidationRejectionReason(StrEnum):
    EMPTY_GROUP = "empty_group"
    DIFFERENT_CURRENCY = "different_currency"
    CAPACITY_WEIGHT = "weight_capacity"
    CAPACITY_VOLUME = "volume_capacity"
    DEADLINE = "deadline"
    READY_TIME = "ready_time"
    UNAVAILABLE = "unavailable"
    CARGO_INCOMPATIBLE = "cargo_incompatible"
    SERVICE_MISMATCH = "service_mismatch"


@dataclass(frozen=True)
class SharedSegment:
    """A concrete scheduled transport instance shared by candidate paths."""

    option_id: str
    origin_id: str
    destination_id: str
    departure_at: datetime
    arrival_at: datetime

    @classmethod
    def from_leg(cls, leg: TransportLeg) -> "SharedSegment":
        return cls(
            option_id=leg.option_id,
            origin_id=leg.origin.id,
            destination_id=leg.destination.id,
            departure_at=leg.departure_at,
            arrival_at=leg.arrival_at,
        )


@dataclass(frozen=True)
class ConsolidationRejection:
    reason: ConsolidationRejectionReason
    message: str


@dataclass(frozen=True)
class ConsolidationOpportunity:
    """A feasible group of shipments sharing one scheduled transport leg."""

    segment: SharedSegment
    shipment_ids: tuple[str, ...]
    total_weight_kg: float
    total_volume_m3: float
    weight_utilization: float
    volume_utilization: float | None
    baseline_cost: Decimal
    consolidated_cost: Decimal
    savings: Decimal
    currency: str


@dataclass(frozen=True)
class ConsolidationEvaluation:
    opportunity: ConsolidationOpportunity | None
    rejection: ConsolidationRejection | None = None


class ConsolidationEngine:
    """Evaluate deterministic consolidation opportunities for candidate paths."""

    def evaluate(
        self,
        shipments: Iterable[Shipment],
        paths: Iterable[CandidatePath],
        options: Iterable[TransportOption],
    ) -> list[ConsolidationEvaluation]:
        shipment_map = {shipment.id: shipment for shipment in shipments}
        option_map = {option.id: option for option in options}
        by_segment: dict[SharedSegment, list[CandidatePath]] = {}

        for path in paths:
            for leg in path.legs:
                by_segment.setdefault(SharedSegment.from_leg(leg), []).append(path)

        evaluations: list[ConsolidationEvaluation] = []
        for segment, segment_paths in by_segment.items():
            unique: dict[str, CandidatePath] = {path.shipment_id: path for path in segment_paths}
            if len(unique) < 2:
                continue
            ordered = list(unique.values())
            for left, right in combinations(ordered, 2):
                evaluations.append(
                    self._evaluate_pair(
                        segment,
                        left,
                        right,
                        shipment_map,
                        option_map,
                    )
                )
        return evaluations

    def _evaluate_pair(
        self,
        segment: SharedSegment,
        left: CandidatePath,
        right: CandidatePath,
        shipments: dict[str, Shipment],
        options: dict[str, TransportOption],
    ) -> ConsolidationEvaluation:
        if left.currency != right.currency:
            return self._reject(ConsolidationRejectionReason.DIFFERENT_CURRENCY, "Paths use different currencies")

        shipment_left = shipments[left.shipment_id]
        shipment_right = shipments[right.shipment_id]
        option = options.get(segment.option_id)
        if option is None or not option.available:
            return self._reject(ConsolidationRejectionReason.UNAVAILABLE, "Shared transport service is unavailable")

        if shipment_left.ready_at > segment.departure_at or shipment_right.ready_at > segment.departure_at:
            return self._reject(ConsolidationRejectionReason.READY_TIME, "A shipment is not ready for the shared departure")

        if shipment_left.deadline and segment.arrival_at > shipment_left.deadline:
            return self._reject(ConsolidationRejectionReason.DEADLINE, "Shared segment misses the first shipment deadline")
        if shipment_right.deadline and segment.arrival_at > shipment_right.deadline:
            return self._reject(ConsolidationRejectionReason.DEADLINE, "Shared segment misses the second shipment deadline")

        if not self._cargo_compatible(shipment_left, shipment_right, option):
            return self._reject(ConsolidationRejectionReason.CARGO_INCOMPATIBLE, "Shipment cargo is incompatible with shared transport")

        total_weight = shipment_left.weight_kg + shipment_right.weight_kg
        total_volume = shipment_left.volume_m3 + shipment_right.volume_m3
        schedule = self._schedule_for(option, segment)
        max_weight = schedule.available_weight_kg if schedule and schedule.available_weight_kg is not None else option.capacity.max_weight_kg
        max_volume = schedule.available_volume_m3 if schedule and schedule.available_volume_m3 is not None else option.capacity.max_volume_m3

        if total_weight > max_weight:
            return self._reject(ConsolidationRejectionReason.CAPACITY_WEIGHT, "Combined shipment weight exceeds shared capacity")
        if max_volume is not None and total_volume > max_volume:
            return self._reject(ConsolidationRejectionReason.CAPACITY_VOLUME, "Combined shipment volume exceeds shared capacity")

        baseline = left.total_cost + right.total_cost
        shared_leg_cost = self._price(option, total_weight, total_volume)
        # Existing candidate costs represent complete shipment paths. To avoid
        # inventing a new downstream pricing model, savings are reported only
        # against the two candidate costs minus the shared leg price.
        consolidated = shared_leg_cost
        savings = baseline - consolidated
        weight_utilization = total_weight / max_weight
        volume_utilization = total_volume / max_volume if max_volume is not None else None

        return ConsolidationEvaluation(
            opportunity=ConsolidationOpportunity(
                segment=segment,
                shipment_ids=(left.shipment_id, right.shipment_id),
                total_weight_kg=total_weight,
                total_volume_m3=total_volume,
                weight_utilization=weight_utilization,
                volume_utilization=volume_utilization,
                baseline_cost=baseline,
                consolidated_cost=consolidated,
                savings=savings,
                currency=left.currency,
            )
        )

    @staticmethod
    def _schedule_for(option: TransportOption, segment: SharedSegment):
        for schedule in option.schedules:
            if schedule.departure_at == segment.departure_at and schedule.arrival_at == segment.arrival_at:
                return schedule
        return None

    @staticmethod
    def _cargo_compatible(left: Shipment, right: Shipment, option: TransportOption) -> bool:
        if "fragile_only" in option.restrictions:
            return all(package.fragile for package in left.packages + right.packages)
        if "no_temperature_control" in option.restrictions:
            return not any(package.temperature_controlled for package in left.packages + right.packages)
        return True

    @staticmethod
    def _price(option: TransportOption, weight: float, volume: float) -> Decimal:
        amount = option.price.amount
        if option.price.model.value == "fixed" or option.price.model.value == "quoted":
            return amount
        if option.price.model.value == "per_kg":
            return amount * Decimal(str(weight))
        if option.price.model.value == "per_volume":
            return amount * Decimal(str(volume))
        if option.price.model.value == "per_km":
            if option.distance_km is None:
                raise ValueError("Distance is required for per-km consolidation pricing")
            return amount * Decimal(str(option.distance_km))
        if option.price.model.value == "per_kg_km":
            if option.distance_km is None:
                raise ValueError("Distance is required for per-kg-km consolidation pricing")
            return amount * Decimal(str(weight)) * Decimal(str(option.distance_km))
        raise ValueError(f"Unsupported pricing model: {option.price.model}")

    @staticmethod
    def _reject(reason: ConsolidationRejectionReason, message: str) -> ConsolidationEvaluation:
        return ConsolidationEvaluation(
            opportunity=None,
            rejection=ConsolidationRejection(reason=reason, message=message),
        )
