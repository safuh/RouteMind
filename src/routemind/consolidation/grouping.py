"""Deterministic shipment-group generation for consolidation opportunities."""

from __future__ import annotations

from itertools import combinations

from routemind.domain.models import Shipment
from routemind.paths.models import CandidatePath

from .models import ConsolidationRejection, ConsolidationRejectionReason


def generate_shipment_groups(
    shipment_ids: list[str] | tuple[str, ...],
    *,
    min_group_size: int = 2,
    max_group_size: int | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Generate deterministic unique shipment subsets of the requested sizes."""
    ids = tuple(dict.fromkeys(shipment_ids))
    if min_group_size < 2:
        raise ValueError("min_group_size must be at least 2")
    if max_group_size is None:
        max_group_size = len(ids)
    if max_group_size < min_group_size:
        raise ValueError("max_group_size must be greater than or equal to min_group_size")

    upper = min(max_group_size, len(ids))
    return tuple(group for size in range(min_group_size, upper + 1) for group in combinations(ids, size))


def candidate_paths_by_shipment(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
) -> dict[str, tuple[CandidatePath, ...]]:
    """Group candidate paths by shipment while preserving input order."""
    grouped: dict[str, list[CandidatePath]] = {}
    for path in paths:
        grouped.setdefault(path.shipment_id, []).append(path)
    return {shipment_id: tuple(items) for shipment_id, items in grouped.items()}


def generate_consolidation_groups(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
    shipments: dict[str, Shipment],
    *,
    min_group_size: int = 2,
    max_group_size: int | None = None,
) -> tuple[tuple[CandidatePath, ...], ...]:
    """Generate path groups only when every shipment has at least one candidate path.

    Groups are deterministic: shipment IDs are ordered by first appearance in
    ``paths`` and candidate paths retain their original order.
    """
    by_shipment = candidate_paths_by_shipment(paths)
    ordered_ids = tuple(dict.fromkeys(path.shipment_id for path in paths))
    valid_ids = tuple(shipment_id for shipment_id in ordered_ids if shipment_id in shipments)
    groups = generate_shipment_groups(valid_ids, min_group_size=min_group_size, max_group_size=max_group_size)

    results: list[tuple[CandidatePath, ...]] = []
    for group in groups:
        choices = [by_shipment[shipment_id] for shipment_id in group]
        for selected in _cartesian_product(choices):
            results.append(tuple(selected))
    return tuple(results)


def _cartesian_product(groups: list[tuple[CandidatePath, ...]]) -> list[tuple[CandidatePath, ...]]:
    if not groups:
        return [()]
    result: list[tuple[CandidatePath, ...]] = [()]
    for choices in groups:
        result = [prefix + (choice,) for prefix in result for choice in choices]
    return result


def reject_unknown_shipments(
    shipment_ids: tuple[str, ...],
    shipments: dict[str, Shipment],
) -> tuple[ConsolidationRejection, ...]:
    """Return structured diagnostics for IDs absent from the shipment registry."""
    return tuple(
        ConsolidationRejection(
            reason=ConsolidationRejectionReason.UNKNOWN_SHIPMENT,
            message=f"Shipment {shipment_id!r} is not available to the consolidation engine.",
        )
        for shipment_id in shipment_ids
        if shipment_id not in shipments
    )
