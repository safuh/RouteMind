"""Deterministic shipment-group generation for consolidation opportunities."""

from __future__ import annotations

from itertools import combinations

from routemind.domain.models import Shipment, TransportOption
from routemind.paths.models import CandidatePath

from .engine import evaluate_consolidation
from .models import ConsolidationOpportunity, ConsolidationRejection, ConsolidationRejectionReason
from .reservation import reserve_opportunities


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


def generate_consolidation_opportunities(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
    shipments: dict[str, Shipment],
    transport_options: dict[str, TransportOption],
    *,
    min_group_size: int = 2,
    max_group_size: int | None = None,
) -> tuple[ConsolidationOpportunity, ...]:
    """Evaluate every deterministic candidate group and retain feasible opportunities.

    Candidate path combinations are expanded before feasibility evaluation, so a
    shipment group is not incorrectly tied to the first path discovered for each
    shipment. The returned opportunities preserve deterministic input order.
    """
    opportunities: list[ConsolidationOpportunity] = []
    for group in generate_consolidation_groups(
        paths,
        shipments,
        min_group_size=min_group_size,
        max_group_size=max_group_size,
    ):
        opportunity = evaluate_consolidation(group, shipments, transport_options)
        if opportunity.feasible:
            opportunities.append(opportunity)
    return tuple(opportunities)


def generate_coexisting_opportunity_combinations(
    opportunities: list[ConsolidationOpportunity] | tuple[ConsolidationOpportunity, ...],
    shipments: dict[str, Shipment],
    transport_options: dict[str, TransportOption],
) -> tuple[tuple[ConsolidationOpportunity, ...], ...]:
    """Enumerate every feasible, mutually compatible consolidation portfolio.

    Two opportunities may coexist when their combined reservations remain within
    every scheduled service's capacity and no shipment is reserved twice. This
    intentionally evaluates capacity across the whole combination rather than
    treating each opportunity as independently feasible.

    The empty combination is included because selecting no consolidation is a
    valid portfolio baseline. Results are deterministic and preserve opportunity
    input order.
    """
    ordered = tuple(opportunity for opportunity in opportunities if opportunity.feasible)
    results: list[tuple[ConsolidationOpportunity, ...]] = [()]

    def visit(
        start: int,
        selected: tuple[ConsolidationOpportunity, ...],
    ) -> None:
        for index in range(start, len(ordered)):
            candidate = ordered[index]
            trial = selected + (candidate,)
            _, reservation_results = reserve_opportunities(trial, shipments, transport_options)
            if not all(result.accepted for result in reservation_results):
                continue
            results.append(trial)
            visit(index + 1, trial)

    visit(0, ())
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
