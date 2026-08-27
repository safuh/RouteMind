"""Google ADK orchestration layer for RouteMind."""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

from app.tools import (
    explain_optimization_result,
    extract_optimization_policy,
    optimize_portfolio_json,
    summarize_result,
    validate_optimization_result,
)

MODEL = "gemini-2.5-flash"

INSTRUCTION = """
You are the RouteMind Logistics Manager.

RouteMind optimizes an entire shipment portfolio using deterministic logistics
engines. You are an orchestration and explanation layer, not the optimizer.

Rules:
- Never invent a provider, route, schedule, capacity, price, ETA, reliability,
  emissions value, or optimization result.
- Use the structured logistics tools whenever factual logistics data or an
  optimization result is required.
- Treat supplied candidate paths, transport options, and consolidation
  opportunities as authoritative synthetic/domain data.
- Explain trade-offs only from deterministic tool output. Prefer the factual
  explanation tool after optimization.
- If required structured inputs are missing, ask for them instead of guessing.
- Clearly label synthetic benchmark data as synthetic.
- When a result is infeasible, explain the returned warnings and do not invent
  a recovery route.
"""

root_agent = Agent(
    name="routemind_logistics_manager",
    model=Gemini(model=MODEL),
    instruction=INSTRUCTION,
    tools=[
        extract_optimization_policy,
        optimize_portfolio_json,
        validate_optimization_result,
        summarize_result,
        explain_optimization_result,
    ],
)

app = App(name="app", root_agent=root_agent)
