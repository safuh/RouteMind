"""Pure domain-level feasibility checks used before optimization."""

from __future__ import annotations

from datetime import datetime

from .models import Shipment, TransportOption, TransportSchedule


def schedule_is_valid(schedule: TransportSchedule) -> bool:
    """Return whether a transport schedule has a positive duration."""
    return schedule.arrival_at > schedule.departure_at


def shipment_timing_is_valid(shipment: Shipment) -> bool:
    """Return whether a shipment deadline, when present, follows readiness."""
    return shipment.deadline is None or shipment.deadline > shipment.ready_at


def transport_can_carry_shipment(
    shipment: Shipment,
    option: TransportOption,
    *,
    available_weight_kg: float | None = None,
    available_volume_m3: float | None = None,
) -> bool:
    """Check weight and volume constraints, including schedule-specific capacity."""
    weight_capacity = option.capacity.max_weight_kg
    if available_weight_kg is not None:
        weight_capacity = min(weight_capacity, available_weight_kg)
    if shipment.weight_kg > weight_capacity:
        return False

    volume_capacity = option.capacity.max_volume_m3
    if available_volume_m3 is not None:
        volume_capacity = available_volume_m3 if volume_capacity is None else min(volume_capacity, available_volume_m3)
    if volume_capacity is not None and shipment.volume_m3 > volume_capacity:
        return False

    return option.available


def schedule_is_available_after(
    schedule: TransportSchedule,
    ready_at: datetime,
) -> bool:
    """Return whether the service can be boarded after a shipment is ready."""
    return schedule.departure_at >= ready_at and schedule_is_valid(schedule)
