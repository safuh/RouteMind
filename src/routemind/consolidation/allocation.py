"""Deterministic allocation of shared and shipment-specific transport legs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from routemind.domain.models import PricingModel, Shipment, TransportOption, TransportLeg
from routemind.paths.models import CandidatePath

from .models import SharedTransportSegment


@dataclass(frozen=True, slots=True)
class SegmentAllocation:
    """Capacity and cost attributed to a concrete scheduled segment."""

    segment: SharedTransportSegment
    shipment_ids: tuple[str, ...]
    weight_kg: float
    volume_m3: float
    package_count: int
    shared: bool
    allocated_cost: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class ConsolidationAllocation:
    """Complete allocation of a candidate-path group across shared/private legs."""

    shipment_ids: tuple[str, ...]
    shared: tuple[SegmentAllocation, ...]
    private: dict[str, tuple[SegmentAllocation, ...]]

    @property
    def all_segments(self) -> tuple[SegmentAllocation, ...]:
        return self.shared + tuple(
            segment
            for shipment_id in self.shipment_ids
            for segment in self.private.get(shipment_id, ())
        )

    @property
    def total_cost(self) -> Decimal:
        return sum((segment.allocated_cost for segment in self.all_segments), Decimal("0"))


def _segment_key(leg: TransportLeg) -> tuple[str, str, str, object, object]:
    return (leg.option_id, leg.origin.id, leg.destination.id, leg.departure_at, leg.arrival_at)


def _segment_from_leg(leg: TransportLeg, option: TransportOption) -> SharedTransportSegment:
    return SharedTransportSegment(
        option_id=leg.option_id,
        provider_id=option.provider_id,
        provider_name=option.provider_name,
        origin_id=leg.origin.id,
        destination_id=leg.destination.id,
        departure_at=leg.departure_at,
        arrival_at=leg.arrival_at,
    )


def _leg_cost(shipment: Shipment, option: TransportOption) -> Decimal:
    amount = option.price.amount
    model = option.price.model
    if model in {PricingModel.FIXED, PricingModel.QUOTED}:
        return amount
    if model == PricingModel.PER_KG:
        return amount * Decimal(str(shipment.weight_kg))
    if model == PricingModel.PER_VOLUME:
        return amount * Decimal(str(shipment.volume_m3))
    if option.distance_km is None:
        raise ValueError(f"distance_km is required for {model.value} pricing on {option.id!r}")
    distance = Decimal(str(option.distance_km))
    if model == PricingModel.PER_KM:
        return amount * distance
    if model == PricingModel.PER_KG_KM:
        return amount * distance * Decimal(str(shipment.weight_kg))
    raise ValueError(f"Unsupported pricing model: {model.value}")


def allocate_consolidation(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
    shipments: dict[str, Shipment],
    transport_options: dict[str, TransportOption],
) -> ConsolidationAllocation:
    """Allocate every leg into shared or shipment-private capacity buckets.

    A segment is shared only when the exact scheduled service instance is used
    by at least two shipments. Downstream legs remain private when their
    concrete scheduled segment is used by one shipment only.
    """
    shipment_ids = tuple(dict.fromkeys(path.shipment_id for path in paths))
    occurrences: dict[tuple[str, str, str, object, object], list[tuple[str, TransportLeg]]] = defaultdict(list)
    for path in paths:
        for leg in path.legs:
            occurrences[_segment_key(leg)].append((path.shipment_id, leg))

    shared: list[SegmentAllocation] = []
    private: dict[str, list[SegmentAllocation]] = defaultdict(list)

    for entries in occurrences.values():
        shipment_ids_on_segment = tuple(dict.fromkeys(shipment_id for shipment_id, _ in entries))
        first_leg = entries[0][1]
        option = transport_options.get(first_leg.option_id)
        if option is None:
            raise KeyError(f"Unknown transport option {first_leg.option_id!r}")

        weight = sum(shipments[sid].weight_kg for sid in shipment_ids_on_segment)
        volume = sum(shipments[sid].volume_m3 for sid in shipment_ids_on_segment)
        packages = sum(
            package.quantity
            for sid in shipment_ids_on_segment
            for package in shipments[sid].packages
        )
        segment = _segment_from_leg(first_leg, option)
        is_shared = len(shipment_ids_on_segment) >= 2

        if is_shared and option.price.model in {PricingModel.FIXED, PricingModel.QUOTED}:
            cost = option.price.amount
        else:
            cost = sum((_leg_cost(shipments[sid], option) for sid in shipment_ids_on_segment), Decimal("0"))

        allocation = SegmentAllocation(
            segment=segment,
            shipment_ids=shipment_ids_on_segment,
            weight_kg=weight,
            volume_m3=volume,
            package_count=packages,
            shared=is_shared,
            allocated_cost=cost,
            currency=option.price.currency,
        )
        if is_shared:
            shared.append(allocation)
        else:
            private[shipment_ids_on_segment[0]].append(allocation)

    shared.sort(key=lambda item: item.segment.identity)
    ordered_private = {
        shipment_id: tuple(private.get(shipment_id, ()))
        for shipment_id in shipment_ids
    }
    return ConsolidationAllocation(
        shipment_ids=shipment_ids,
        shared=tuple(shared),
        private=ordered_private,
    )
