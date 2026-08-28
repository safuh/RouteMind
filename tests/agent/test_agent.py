from app.agent import root_agent


def test_agent_exposes_high_level_logistics_workflow_only():
    names = {
        getattr(tool, "name", None) or getattr(tool, "__name__", "")
        for tool in root_agent.tools
    }
    assert "discover_and_optimize_portfolio" in names
    assert "optimize_portfolio_json" not in names
