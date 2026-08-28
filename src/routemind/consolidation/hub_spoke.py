"""Deterministic hub-and-spoke consolidation opportunity discovery."""

from __future__ import annotations

from itertools import combinations

from routemind.paths.models import CandidatePath


def common_prefix_option_ids(paths: tuple[CandidatePath, ...]) -> tuple[str, ...]:
    """Return the exact scheduled option-ID prefix shared by every path."""
    if not paths:
        return ()
    prefix = list(paths[0].option_ids)
    for path in paths[1:]:
        length = min(len(prefix), len(path.option_ids))
        prefix = prefix[:next((i for i in range(length) if prefix[i] != path.option_ids[i]), length)]
        if not prefix:
            break
    return tuple(prefix)


def generate_hub_spoke_groups(
    paths: list[CandidatePath] | tuple[CandidatePath, ...],
    *,
    min_group_size: int = 2,
    max_group_size: int | None = None,
) -> tuple[tuple[CandidatePath, ...], ...]:
    """Find groups sharing at least one exact scheduled upstream leg and then branching.

    A hub-and-spoke group requires a common non-empty option prefix and at least
    one path to continue beyond that prefix differently. Option IDs are only the
    candidate-level identity; exact schedule equality is enforced by comparing
    the corresponding TransportLeg timing and locations as well.
    """
    unique: dict[tuple[str, tuple[str, ...]], CandidatePath] = {}
    for path in paths:
        unique[(path.shipment_id, path.option_ids)] = path
    candidates = tuple(unique.values())
    upper = len(candidates) if max_group_size is None else min(max_group_size, len(candidates))
    if min_group_size < 2 or upper < min_group_size:
        return ()

    results: list[tuple[CandidatePath, ...]] = []
    for size in range(min_group_size, upper + 1):
        for group in combinations(candidates, size):
            shipment_ids = {path.shipment_id for path in group}
            if len(shipment_ids) != size:
                continue
            prefix_len = len(common_prefix_option_ids(group))
            if prefix_len == 0 or any(len(path.legs) <= prefix_len for path in group):
                continue
            if not _prefix_legs_equal(group, prefix_len):
                continue
            downstream = {path.option_ids[prefix_len:] for path in group}
            if len(downstream) < 2:
                continue
            results.append(group)
    return tuple(results)


def _prefix_legs_equal(paths: tuple[CandidatePath, ...], prefix_len: int) -> bool:
    reference = paths[0].legs[:prefix_len]
    for path in paths[1:]:
        for left, right in zip(reference, path.legs[:prefix_len]):
            if (
                left.option_id != right.option_id
                or left.origin.id != right.origin.id
                or left.destination.id != right.destination.id
                or left.departure_at != right.departure_at
                or left.arrival_at != right.arrival_at
            ):
                return False
    return True
