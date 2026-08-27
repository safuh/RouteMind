# RouteMind — Project Progress Tracker

> Living engineering tracker. Do not mark a component complete until implementation, tests, documentation, and validation evidence exist in the repository.

**Current phase:** Milestone 3 — Candidate Path Discovery

**Overall status:** ~45% — M3 candidate discovery is feature-complete except for benchmark/performance evidence and distance-aware economics.

## Status Legend
- ⬜ Not started
- 🟡 In progress
- 🟢 Complete
- 🔴 Blocked
- 🔵 Deferred / future phase

### Completion standard
A milestone is complete only when implementation, automated tests, representative scenarios, documentation, and quality checks are present.

## Executive Progress
| Milestone | Area | Status |
|---|---|---:|
| M0 | Product & architecture | 🟢 |
| M1 | Multimodal domain + synthetic data | 🟢 |
| M2 | Transportation graph | 🟢 |
| M3 | Candidate path discovery | 🟡 |
| M4 | Shipment consolidation | ⬜ |
| M5 | Deterministic optimization | ⬜ |
| M6 | Google ADK agent layer | ⬜ |
| M7 | Dynamic re-optimization | ⬜ |
| M8 | Predictive logistics intelligence | ⬜ |
| M9 | Production platform | ⬜ |

# M3 — Candidate Path Discovery
**Status: 🟡 In progress**

## Implemented
- [x] Direct, multi-hop and multimodal path discovery
- [x] Time-dependent departure and deadline checks
- [x] Weight/volume and schedule-specific remaining-capacity filtering
- [x] Availability, reliability and transfer constraints
- [x] Cargo compatibility and provider/mode policy filtering
- [x] Cycle/reuse protection
- [x] Shipment-evaluable fixed, quoted, per-kg and per-volume pricing
- [x] Explicit rejection of distance-based pricing until distance is modeled
- [x] Optimization-grade `CandidatePath` abstraction and invariants
- [x] Transit/waiting/transfer/reliability/capacity metrics
- [x] Pareto dominance filtering with meaningful trade-off preservation
- [x] Bounded search expansion budget
- [x] Structured rejection diagnostics
- [x] Search counters and diagnostic aggregation
- [x] Automated tests and path documentation

## Remaining
- [ ] Distance-aware pricing and emissions metrics
- [ ] Provider-specific transfer compatibility semantics
- [ ] Benchmark against baseline search
- [ ] Search performance instrumentation/benchmark report

### M3 exit criteria
- [x] A shipment can receive multiple feasible strategies.
- [x] Direct and multimodal services are considered.
- [x] Time, deadline and capacity constraints are respected.
- [x] Candidates include core decision metrics and Pareto filtering.
- [x] Rejected alternatives expose machine-readable reasons.
- [ ] Benchmark/performance evidence is complete.

# M4 — Shipment Consolidation
**Status: ⬜ Not started**
- [ ] Same-destination grouping
- [ ] Common-origin grouping
- [ ] Shared-segment detection
- [ ] Time-window compatibility
- [ ] Cargo compatibility
- [ ] Weight/volume aggregation
- [ ] Capacity reservation
- [ ] Consolidation economics
- [ ] Hub-and-spoke opportunities
- [ ] Consolidation vs direct comparison

# M5 — Deterministic Optimization Engine
**Status: ⬜ Not started**
- [ ] Baselines
- [ ] OR-Tools integration
- [ ] Shipment assignment
- [ ] Capacity and schedule constraints
- [ ] Consolidation decisions
- [ ] Provider availability
- [ ] Multi-objective optimization
- [ ] Objective/constraint reports

# M6 — Google ADK Agent Layer
**Status: ⬜ Not started**
- [ ] Logistics Manager Agent
- [ ] Structured logistics tools
- [ ] Optimization and validation tools
- [ ] Natural-language objective extraction
- [ ] Infeasibility and trade-off explanation
- [ ] Agent regression and grounding tests

# M7 — Dynamic Re-optimization
**Status: ⬜ Not started**
- [ ] Disruption/event model
- [ ] Impact analysis
- [ ] Alternative discovery
- [ ] Incremental optimization
- [ ] Recovery validation
- [ ] Decision audit trail

# M8 — Predictive Logistics Intelligence
**Status: ⬜ Not started**
- [ ] ETA/delay prediction
- [ ] Reliability prediction
- [ ] Demand/capacity forecasting
- [ ] Price/congestion/failure prediction
- [ ] Model monitoring and data lineage

# M9 — Production Platform
**Status: ⬜ Not started**
- [ ] FastAPI
- [ ] PostgreSQL / SQLAlchemy / Alembic
- [ ] Async processing
- [ ] Authentication/RBAC/tenant isolation
- [ ] Docker/CI/CD
- [ ] Observability
- [ ] Google Cloud deployment

# Benchmark & Research Track
- [ ] City, regional, cross-border and intercontinental scenarios
- [ ] Fleet-only and no-owned-fleet scenarios
- [ ] Public-transport-heavy scenario
- [ ] High-consolidation scenario
- [ ] Tight-deadline scenario
- [ ] Capacity-constrained scenario
- [ ] Disruption scenario
- [ ] Cost/time/on-time/utilization/transfer/consolidation/emissions/runtime metrics
- [ ] Optimality-gap measurement

# Change Log
| Date | Change |
|---|---|
| 2026-08-27 | Optimization-grade CandidatePath model, Pareto filtering, bounded search, transfer/cargo/policy constraints and tests established |
| 2026-08-27 | Structured path rejection diagnostics and auditable search counters added |
