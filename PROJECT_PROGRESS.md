# RouteMind — Project Progress Tracker

> Living engineering tracker. Do not mark a component complete until implementation, automated tests, documentation, and validation evidence exist.

**Current phase:** Milestone 4 — Shipment Consolidation

**Overall status:** ~78% — M3/M4/M5/M6 core implementation is on `main`; PR #7 contains an ADK surface fix awaiting CI completion. M4 now also has deterministic hub-and-spoke opportunity discovery. Remaining work is benchmark evidence, richer consolidation portfolio generation, model-backed ADK evaluation, and later milestones.

| Milestone | Area | Status |
|---|---|---:|
| M0 | Product & architecture | 🟢 |
| M1 | Multimodal domain + synthetic data | 🟢 |
| M2 | Transportation graph | 🟢 |
| M3 | Candidate path discovery | 🟡 |
| M4 | Shipment consolidation | 🟡 |
| M5 | Deterministic optimization | 🟢 Core implementation + automated validation |
| M6 | Google ADK agent layer | 🟢 Core implementation + automated validation; PR #7 pending |
| M7 | Dynamic re-optimization | ⬜ |
| M8 | Predictive logistics intelligence | ⬜ |
| M9 | Production platform | ⬜ |

# M3 — Candidate Path Discovery
**Status: 🟡 Implementation complete; runtime regression suite passing, benchmark evidence pending**

## Validation evidence
- [x] Full pytest suite executes successfully in GitHub Actions
- [x] Path-search regressions fixed for emissions state initialization
- [x] Waiting-time semantics validated
- [x] Minimum-transfer and maximum-transfer diagnostics validated

## Remaining
- [ ] Execute benchmark suite and capture runtime evidence
- [ ] Produce search performance benchmark report
- [ ] Add provider-specific transfer compatibility semantics

# M4 — Shipment Consolidation
**Status: 🟡 Deterministic foundation substantially implemented; advanced portfolio semantics pending**

## Implemented
- [x] Concrete scheduled shared-segment identity
- [x] Shared-segment detection across candidate paths
- [x] Different destinations can share an upstream segment
- [x] Shipment-group weight, volume and package aggregation
- [x] Schedule-specific remaining capacity checks
- [x] Existing domain cargo compatibility reused
- [x] Structured consolidation rejection diagnostics
- [x] Fixed/quoted and variable pricing economics
- [x] Deterministic shipment subset and candidate-path enumeration
- [x] Shipment time-window validation
- [x] Shared/private leg allocation
- [x] Shared downstream leg recognition
- [x] Per-segment resource aggregation
- [x] Shared/private cost attribution
- [x] Deterministic capacity reservation across competing opportunities
- [x] Exact scheduled-segment resource accounting
- [x] Shipment double-reservation protection
- [x] Atomic multi-segment reservation
- [x] Structured reservation rejection diagnostics
- [x] Consolidation regression suite passing in CI
- [x] Deterministic hub-and-spoke group discovery
- [x] Exact scheduled-prefix validation before hub-and-spoke classification
- [x] Hub-and-spoke regression tests

## Remaining
- [ ] Validate hub-and-spoke tests in CI
- [ ] Consolidation-vs-direct portfolio comparison
- [ ] Generate all coexisting feasible consolidation combinations
- [ ] Feed richer consolidation combinations into M5 optimization

# M5 — Deterministic Optimization Engine
**Status: 🟢 Core implementation and automated validation complete**

## Implemented
- [x] OR-Tools CP-SAT integration
- [x] Exactly-one candidate path assignment per shipment
- [x] Shared scheduled weight/volume capacity constraints
- [x] Schedule-specific capacity accounting
- [x] Provider/service availability filtering
- [x] Cost, time, reliability, emissions and transfer policy terms
- [x] Consolidation opportunity objective bonuses
- [x] Protection against double-counting overlapping consolidation savings
- [x] Deterministic single-worker solver configuration
- [x] Solver objective/constraint result metrics
- [x] Automated optimizer tests
- [x] M5 tests pass in CI

## Remaining
- [ ] Formal baseline comparison reporting
- [ ] Richer multi-segment consolidation portfolio generation from M4
- [ ] Full optimality-gap/benchmark reporting

# M6 — Google ADK Agent Layer
**Status: 🟢 Core implementation and automated validation complete; model-backed evaluation pending**

## Implemented
- [x] RouteMind Logistics Manager ADK agent
- [x] Structured policy extraction tool
- [x] Structured portfolio optimization tool
- [x] Optimization result validation tool
- [x] Deterministic result summarization
- [x] Deterministic infeasibility/trade-off explanation
- [x] Grounding instructions prohibiting invented logistics facts
- [x] Synthetic-data disclosure requirement
- [x] Google ADK 2.x dependency
- [x] Local ADK playground instructions
- [x] ADK tool regression tests
- [x] CI workflow for lint and full pytest execution
- [x] ADK agent import smoke test in CI
- [x] Full pytest suite passing in CI on the merged M5/M6 baseline
- [ ] Merge PR #7 after its corrected CI run passes

## Remaining
- [ ] Execute model-backed ADK evaluation/regression dataset with configured credentials
- [ ] Validate local `adk web` interactive session with real Gemini credentials

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
| 2026-08-27 | Deterministic shipment grouping and candidate-path enumeration added |
| 2026-08-27 | Explicit consolidation time-window compatibility checks and tests added |
| 2026-08-27 | Shared/private leg allocation and downstream cost attribution added |
| 2026-08-27 | Deterministic capacity reservation across competing consolidation opportunities added |
| 2026-08-27 | CP-SAT portfolio optimization with shared scheduled capacity and consolidation objective integration added |
| 2026-08-27 | Google ADK Logistics Manager, structured tools, grounding rules and CI workflow added |
| 2026-08-27 | Full 72-test CI suite and ADK import smoke test passed; M5/M6 merged to main |
| 2026-08-28 | PR #7 corrected ADK regression test to inspect wrapped tool names rather than function __name__ |
| 2026-08-28 | Deterministic hub-and-spoke opportunity discovery and regression tests added |
