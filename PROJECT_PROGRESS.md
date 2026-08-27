# RouteMind — Project Progress Tracker

> Living engineering tracker. Do not mark a component complete until implementation, automated tests, documentation, and validation evidence exist.

**Current phase:** Milestone 4 — Shipment Consolidation

**Overall status:** ~52% — M3 implementation remains validation-pending; M4 now has deterministic shared-segment detection, consolidation feasibility, capacity aggregation, cargo checks, and pricing economics.

| Milestone | Area | Status |
|---|---|---:|
| M0 | Product & architecture | 🟢 |
| M1 | Multimodal domain + synthetic data | 🟢 |
| M2 | Transportation graph | 🟢 |
| M3 | Candidate path discovery | 🟡 |
| M4 | Shipment consolidation | 🟡 |
| M5 | Deterministic optimization | ⬜ |
| M6 | Google ADK agent layer | ⬜ |
| M7 | Dynamic re-optimization | ⬜ |
| M8 | Predictive logistics intelligence | ⬜ |
| M9 | Production platform | ⬜ |

# M3 — Candidate Path Discovery
**Status: 🟡 Implementation complete; validation evidence pending**

## Implemented
- [x] Direct, multi-hop and multimodal path discovery
- [x] Time-dependent schedules and shipment readiness
- [x] Deadline-aware filtering
- [x] Weight/volume and schedule-specific capacity filtering
- [x] Availability, reliability and transfer constraints
- [x] Cargo compatibility and provider/mode policies
- [x] Cycle/reuse protection
- [x] Fixed, quoted, per-kg and per-volume pricing
- [x] Distance-aware per-km pricing
- [x] Distance-aware per-kg-km pricing
- [x] Explicit rejection when distance-based pricing lacks distance data
- [x] Optional transport emissions propagation
- [x] Optimization-grade CandidatePath abstraction and invariants
- [x] Transit/waiting/transfer/reliability/capacity/emissions metrics
- [x] Pareto dominance filtering
- [x] Bounded search expansion budget
- [x] Structured rejection diagnostics
- [x] Search counters
- [x] Deterministic benchmark scenario harness
- [x] Automated economics and diagnostics tests
- [x] Path package documentation

## Remaining validation
- [ ] Execute full test suite in CI
- [ ] Execute benchmark suite and capture runtime evidence
- [ ] Produce search performance benchmark report
- [ ] Add provider-specific transfer compatibility semantics

### M3 exit criteria
- [x] A shipment can receive multiple feasible strategies.
- [x] Direct and multimodal services are considered.
- [x] Time, deadline and capacity constraints are respected.
- [x] Candidates include core decision metrics and Pareto filtering.
- [x] Rejected alternatives expose machine-readable reasons.
- [x] Distance-based economics are deterministic when distance is supplied.
- [ ] Benchmark/performance evidence is executed and recorded.

# M4 — Shipment Consolidation
**Status: 🟡 First brick implemented; validation pending**

## Implemented in first brick
- [x] Concrete scheduled shared-segment identity
- [x] Shared-segment detection across candidate paths
- [x] Different destinations can share an upstream segment
- [x] Shipment-group weight aggregation
- [x] Shipment-group volume aggregation
- [x] Shipment-group package-count aggregation
- [x] Schedule-specific remaining capacity checks
- [x] Existing domain cargo compatibility reused
- [x] Structured consolidation rejection diagnostics
- [x] Fixed/quoted consolidation economics
- [x] Additive variable-pricing economics
- [x] Three-shipment aggregation without pairwise-only assumptions
- [x] Consolidation domain documentation
- [x] Deterministic consolidation tests for core scenarios

## Remaining
- [ ] Execute consolidation tests in CI/runtime environment
- [ ] Capacity reservation across competing consolidation opportunities
- [ ] Shipment grouping/candidate subset generation
- [ ] Explicit end-to-end time-window compatibility model
- [ ] Transfer handling allocation for shared/unshared downstream legs
- [ ] Hub-and-spoke opportunity generation
- [ ] Consolidation-vs-direct portfolio comparison
- [ ] Feed feasible consolidation combinations into M5 optimization

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
| 2026-08-27 | Candidate path model, multimodal search, constraints, Pareto filtering and diagnostics established |
| 2026-08-27 | Distance-aware pricing and optional emissions metrics added |
| 2026-08-27 | Deterministic economics tests and benchmark harness updated |
| 2026-08-27 | M4 consolidation domain models and scheduled shared-segment detection added |
| 2026-08-27 | Consolidation feasibility, capacity aggregation, cargo checks and deterministic economics added |
| 2026-08-27 | Core M4 consolidation scenarios documented and covered by automated tests |
