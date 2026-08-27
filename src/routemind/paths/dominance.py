"""Pareto filtering for feasible candidate paths."""

from __future__ import annotations

from .models import CandidatePath


def remove_dominated_paths(paths: list[CandidatePath]) -> list[CandidatePath]:
    """Return non-dominated paths while preserving input order.

    A candidate is removed only when another candidate is no worse on the
    supported path metrics and strictly better on at least one. Cost-only
    sorting is deliberately avoided so meaningful cost/time/reliability
    trade-offs survive for the later portfolio optimizer.
    """
    result: list[CandidatePath] = []
    for candidate in paths:
        if any(existing.dominates(candidate) for existing in paths if existing is not candidate):
            continue
        result.append(candidate)
    return result
