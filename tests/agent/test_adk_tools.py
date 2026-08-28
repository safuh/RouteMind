import json

from app.adk_tools import _parse_tool_json


def test_adk_adapter_returns_native_object():
    result = _parse_tool_json('{"feasible": true, "plans": []}')
    assert result == {"feasible": True, "plans": []}


def test_adk_adapter_reports_truncated_json_without_raising():
    result = _parse_tool_json('{"plans": [{"shipment_id": "S1"}')
    assert result["errorCode"] == "ToolSerializationError"
    assert "invalid JSON" in result["errorMessage"]


def test_adk_adapter_rejects_non_object_json():
    result = _parse_tool_json(json.dumps([{"shipment_id": "S1"}]))
    assert result["errorCode"] == "ToolSerializationError"
