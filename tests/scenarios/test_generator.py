from routemind.scenarios.generator import generate_scenario


def test_scenario_generation_is_reproducible():
    first = generate_scenario(seed=123, shipment_count=10)
    second = generate_scenario(seed=123, shipment_count=10)

    assert first.locations == second.locations
    assert first.transport_options == second.transport_options
    assert first.shipments == second.shipments


def test_scenario_contains_multimodal_transport():
    scenario = generate_scenario(seed=42, shipment_count=10)
    modes = {option.mode for option in scenario.transport_options}

    assert len(modes) >= 4
    assert any(option.mode.value == "motorcycle" for option in scenario.transport_options)
    assert any(option.mode.value == "rail" for option in scenario.transport_options)


def test_scenario_generates_requested_shipments():
    scenario = generate_scenario(seed=42, shipment_count=37)
    assert len(scenario.shipments) == 37
    assert all(shipment.weight_kg > 0 for shipment in scenario.shipments)
    assert all(shipment.volume_m3 > 0 for shipment in scenario.shipments)
