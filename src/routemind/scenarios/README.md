# Synthetic Scenario Engine

RouteMind uses reproducible synthetic logistics data before connecting to live carrier, fleet, marketplace, or public-transport feeds.

The generator currently creates a small Kenya-inspired network containing Nairobi, Nakuru, Kisumu, Eldoret, Kakamega and Mombasa. The locations and services are **synthetic** and are not intended to represent real carrier schedules or prices.

## Example

```python
from routemind.scenarios.generator import generate_scenario

scenario = generate_scenario(seed=42, shipment_count=50)

print(len(scenario.locations))
print(len(scenario.transport_options))
print(len(scenario.shipments))
```

## Why synthetic data first?

It gives the optimization engine a controlled environment where we can:

- reproduce bugs;
- benchmark algorithms;
- change one constraint at a time;
- create known edge cases;
- compare optimization strategies fairly;
- avoid coupling the core engine to external APIs.

The next step is to transform these transport options into a **time-dependent multimodal graph**.
