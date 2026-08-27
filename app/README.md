# RouteMind ADK Agent

The `app/` package is the Google ADK orchestration layer. It delegates all logistics decisions to deterministic RouteMind tools.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[agents,dev]'
```

For Gemini API-key development, configure the Google/Gemini credentials supported by your installed ADK version. The current Google ADK documentation supports local playground execution and Gemini authentication. See the official ADK/Agents CLI documentation for current authentication options.

## Run the local playground

From the repository root:

```bash
adk web
```

Then open the local ADK playground and select the `app` agent.

A useful first request is:

> I need the cheapest feasible portfolio. I will provide candidate paths and transport options as structured data; do not invent missing logistics facts.

For deterministic optimization, the agent expects structured JSON inputs for candidate paths and transport options. It must not manufacture those inputs.

## Tool boundary

- `extract_optimization_policy()` normalizes explicit business objectives.
- `optimize_portfolio_json()` calls the deterministic CP-SAT optimizer.
- `validate_optimization_result()` checks that returned plans correspond to known candidate paths.
- `summarize_result()` formats factual solver output for explanation.

Synthetic benchmark data remains synthetic and is not presented as live provider data.
