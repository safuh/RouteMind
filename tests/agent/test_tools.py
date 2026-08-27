import json

from app.tools import extract_optimization_policy, summarize_result, validate_optimization_result


def test_objective_extraction_is_conservative_and_structured():
    policy = extract_optimization_policy("Choose the cheapest reliable option with low carbon emissions")
    assert policy["cost_weight"] == 1.0
    assert policy["reliability_weight"] == 100.0
    assert policy["carbon_weight"] == 10.0


def test_result_summary_preserves_deterministic_facts():
    result = {
        "plans": [], "objective_value": 0.0, "feasible": False,
        "warnings": ["No candidate path"], "metrics": {"shipment_count": 0},
    }
    summary = json.loads(summarize_result(json.dumps(result)))
    assert summary["feasible"] is False
    assert summary["warnings"] == ["No candidate path"]


def test_result_validation_rejects_unknown_plan_path():
    path = {
        "shipment_id": "A",
        "legs": [{
            "option_id": "BUS-1", "origin": {"id": "nbo", "name": "Nairobi"},
            "destination": {"id": "nku", "name": "Nakuru"},
            "departure_at": "2026-08-27T08:00:00Z", "arrival_at": "2026-08-27T11:00:00Z",
            "allocated_weight_kg": 10, "allocated_volume_m3": .008,
        }],
        "total_cost": "50", "currency": "KES", "transit_seconds": 10800,
        "waiting_seconds": 0, "number_of_transfers": 0, "reliability": .95,
        "modes": ["bus"], "providers": ["P"], "capacity_utilization": .1,
        "deadline_feasible": True,
    }
    result = {
        "plans": [{
            "shipment_id": "A", "legs": [{
                "option_id": "BUS-UNKNOWN", "origin": {"id": "nbo", "name": "Nairobi"},
                "destination": {"id": "nku", "name": "Nakuru"},
                "departure_at": "2026-08-27T08:00:00Z", "arrival_at": "2026-08-27T11:00:00Z",
                "allocated_weight_kg": 10, "allocated_volume_m3": .008,
            }], "total_cost": "50", "currency": "KES", "total_transit_seconds": 10800,
            "reliability": .95,
        }],
        "objective_value": 50, "feasible": True, "warnings": [], "metrics": {},
    }
    validation = json.loads(validate_optimization_result(json.dumps([path]), json.dumps(result)))
    assert validation["valid"] is False
    assert validation["errors"]
