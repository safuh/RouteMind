# RouteMind ADK Agent

The `app/` package is the Google ADK orchestration layer. It delegates all logistics decisions to deterministic RouteMind tools.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[agents,dev]'
```

For Gemini API-key development, configure the Google/Gemini credentials supported by your installed ADK version.

## Run the local playground

From the repository root:

```bash
adk web
```

Then open the local ADK playground and select the `app` agent.

A good first request is:

> I need the cheapest feasible portfolio. I will provide complete shipment and transport-option JSON. Do not invent missing logistics facts.

### Important input boundary

Do **not** ask the agent to construct `CandidatePath` JSON from shorthand route descriptions. A `CandidatePath` is a low-level deterministic object and requires complete transport legs, including origin, destination, departure, arrival and path metrics.

For user-facing workflows, provide complete `Shipment` and `TransportOption` domain objects to `discover_and_optimize_portfolio()`. The deterministic `PathSearchEngine` then derives candidate legs and metrics before calling the CP-SAT optimizer.

`optimize_portfolio_json()` remains available for callers that already have complete `CandidatePath` objects.

If incomplete path JSON is supplied, the tool returns an actionable validation response rather than exposing a Pydantic traceback.

## Tool boundary

- `extract_optimization_policy()` normalizes explicit business objectives.
- `discover_and_optimize_portfolio()` deterministically discovers candidate paths and optimizes the complete shipment portfolio.
- `optimize_portfolio_json()` optimizes already-discovered complete candidate paths.
- `validate_optimization_result()` checks that returned plans correspond to known candidate paths.
- `summarize_result()` formats factual solver output for explanation.
- `explain_optimization_result()` explains only deterministic solver facts.

Synthetic benchmark data remains synthetic and is not presented as live provider data.
