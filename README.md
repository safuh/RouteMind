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
- Minimum carbon footprint
- Balanced cost / speed / reliability
- Capacity preservation

---

# Deterministic Optimization

M5 uses Google OR-Tools CP-SAT for portfolio-level assignment. Candidate paths are decision alternatives; the solver selects exactly one path per shipment while enforcing capacity on exact scheduled transport instances. Consolidation opportunities can contribute savings only when the selected paths actually contain the shared scheduled segments. Provider availability is enforced before solving.

The optimizer is independent of Google ADK. This keeps the LLM out of feasibility, capacity, pricing and optimization decisions.

# Local Google ADK Agent

The M6 agent is in `app/`. It is an orchestration and explanation layer over the deterministic engines.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[agents,dev]'
adk web
```

Then open the local ADK playground and select the `app` agent. Configure the Gemini/Google credentials required by your installed ADK version before making model-backed requests.

The agent exposes structured tools for:

- business-objective extraction
- deterministic portfolio optimization
- result validation
- factual result summarization
- grounded infeasibility/trade-off explanation

It must not invent missing logistics data. Candidate paths, schedules, capacities, prices and provider facts must come from structured inputs.

See `app/README.md` for the local workflow.

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

The project will progressively incorporate multimodal path optimization, shipment consolidation, scheduling, assignment optimization, multi-objective optimization and dynamic re-optimization.

Google OR-Tools is the initial optimization technology; the optimization layer remains independent of Google ADK.
