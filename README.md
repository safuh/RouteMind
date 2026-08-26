# RouteMind

> **Agentic multimodal logistics optimization and transportation decision engine.**

RouteMind determines how goods should move from origin to destination across a heterogeneous transportation network. It does not assume that a business owns vehicles. Instead, it discovers and evaluates feasible transportation options—including motorcycles, vans, trucks, buses, rail, air, sea, courier networks, third-party logistics providers, and company-owned capacity—and recommends an optimal or Pareto-efficient logistics plan.

The project combines **Google ADK agentic orchestration**, **operations research**, **multimodal graph optimization**, **shipment consolidation**, **capacity allocation**, **scheduling**, and eventually **predictive logistics intelligence**.

---

## Why RouteMind?

Most delivery software starts from a fleet-centric assumption:

> Orders → company vehicles → routes.

That model is too narrow for modern commerce.

A marketplace such as an e-commerce platform may own no delivery vehicles. A retailer may use buses or trains for regional movement. A logistics company may combine trucks, rail, air and sea. A local merchant may use motorcycles. An international shipper may use a chain of third-party carriers.

RouteMind therefore treats **transportation itself as the optimization resource**.

Given a shipment, the system asks:

> **What feasible ways exist to move this shipment from origin to destination, and which strategy best satisfies the business's objectives and constraints?**

The answer can be a direct journey or a multimodal journey involving consolidation, hubs and multiple providers.

---

## Product Vision

RouteMind is intended to become a general-purpose **logistics decision engine** for:

- E-commerce marketplaces
- Retailers and wholesalers
- Courier and parcel companies
- 3PL / 4PL providers
- Manufacturers and distributors
- Freight forwarders
- Import/export businesses
- Postal networks
- Food and agricultural distribution
- Pharmaceutical distribution
- Companies with or without their own fleet

The system is designed to support local, regional, national and intercontinental transportation.

### Core abstraction

A vehicle is only one type of transportation resource.

```text
Transport Resource
├── Motorcycle
├── Van
├── Truck
├── Bus
├── Rail
├── Air
├── Sea
├── Courier
├── 3PL
├── Company Fleet
└── Other scheduled or on-demand capacity
```

Each resource is modeled through a common interface containing characteristics such as:

- Origin / destination coverage
- Capacity
- Weight limits
- Volume limits
- Dimensions
- Schedule
- Transit time
- Price model
- Reliability
- Availability
- Handling constraints
- Service restrictions

---

# System Concept

```text
                           BUSINESS REQUEST
                                  │
                                  ▼
                         Google ADK Agent Layer
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
             Shipment Intent  Transport Data  Business Policy
                   │              │              │
                   └──────────────┼──────────────┘
                                  ▼
                       TRANSPORT DISCOVERY
                                  │
                                  ▼
                    MULTIMODAL TRANSPORT GRAPH
                                  │
                                  ▼
                       CANDIDATE PATH SEARCH
                                  │
                                  ▼
                     SHIPMENT CONSOLIDATION
                                  │
                                  ▼
                       CAPACITY ALLOCATION
                                  │
                                  ▼
                       SCHEDULE OPTIMIZATION
                                  │
                                  ▼
                    MULTI-OBJECTIVE OPTIMIZER
                                  │
                                  ▼
                       SOLUTION VALIDATION
                                  │
                                  ▼
                    BUSINESS RECOMMENDATION
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
               Cheapest        Fastest        Balanced
                  │               │               │
                  └───────────────┼───────────────┘
                                  ▼
                           TRANSPORT PLAN
```

The central engineering principle is:

> **AI decides what needs to be analyzed and how to communicate the result; deterministic optimization determines what is feasible and mathematically preferable.**

The LLM is therefore not trusted to invent routes, costs, capacities or constraints.

---

# Key Capabilities

## 1. Multimodal Transportation Discovery

For an order from Nairobi to Kisumu, RouteMind may evaluate:

```text
Direct motorcycle
Direct van
Direct truck
Public bus
Rail
Van → rail → motorcycle
Truck → hub → motorcycle
3PL courier
```

The candidate set is generated from actual transportation resources available to the system.

## 2. Shared Route / Segment Optimization

Multiple products can share the same transportation segment.

```text
                    Nairobi
                       │
                  shared truck
                       │
                     Nakuru
                   /    │     \
                  /     │      \
             Kisumu  Kakamega  Eldoret
```

Instead of optimizing every order independently, RouteMind can consolidate compatible shipments and measure utilization of each shared segment.

## 3. Multimodal Journeys

A shipment may use multiple transport legs:

```text
China
  ↓ truck
Port
  ↓ ship
Mombasa
  ↓ rail
Nairobi
  ↓ motorcycle
Customer
```

## 4. Capacity-aware Optimization

Every transport resource can impose:

- Weight limits
- Volume limits
- Dimensional restrictions
- Item-count limits
- Cargo compatibility rules
- Remaining capacity

## 5. Schedule-aware Optimization

Transport options may have fixed schedules:

```text
Bus:    08:00 → 14:30
Train:  18:00 → 04:00
Flight: 21:30 → 23:00
```

The optimizer must account for shipment readiness, transfer time and deadlines.

## 6. Business Policies

Businesses can optimize for different objectives:

- Minimum cost
- Minimum delivery time
- Maximum reliability
- Maximum internal fleet utilization
- Minimum carbon footprint
- Balanced cost / speed / reliability
- Premium delivery
- Capacity preservation

## 7. Dynamic Re-optimization

Eventually, events such as these will trigger re-planning:

- Vehicle breakdown
- Bus cancellation
- Train delay
- Flight cancellation
- Capacity reduction
- New urgent order
- Road closure
- Provider price change
- Unexpected demand

---

# Optimization Model

RouteMind is fundamentally a **multimodal, capacitated, time-dependent network optimization problem**.

A simplified objective is:

\[
\min\left(
C_{transport} + C_{handling} + C_{storage} + C_{delay} + C_{risk} + C_{carbon}
\right)
\]

subject to constraints such as:

\[
weight \le capacity
\]

\[
volume \le capacity
\]

\[
arrival \le deadline
\]

\[
shipment\ compatibility = true
\]

\[
transport\ availability = true
\]

The project will progressively incorporate:

- Shortest-path optimization
- Shipment consolidation
- Capacitated Vehicle Routing Problem (CVRP)
- Vehicle Routing Problem with Time Windows (VRPTW)
- Multimodal path optimization
- Scheduling
- Assignment optimization
- Bin-packing / loading constraints
- Multi-objective optimization
- Dynamic re-optimization

Google OR-Tools is the initial optimization technology; the optimization layer remains independent of Google ADK.

---

# Agent Architecture

The initial Google ADK implementation will deliberately remain small.

```text
                         Root / Logistics Manager
                                  Agent
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
          Shipment Analysis   Transport Discovery   Policy Analysis
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    ▼
                         Multimodal Optimizer
                                    │
                                    ▼
                           Solution Validator
                                    │
                                    ▼
                        Recommendation / Explanation
```

Agents will use typed tools rather than directly manipulating optimization internals.

Initial tools are expected to include:

```text
get_shipments()
discover_transport_options()
build_transport_graph()
find_candidate_paths()
find_shared_segments()
consolidate_shipments()
allocate_capacity()
optimize_transport_plan()
validate_solution()
calculate_plan_metrics()
```

---

# Initial Domain Model

The core domain will evolve around these concepts:

```text
Shipment
Package
Product
Origin
Destination
Hub
TransportProvider
TransportOption
TransportLeg
TransportSchedule
TransportCapacity
TransportPrice
TransportConstraint
TransportPlan
OptimizationPolicy
OptimizationResult
RouteSegment
ConsolidationGroup
```

A transport option is intentionally broader than a vehicle:

```python
TransportOption(
    mode="bus",
    provider="Provider X",
    origin="Nairobi",
    destination="Kisumu",
    departure_time="08:00",
    arrival_time="14:30",
    max_weight_kg=100,
    price_model="per_kg",
    reliability=0.94,
)
```

A multimodal plan can then contain several legs:

```python
TransportPlan(
    shipment_id="S123",
    legs=[
        TransportLeg(...),
        TransportLeg(...),
        TransportLeg(...),
    ],
)
```

---

# Development Roadmap

## Milestone 0 — Foundation and Specification

**Status: In progress**

Deliverables:

- Product definition
- Architecture
- Domain model
- Optimization formulation
- Repository structure
- Development standards
- Evaluation strategy

## Milestone 1 — Multimodal Domain Core

- Pydantic domain models
- Shipment models
- Transport provider models
- Transport options
- Schedules
- Capacity models
- Pricing models
- Constraints
- Synthetic dataset generator

## Milestone 2 — Transportation Graph

- Geographic nodes
- Transport edges
- Road/service segments
- Scheduled transport edges
- Hub representation
- Cost/time/reliability attributes
- Multimodal graph construction

## Milestone 3 — Path Discovery

- Direct paths
- Multileg paths
- Multimodal paths
- Feasibility filtering
- Transfer constraints
- Time-dependent paths

## Milestone 4 — Consolidation Engine

- Shared destination detection
- Shared segment detection
- Compatibility analysis
- Capacity aggregation
- Consolidation savings
- Hub-and-spoke opportunities

## Milestone 5 — Optimization Engine

- Baseline algorithms
- OR-Tools integration
- Capacity constraints
- Time windows
- Scheduling
- Cost optimization
- Multi-objective optimization

## Milestone 6 — Google ADK Integration

- Root agent
- Shipment analysis agent/tooling
- Transport discovery tooling
- Optimization tooling
- Validation tooling
- Structured outputs
- Agent evaluation

## Milestone 7 — Dynamic Optimization

- Event model
- Delay handling
- Cancellation handling
- Capacity changes
- New-order insertion
- Re-optimization

## Milestone 8 — Predictive Intelligence

- ETA prediction
- Demand forecasting
- Carrier reliability prediction
- Capacity forecasting
- Delay prediction
- Cost forecasting

## Milestone 9 — Production Platform

- FastAPI API
- PostgreSQL
- Redis
- Authentication / RBAC
- Multi-tenancy
- Observability
- Audit logging
- Docker
- CI/CD
- Cloud deployment

---

# Evaluation Strategy

RouteMind will not be evaluated by whether an LLM produces a convincing explanation.

It will be evaluated using measurable logistics outcomes.

### Baselines

1. Independent direct routing
2. Nearest-neighbor routing
3. Unconsolidated shipment planning
4. Deterministic optimization
5. Agent + deterministic optimization

### Metrics

| Category | Metrics |
|---|---|
| Cost | Total transport cost, cost/shipment |
| Distance | Total distance, empty distance |
| Time | Transit time, lateness |
| Service | On-time %, deadline violations |
| Capacity | Weight utilization, volume utilization |
| Consolidation | Shared segments, consolidated shipments |
| Fleet | Vehicles/resources used |
| Reliability | Expected and realized failures |
| Sustainability | Estimated emissions |
| Compute | Optimization runtime |
| Agent | Tool accuracy, constraint adherence |

Every major optimizer improvement should have benchmark scenarios demonstrating whether it actually improves the solution.

---

# Example Scenario

Suppose a marketplace has five shipments:

```text
A → Kisumu   8 kg
B → Kisumu   5 kg
C → Kakamega 12 kg
D → Eldoret  10 kg
E → Eldoret  7 kg
```

Available transport includes:

```text
Nairobi → Nakuru     Truck
Nairobi → Kisumu     Bus
Nakuru → Kisumu      Van
Nakuru → Eldoret     Truck
Kisumu → Customer    Motorcycle
Eldoret → Customer   Motorcycle
```

RouteMind should not independently select transportation for A–E.

It should identify opportunities such as:

```text
Nairobi
   │
   │ shared truck
   ▼
Nakuru
   ├──────────────► Kisumu ──► motorcycles
   │
   └──────────────► Eldoret ──► motorcycles
```

and compare that against direct and alternative multimodal plans.

The result should explain **why** a plan is preferred:

```text
Recommended strategy:

- Consolidate A+B for the Kisumu flow.
- Consolidate D+E for the Eldoret flow.
- Use the shared Nairobi→Nakuru truck segment.
- Use local motorcycles for final-mile delivery.

Expected trade-off:
- Lower transport cost
- Higher shared-segment utilization
- Additional transfer handling
- Longer transit than premium direct transport
```

The numerical result must come from the optimizer, not from the LLM.

---

# Technology Direction

### Core

- Python 3.12+
- Pydantic
- Google ADK
- Google Gemini models through ADK
- Google OR-Tools
- NetworkX initially where appropriate

### Backend — later milestone

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis

### Testing

- pytest
- property-based testing where useful
- optimization benchmark scenarios
- agent evaluation

### Production

- Docker
- GitHub Actions
- Google Cloud
- Cloud Run
- Cloud SQL
- observability / tracing

The architecture will keep the **optimization core independent from the API and agent framework**.

---

# Design Principles

1. **Transport, not vehicles, is the core abstraction.**
2. **Optimization must be deterministic and measurable.**
3. **LLMs orchestrate; solvers enforce mathematical constraints.**
4. **Multimodal journeys are first-class.**
5. **Shared transportation segments are explicitly modeled.**
6. **Consolidation is an optimization decision, not a preprocessing assumption.**
7. **A business does not need to own transportation capacity.**
8. **Policies and objectives must be configurable.**
9. **Every recommendation must be explainable through its underlying data and optimization result.**
10. **The model must scale from last-mile delivery to intercontinental freight.**
11. **Benchmark every major optimization change.**
12. **Do not use an LLM where a deterministic algorithm is more reliable.**

---

# Current Status

| Component | Status |
|---|---|
| Product definition | Complete |
| Multimodal architecture | Defined |
| Domain model | Initial specification |
| Optimization formulation | Initial specification |
| Repository | Active |
| Synthetic data | Planned |
| Transport graph | Planned |
| Path discovery | Planned |
| Consolidation | Planned |
| Optimizer | Planned |
| Google ADK agents | Planned |
| Dynamic optimization | Planned |
| Predictive ML | Planned |
| Production API | Planned |

---

# Portfolio Objective

RouteMind is deliberately designed as a substantial AI engineering and operations-research portfolio project rather than a chatbot demonstration.

It demonstrates:

- Agentic AI with Google ADK
- LLM tool orchestration
- Operations research
- Constraint optimization
- Graph algorithms
- Multimodal transportation modeling
- Scheduling
- Combinatorial optimization
- Machine learning
- Backend engineering
- Testing and evaluation
- Cloud deployment
- Production architecture

The intended progression is:

```text
Mathematical Model
       ↓
Optimization Core
       ↓
Synthetic Benchmarking
       ↓
Google ADK Agent Layer
       ↓
Dynamic Logistics Intelligence
       ↓
Production API / Platform
```

---

# License

TBD during the initial engineering phase.

---

## Project Status

**Active development — Milestone 0 / Foundation**

RouteMind is being developed incrementally. The repository intentionally prioritizes a correct, testable optimization model before building a user interface or production SaaS layer.
