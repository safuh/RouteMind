"""Deterministic portfolio optimization over candidate shipment paths."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from ortools.sat.python import cp_model

from routemind.consolidation.models import ConsolidationOpportunity, SharedTransportSegment
from routemind.domain.models import OptimizationPolicy, OptimizationResult, TransportLeg, TransportOption, TransportPlan
from routemind.paths.models import CandidatePath

_SCALE = 1000


def _int(value: float) -> int:
    return int(round(value * _SCALE))


def _segment_identity(leg: TransportLeg) -> tuple[str, str, object, object]:
    return (leg.option_id, leg.origin.id, leg.departure_at, leg.arrival_at)


def optimize_portfolio(
    candidate_paths: Iterable[CandidatePath],
    transport_options: dict[str, TransportOption],
    policy: OptimizationPolicy | None = None,
    consolidation_opportunities: Iterable[ConsolidationOpportunity] = (),
    max_time_seconds: float = 30.0,
) -> OptimizationResult:
    """Choose one path per shipment while enforcing portfolio capacity.

    CP-SAT owns the portfolio decision. Consolidation opportunities contribute a
    bonus only when the selected path for every participating shipment contains
    every exact scheduled segment in the opportunity.
    """
    policy = policy or OptimizationPolicy()
    paths = tuple(path for path in candidate_paths if path.deadline_feasible)
    opportunities = tuple(consolidation_opportunities)
    by_shipment: dict[str, list[int]] = defaultdict(list)
    for index, path in enumerate(paths):
        by_shipment[path.shipment_id].append(index)

    if not by_shipment or any(not indices for indices in by_shipment.values()):
        return OptimizationResult(
            plans=[], objective_value=0.0, feasible=False,
            warnings=["No deadline-feasible candidate path exists for at least one shipment."],
        )

    currencies = {path.currency for path in paths}
    if len(currencies) != 1:
        return OptimizationResult(
            plans=[], objective_value=0.0, feasible=False,
            warnings=["Candidate paths contain multiple currencies; normalize currency before optimization."],
        )

    model = cp_model.CpModel()
    selected = [model.new_bool_var(f"path_{index}") for index in range(len(paths))]
    for shipment_id, indices in sorted(by_shipment.items()):
        model.add_exactly_one(selected[index] for index in indices)

    segment_paths: dict[tuple[str, str, object, object], list[tuple[int, float, float]]] = defaultdict(list)
    segment_caps: dict[tuple[str, str, object, object], tuple[float | None, float | None]] = {}
    for index, path in enumerate(paths):
        for leg in path.legs:
            identity = _segment_identity(leg)
            segment_paths[identity].append((index, leg.allocated_weight_kg, leg.allocated_volume_m3))
            option = transport_options.get(leg.option_id)
            if option is None:
                continue
            schedule = next(
                (s for s in option.schedules if s.departure_at == leg.departure_at and s.arrival_at == leg.arrival_at),
                None,
            )
            if schedule is not None:
                segment_caps[identity] = (
                    schedule.available_weight_kg if schedule.available_weight_kg is not None else option.capacity.max_weight_kg,
                    schedule.available_volume_m3 if schedule.available_volume_m3 is not None else option.capacity.max_volume_m3,
                )

    for identity, entries in segment_paths.items():
        weight_cap, volume_cap = segment_caps.get(identity, (None, None))
        if weight_cap is not None:
            model.add(sum(_int(weight) * selected[index] for index, weight, _ in entries) <= _int(weight_cap))
        if volume_cap is not None:
            model.add(sum(_int(volume) * selected[index] for index, _, volume in entries) <= _int(volume_cap))

    objective_terms = []
    for index, path in enumerate(paths):
        value = float(path.total_cost) * policy.cost_weight
        value += path.elapsed_seconds / 3600 * policy.time_weight
        value -= path.reliability * policy.reliability_weight
        value += (path.emissions_kg_co2e or 0.0) * policy.carbon_weight
        value += path.number_of_transfers * (1.0 if policy.minimize_transfers else 0.0)
        objective_terms.append(_int(value) * selected[index])

    opportunity_vars: list[tuple[cp_model.IntVar, ConsolidationOpportunity]] = []
    shipment_op_vars: dict[str, list[cp_model.IntVar]] = defaultdict(list)
    for op_index, opportunity in enumerate(opportunities):
        if not opportunity.feasible or opportunity.savings < 0 or not opportunity.shared_segments:
            continue
        participation_vars: list[cp_model.IntVar] = []
        for shipment_id in opportunity.shipment_ids:
            matching = [
                selected[index]
                for index in by_shipment.get(shipment_id, [])
                if all(_segment_in_path(segment, paths[index]) for segment in opportunity.shared_segments)
            ]
            if not matching:
                participation_vars = []
                break
            marker = model.new_bool_var(f"op_{op_index}_{shipment_id}")
            model.add_max_equality(marker, matching)
            participation_vars.append(marker)
        if len(participation_vars) != len(opportunity.shipment_ids):
            continue

        op_var = model.new_bool_var(f"consolidation_{op_index}")
        for marker in participation_vars:
            model.add(op_var <= marker)
        model.add(op_var >= sum(participation_vars) - len(participation_vars) + 1)
        for shipment_id in opportunity.shipment_ids:
            shipment_op_vars[shipment_id].append(op_var)
        opportunity_vars.append((op_var, opportunity))
        objective_terms.append(-_int(float(opportunity.savings) * policy.consolidation_weight) * op_var)

    # A shipment can participate in at most one accepted consolidation
    # opportunity. This prevents double-counting savings/resources.
    for variables in shipment_op_vars.values():
        model.add(sum(variables) <= 1)

    model.minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return OptimizationResult(
            plans=[], objective_value=0.0, feasible=False,
            warnings=[f"CP-SAT returned {solver.status_name(status)}."],
        )

    plans: list[TransportPlan] = []
    total_cost = Decimal("0")
    total_transit = 0.0
    total_reliability = 1.0
    total_emissions = 0.0
    for index, path in enumerate(paths):
        if not solver.value(selected[index]):
            continue
        plans.append(
            TransportPlan(
                shipment_id=path.shipment_id,
                legs=list(path.legs),
                total_cost=path.total_cost,
                currency=path.currency,
                total_transit_seconds=path.elapsed_seconds,
                reliability=path.reliability,
            )
        )
        total_cost += path.total_cost
        total_transit += path.elapsed_seconds
        total_reliability *= path.reliability
        total_emissions += path.emissions_kg_co2e or 0.0

    consolidation_savings = sum(
        (op.savings for var, op in opportunity_vars if solver.value(var)), Decimal("0")
    )
    total_cost -= consolidation_savings
    return OptimizationResult(
        plans=plans,
        objective_value=solver.objective_value / _SCALE,
        feasible=True,
        metrics={
            "shipment_count": float(len(plans)),
            "total_cost": float(total_cost),
            "total_transit_seconds": total_transit,
            "portfolio_reliability": total_reliability,
            "emissions_kg_co2e": total_emissions,
            "consolidation_savings": float(consolidation_savings),
            "solver_wall_time_seconds": solver.wall_time,
        },
    )


def _segment_in_path(segment: SharedTransportSegment, path: CandidatePath) -> bool:
    identity = segment.identity
    return any(_segment_identity(leg) == identity for leg in path.legs)
