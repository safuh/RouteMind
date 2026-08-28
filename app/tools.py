"""Structured ADK tools that delegate decisions to deterministic RouteMind engines."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from routemind.domain.models import (
    OptimizationPolicy,
    OptimizationResult,
    Shipment,
    TransportOption,
)
from routemind.optimization import optimize_portfolio
from routemind.paths import PathSearchEngine
from routemind.paths.models import CandidatePath


def extract_optimization_policy(request: str) -> dict[str, Any]:
    """Normalize explicit business objective keywords into a deterministic policy."""
    text = request.lower()
    policy = OptimizationPolicy()
    updates: dict[str, Any] = {}
    if any(word in text for word in ("fast", "quick", "speed", "time", "urgent")):
        updates["time_weight"] = 10.0
    if any(word in text for word in ("reliable", "reliability", "on-time")):
        updates["reliability_weight"] = 100.0
    if any(word in text for word in ("carbon", "emission", "green", "environment")):
        updates["carbon_weight"] = 10.0
    if any(word in text for word in ("consolidat", "combine", "shared")):
        updates["consolidation_weight"] = 10.0
    if any(word in text for word in ("cheap", "cheapest", "cost", "economic", "economical")):
        updates["cost_weight"] = 1.0
    if "external provider" in text or "3pl" in text or "third party" in text:
        updates["allow_external_providers"] = True
    return policy.model_copy(update=updates).model_dump()


def _validation_error(message: str, exc: ValidationError) -> str:
    """Return compact, actionable tool diagnostics instead of a Pydantic traceback."""
    fields = [".".join(str(part) for part in error["loc"]) for error in exc.errors()[:10]]
    return json.dumps(
        {
            "errorCode": "ValidationError",
            "errorMessage": message,
            "invalidFields": fields,
            "action": "Provide complete domain objects; do not use path summaries or null transport-leg fields.",
        }
    )


def optimize_portfolio_json(
    candidate_paths_json: str,
    transport_options_json: str,
    policy_json: str = "{}",
    consolidation_opportunities_json: str = "[]",
) -> str:
    """Optimize a portfolio from complete deterministic CandidatePath/TransportOption JSON."""
    try:
        path_data = json.loads(candidate_paths_json)
        option_data = json.loads(transport_options_json)
        policy_data = json.loads(policy_json)
        opportunity_data = json.loads(consolidation_opportunities_json)
        paths = tuple(CandidatePath.model_validate(item) for item in path_data)
        options = {item["id"]: TransportOption.model_validate(item) for item in option_data}
        policy = OptimizationPolicy.model_validate(policy_data)
        from routemind.consolidation.models import ConsolidationOpportunity

        opportunities = tuple(ConsolidationOpportunity.model_validate(item) for item in opportunity_data)
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps({"errorCode": "InvalidJSON", "errorMessage": str(exc)})
    except ValidationError as exc:
        return _validation_error(
            "Candidate paths must contain complete shipment_id, transport legs, timing, cost, currency, "
            "reliability, modes, providers, capacity utilization, and deadline feasibility fields.",
            exc,
        )

    result = optimize_portfolio(paths, options, policy, opportunities)
    return result.model_dump_json()


def discover_and_optimize_portfolio(
    shipments_json: str,
    transport_options_json: str,
    policy_json: str = "{}",
    consolidation_opportunities_json: str = "[]",
) -> str:
    """Discover candidate paths deterministically, then optimize the shipment portfolio."""
    try:
        shipment_data = json.loads(shipments_json)
        option_data = json.loads(transport_options_json)
        policy_data = json.loads(policy_json)
        opportunity_data = json.loads(consolidation_opportunities_json)
        shipments = tuple(Shipment.model_validate(item) for item in shipment_data)
        options = tuple(TransportOption.model_validate(item) for item in option_data)
        policy = OptimizationPolicy.model_validate(policy_data)
        from routemind.consolidation.models import ConsolidationOpportunity

        opportunities = tuple(ConsolidationOpportunity.model_validate(item) for item in opportunity_data)
    except (json.JSONDecodeError, KeyError) as exc:
        return json.dumps({"errorCode": "InvalidJSON", "errorMessage": str(exc)})
    except ValidationError as exc:
        return _validation_error(
            "Shipments and transport options must be complete domain objects; missing logistics facts cannot be guessed.",
            exc,
        )

    engine = PathSearchEngine(list(options))
    paths: list[CandidatePath] = []
    diagnostics: dict[str, Any] = {}
    for shipment in shipments:
        discovered = engine.discover_paths(shipment)
        paths.extend(discovered)
        diagnostics[shipment.id] = {
            "candidate_count": len(discovered),
            "search_diagnostics": engine.last_diagnostics.model_dump(),
        }

    if not paths:
        return json.dumps(
            {
                "feasible": False,
                "warnings": [
                    "No feasible candidate paths were discovered for the supplied shipment portfolio."
                ],
                "search_diagnostics": diagnostics,
            }
        )

    result = optimize_portfolio(paths, {option.id: option for option in options}, policy, opportunities)
    payload = json.loads(result.model_dump_json())
    payload["search_diagnostics"] = diagnostics
    return json.dumps(payload)


def validate_optimization_result(candidate_paths_json: str, result_json: str) -> str:
    """Validate that an optimization result selects known candidate path structures."""
    path_data = json.loads(candidate_paths_json)
    result_data = json.loads(result_json)
    try:
        paths = tuple(CandidatePath.model_validate(item) for item in path_data)
        result = OptimizationResult.model_validate(result_data)
    except ValidationError as exc:
        return _validation_error("Validation inputs are not complete RouteMind domain objects.", exc)
    known = {(path.shipment_id, path.option_ids, path.currency) for path in paths if path.deadline_feasible}
    seen: set[str] = set()
    errors: list[str] = []
    for plan in result.plans:
        if plan.shipment_id in seen:
            errors.append(f"Shipment {plan.shipment_id} appears more than once.")
        seen.add(plan.shipment_id)
        key = (plan.shipment_id, tuple(leg.option_id for leg in plan.legs), plan.currency)
        if key not in known:
            errors.append(f"Plan for {plan.shipment_id} does not match a known candidate path.")
    return json.dumps({"valid": not errors, "errors": errors, "shipment_count": len(seen)})


def summarize_result(result_json: str) -> str:
    """Produce a concise factual summary from a deterministic optimization result."""
    result = OptimizationResult.model_validate_json(result_json)
    return json.dumps(
        {
            "feasible": result.feasible,
            "objective_value": result.objective_value,
            "warnings": result.warnings,
            "metrics": result.metrics,
            "shipments": [plan.shipment_id for plan in result.plans],
        }
    )


def explain_optimization_result(result_json: str) -> str:
    """Explain only facts present in a deterministic optimization result."""
    result = OptimizationResult.model_validate_json(result_json)
    if not result.feasible:
        reason = "; ".join(result.warnings) if result.warnings else "The solver reported no feasible portfolio."
        return f"Infeasible portfolio: {reason}"
    metrics = result.metrics
    parts = [
        f"Selected {int(metrics.get('shipment_count', len(result.plans)))} shipment plan(s).",
        f"Total modeled cost: {metrics.get('total_cost', 0):g}.",
    ]
    if metrics.get("consolidation_savings", 0):
        parts.append(f"Consolidation savings represented in the result: {metrics['consolidation_savings']:g}.")
    if metrics.get("total_transit_seconds") is not None:
        parts.append(f"Aggregate elapsed transit/waiting time: {metrics['total_transit_seconds']:g} seconds.")
    if result.warnings:
        parts.append("Warnings: " + "; ".join(result.warnings))
    return " ".join(parts)
