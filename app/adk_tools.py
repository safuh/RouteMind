"""ADK-safe structured adapters around the deterministic RouteMind tools."""

from __future__ import annotations

import json
from typing import Any

from app.tools import (
    discover_and_optimize_portfolio,
    explain_optimization_result,
    optimize_portfolio_json,
    summarize_result,
)


def _parse_tool_json(raw: str) -> dict[str, Any]:
    """Convert a legacy JSON-string tool result into a native structured object."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "errorCode": "ToolSerializationError",
            "errorMessage": f"Deterministic tool returned invalid JSON: {exc.msg}",
        }
    if not isinstance(value, dict):
        return {
            "errorCode": "ToolSerializationError",
            "errorMessage": "Deterministic tool returned a non-object JSON value.",
        }
    return value


def discover_and_optimize_portfolio_structured(
    shipments_json: str,
    transport_options_json: str,
    policy_json: str = "{}",
    consolidation_opportunities_json: str = "[]",
) -> dict[str, Any]:
    """Discover feasible routes and optimize the portfolio, returning a native object."""
    return _parse_tool_json(
        discover_and_optimize_portfolio(
            shipments_json,
            transport_options_json,
            policy_json,
            consolidation_opportunities_json,
        )
    )


def optimize_portfolio_structured(
    candidate_paths_json: str,
    transport_options_json: str,
    policy_json: str = "{}",
    consolidation_opportunities_json: str = "[]",
) -> dict[str, Any]:
    """Optimize complete candidate paths, returning a native object to ADK."""
    return _parse_tool_json(
        optimize_portfolio_json(
            candidate_paths_json,
            transport_options_json,
            policy_json,
            consolidation_opportunities_json,
        )
    )


def summarize_result_structured(result_json: str) -> dict[str, Any]:
    """Summarize a deterministic result and return a native object to ADK."""
    return _parse_tool_json(summarize_result(result_json))


def explain_optimization_result_structured(result_json: str) -> dict[str, Any]:
    """Explain a deterministic result without inventing logistics facts."""
    try:
        return {"explanation": explain_optimization_result(result_json)}
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "errorCode": "InvalidOptimizationResult",
            "errorMessage": str(exc),
        }
