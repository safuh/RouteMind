# RouteMind Architecture

## Boundary

The project separates four concerns:

1. **Domain** — logistics concepts and invariants.
2. **Optimization** — deterministic algorithms and mathematical solvers.
3. **Agent orchestration** — Google ADK agents and typed tools.
4. **Delivery platform** — API, persistence, integrations and UI, added later.

The first three layers must not be collapsed into a single LLM prompt.

## Transportation abstraction

`TransportOption` represents a capacity/service offering. It can be a company vehicle, a public bus, rail service, airline, shipping line, courier or 3PL provider.

This permits a single optimization model to represent:

- last-mile delivery;
- city-to-city transportation;
- regional multimodal transport;
- international freight;
- hybrid company-owned and outsourced logistics.

## Optimization boundary

The agent may interpret a request such as:

> Minimize cost while ensuring priority shipments arrive within 24 hours and external carriers may be used.

It should convert this into a typed `OptimizationPolicy`. The deterministic optimization layer then evaluates feasible transportation plans.

The agent must not fabricate:

- capacities;
- prices;
- schedules;
- route distances;
- ETAs;
- feasibility.

Those values must originate from domain data, integrations or deterministic calculations.

## Shared transportation

A future graph layer will represent transportation segments as reusable edges. Multiple shipments may allocate capacity on the same edge when their origin, destination, timing and cargo constraints permit consolidation.

This enables the platform to optimize network-level movement rather than independently optimizing each shipment.

## Planned production boundary

```text
Google ADK
     │
     ▼
Agent / Tool Layer
     │
     ▼
Optimization Application Layer
     │
     ├── Path discovery
     ├── Consolidation
     ├── Capacity allocation
     ├── Scheduling
     └── Solver
     │
     ▼
Domain Model
     │
     ▼
Integrations / Data Sources
```

FastAPI, PostgreSQL, Redis, authentication, observability and cloud deployment will be added only after the optimization core has measurable benchmark performance.
