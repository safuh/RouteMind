"""Deterministic shared-segment detection and consolidation feasibility."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from routemind.domain.models import PricingModel, Shipment, TransportOption
from routemind.domain.policies import shipment_is_compatible
from routemind.paths.models import CandidatePath

from .models import (
    ConsolidationOpportunity,
    ConsolidationRejection,
    ConsolidationRejectionReason,
    SharedTransportSegment,
)


def detect_shared_segments(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
) -> dict[tuple[str, str, object, object], tuple[SharedTransportSegment, ...]]:
    """Return concrete scheduled segments used by at least two candidate paths.

    Segment identity deliberately includes the transport option and schedule
    timestamps. Geographic overlap, provider equality, or equal origin/destination
    alone never implies shared capacity.
    """
    occurrences: dict[tuple[str, str, object, object], dict[str, SharedTransportSegment]] = defaultdict(dict)
    for path in paths:
        for leg in path.legs:
            key = (leg.option_id, leg.origin.id, leg.departure_at, leg.arrival_at)
            occurrences[key][path.shipment_id] = SharedTransportSegment(
                option_id=leg.option_id,
                provider_id="",
                provider_name="",
                origin_id=leg.origin.id,
                destination_id=leg.destination.id,
                departure_at=leg.departure_at,
                arrival_at=leg.arrival_at,
            )

    return {
        key: tuple(value.values())
        for key, value in occurrences.items()
        if len(value) >= 2
    }


def _segment_from_option(path: CandidatePath, option: TransportOption) -> SharedTransportSegment | None:
    for leg in path.legs:
        if leg.option_id == option.id:
            return SharedTransportSegment(
                option_id=option.id,
                provider_id=option.provider_id,
                provider_name=option.provider_name,
                origin_id=leg.origin.id,
                destination_id=leg.destination.id,
                departure_at=leg.departure_at,
                arrival_at=leg.arrival_at,
            )
    return None


def _find_schedule(option: TransportOption, segment: SharedTransportSegment):
    return next(
        (
            schedule
            for schedule in option.schedules
            if schedule.departure_at == segment.departure_at
            and schedule.arrival_at == segment.arrival_at
        ),
        None,
    )


def _shipment_cost(shipment: Shipment, option: TransportOption) -> Decimal:
    amount = option.price.amount
    model = option.price.model
    if model in {PricingModel.FIXED, PricingModel.QUOTED}:
        return amount
    if model == PricingModel.PER_KG:
        return amount * Decimal(str(shipment.weight_kg))
    if model == PricingModel.PER_VOLUME:
        return amount * Decimal(str(shipment.volume_m3))
    if option.distance_km is None:
        raise ValueError("distance_km is required for distance-based pricing")
    distance = Decimal(str(option.distance_km))
    if model == PricingModel.PER_KM:
        return amount * distance
    if model == PricingModel.PER_KG_KM:
        return amount * distance * Decimal(str(shipment.weight_kg))
    raise ValueError(f"Unsupported pricing model: {model.value}")


def evaluate_consolidation(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
    shipments: dict[str, Shipment],
    transport_options: dict[str, TransportOption],
) -> ConsolidationOpportunity:
    """Evaluate a proposed shipment group without selecting an optimization plan."""
    shipment_ids = tuple(dict.fromkeys(path.shipment_id for path in paths))
    total_weight = sum(shipments[item].weight_kg for item in shipment_ids if item in shipments)
    total_volume = sum(shipments[item].volume_m3 for item in shipment_ids if item in shipments)
    package_count = sum(
        package.quantity
        for item in shipment_ids
        if item in shipments
        for package in shipments[item].packages
    )

    detected = detect_shared_segments(paths)
    shared = tuple(
        segment
        for segments in detected.values()
        for segment in segments[:1]
    )
    rejections: list[ConsolidationRejection] = []
    standalone_cost = Decimal("0")
    consolidated_cost = Decimal("0")
    currency: str | None = None
    weight_capacity: float | None = None
    volume_capacity: float | None = None

    if not shared:
        rejections.append(
            ConsolidationRejection(
                ConsolidationRejectionReason.NO_SHARED_SEGMENT,
                "Candidate paths do not use the same scheduled transport instance.",
            )
        )

    for segment in shared:
        option = transport_options.get(segment.option_id)
        if option is None:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.UNKNOWN_TRANSPORT_SERVICE,
                    f"Transport option {segment.option_id!r} is not available to the consolidation engine.",
                    segment,
                )
            )
            continue

        resolved = SharedTransportSegment(
            option_id=segment.option_id,
            provider_id=option.provider_id,
            provider_name=option.provider_name,
            origin_id=segment.origin_id,
            destination_id=segment.destination_id,
            departure_at=segment.departure_at,
            arrival_at=segment.arrival_at,
        )
        schedule = _find_schedule(option, resolved)
        if schedule is None:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.UNKNOWN_TRANSPORT_SERVICE,
                    "The shared leg does not match a concrete schedule on the transport option.",
                    resolved,
                )
            )
            continue

        if currency is None:
            currency = option.price.currency
        elif currency != option.price.currency:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.CURRENCY_MISMATCH,
                    "Shared transport costs use incompatible currencies.",
                    resolved,
                )
            )

        weight_capacity = min(
            option.capacity.max_weight_kg,
            schedule.available_weight_kg
            if schedule.available_weight_kg is not None
            else option.capacity.max_weight_kg,
        )
        if option.capacity.max_volume_m3 is not None:
            volume_capacity = option.capacity.max_volume_m3
        if schedule.available_volume_m3 is not None:
            volume_capacity = (
                schedule.available_volume_m3
                if volume_capacity is None
                else min(volume_capacity, schedule.available_volume_m3)
            )

        if total_weight > weight_capacity:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.CAPACITY_WEIGHT,
                    f"Combined shipment weight {total_weight:g} kg exceeds {weight_capacity:g} kg available capacity.",
                    resolved,
                )
            )
        if volume_capacity is not None and total_volume > volume_capacity:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.CAPACITY_VOLUME,
                    f"Combined shipment volume {total_volume:g} m³ exceeds {volume_capacity:g} m³ available capacity.",
                    resolved,
                )
            )

        for shipment_id in shipment_ids:
            shipment = shipments.get(shipment_id)
            if shipment is None:
                continue
            if not shipment_is_compatible(shipment, option):
                rejections.append(
                    ConsolidationRejection(
                        ConsolidationRejectionReason.CARGO_INCOMPATIBILITY,
                        f"Shipment {shipment_id!r} is incompatible with restrictions on the shared service.",
                        resolved,
                    )
                )
            path = next((item for item in paths if item.shipment_id == shipment_id), None)
            if path is not None and not path.deadline_feasible:
                rejections.append(
                    ConsolidationRejection(
                        ConsolidationRejectionReason.PATH_NOT_DEADLINE_FEASIBLE,
                        f"Shipment {shipment_id!r} has a candidate path that is not deadline-feasible.",
                        resolved,
                    )
                )

        try:
            individual = sum((_shipment_cost(shipments[item], option) for item in shipment_ids), Decimal("0"))
            standalone_cost += individual
            if option.price.model in {PricingModel.FIXED, PricingModel.QUOTED}:
                consolidated_cost += option.price.amount
            else:
                consolidated_cost += individual
        except ValueError as exc:
            reason = ConsolidationRejectionReason.MISSING_DISTANCE
            rejections.append(ConsolidationRejection(reason, str(exc), resolved))

    currency = currency or ""
    savings = standalone_cost - consolidated_cost if not rejections else standalone_cost - consolidated_cost
    return ConsolidationOpportunity(
        shipment_ids=shipment_ids,
        shared_segments=shared,
        total_weight_kg=total_weight,
        total_volume_m3=total_volume,
        total_package_count=package_count,
        weight_capacity_kg=weight_capacity,
        volume_capacity_m3=volume_capacity,
        standalone_shared_segment_cost=standalone_cost,
        consolidated_shared_segment_cost=consolidated_cost,
        savings=savings,
        currency=currency,
        feasible=not rejections and len(shipment_ids) >= 2,
        rejections=tuple(rejections),
    )
