# RouteMind — Project Progress Tracker

> Living engineering tracker. Do not mark a component complete until implementation, automated tests, documentation, and validation evidence exist.

**Current phase:** Milestone 4 — Shipment Consolidation

**Overall status:** ~55% — M4 foundation is implemented; runtime validation and broader portfolio scenarios remain.

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
- [x] Stable tool/API serialization contract for validated candidates
- [x] Automated economics, diagnostics and contract tests
- [x] Path package documentation

## Remaining validation
- [ ] Execute full test suite in CI
- [ ] Execute benchmark suite and capture runtime evidence
- [ ] Produce search performance benchmark report
- [ ] Add provider-specific transfer compatibility semantics

# M4 — Shipment Consolidation
**Status: 🟡 Foundation implemented**

## Implemented
- [x] Concrete scheduled `SharedSegment` identity
- [x] Shared-segment detection across candidate paths
- [x] Distinguish same scheduled service from merely same geographic route
- [x] Aggregate shipment weight and volume
- [x] Schedule-specific remaining-capacity validation
- [x] Cargo restriction validation
- [x] Deadline compatibility validation
- [x] Service availability validation
- [x] Fixed/quoted consolidation economics
- [x] Usage-based consolidation economics
- [x] Deterministic rejection objects
- [x] Automated consolidation tests
- [x] Consolidation package documentation

## Remaining
- [ ] Common-origin/common-hub shipment grouping
- [ ] Different-destination shared-prefix detection scenarios
- [ ] Time-window compatibility across pickup readiness windows
- [ ] Explicit capacity reservation model
- [ ] Handling/storage/transfer economics at consolidation boundaries
- [ ] Consolidation savings vs independent candidate baselines across complete paths
- [ ] Multi-segment shared-chain detection
- [ ] Larger deterministic benchmark portfolio

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
| 2026-08-27 | Stable CandidatePath tool serialization contract added to prevent partial legacy payloads entering the domain |
| 2026-08-28 | M4 shared scheduled-segment detection, aggregate feasibility, consolidation economics and tests added |
