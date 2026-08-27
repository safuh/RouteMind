"""Deterministic time-window checks for consolidation candidates."""

from __future__ import annotations

from routemind.domain.models import Shipment
from routemind.paths.models import CandidatePath

from .models import ConsolidationRejection, ConsolidationRejectionReason


def check_path_time_window(
    path: CandidatePath,
    shipment: Shipment,
) -> tuple[ConsolidationRejection, ...]:
    """Validate a complete candidate path against shipment readiness/deadline."""
    rejections: list[ConsolidationRejection] = []
    if path.departure_at < shipment.ready_at:
        rejections.append(
            ConsolidationRejection(
                ConsolidationRejectionReason.PATH_NOT_DEADLINE_FEASIBLE,
                f"Shipment {shipment.id!r} is not ready before candidate departure at {path.departure_at.isoformat()}.",
            )
        )
    if shipment.deadline is not None and path.arrival_at > shipment.deadline:
        rejections.append(
            ConsolidationRejection(
                ConsolidationRejectionReason.PATH_NOT_DEADLINE_FEASIBLE,
                f"Candidate arrival at {path.arrival_at.isoformat()} exceeds shipment {shipment.id!r} deadline {shipment.deadline.isoformat()}.",
            )
        )
    if not path.deadline_feasible:
        rejections.append(
            ConsolidationRejection(
                ConsolidationRejectionReason.PATH_NOT_DEADLINE_FEASIBLE,
                f"Candidate path for shipment {shipment.id!r} is already marked deadline-infeasible.",
            )
        )
    return tuple(rejections)


def check_group_time_windows(
    paths: tuple[CandidatePath, ...] | list[CandidatePath],
    shipments: dict[str, Shipment],
) -> tuple[ConsolidationRejection, ...]:
    """Validate every selected path independently against its shipment window."""
    rejections: list[ConsolidationRejection] = []
    for path in paths:
        shipment = shipments.get(path.shipment_id)
        if shipment is None:
            rejections.append(
                ConsolidationRejection(
                    ConsolidationRejectionReason.UNKNOWN_SHIPMENT,
                    f"Shipment {path.shipment_id!r} is not available to the consolidation engine.",
                )
            )
            continue
        rejections.extend(check_path_time_window(path, shipment))
    return tuple(rejections)
