# Candidate Path Discovery

The `paths` package generates feasible shipment-level transportation strategies. It is deliberately deterministic and independent of Google ADK and the future OR-Tools optimizer.

## CandidatePath

`CandidatePath` is the handoff contract between path discovery and portfolio optimization. It contains:

- ordered transport legs
- shipment reference
- total evaluated cost and currency
- in-vehicle transit time
- waiting time, including readiness and transfer waits
- transfer count
- compounded reliability
- transport modes and provider IDs
- maximum weight/volume capacity utilization across legs
- deadline feasibility
- optional emissions estimate
- path status and metadata

The object does **not** choose a preferred route.

## Search semantics

`PathSearchEngine` considers scheduled services only when they are feasible for the shipment and configured policy:

- shipment readiness and deadlines
- service and schedule availability
- schedule-specific remaining capacity
- weight and volume capacity
- cargo restrictions
- provider and mode allow/deny policies
- maximum legs/transfers
- minimum transfer handling time
- transfer handling cost
- cycle/reuse protection
- reliability threshold

Pricing currently evaluates `fixed`, `quoted`, `per_kg`, and `per_volume`. A `per_km` or `per_kg_km` price is rejected until distance is a first-class service/graph attribute. The engine intentionally does not reinterpret a distance rate as a total price.

## Pareto filtering

After candidate generation, `remove_dominated_paths()` removes a path only when another path is no worse on cost, transit time, waiting time, transfer count and reliability, and strictly better on at least one. When both paths contain emissions estimates, emissions are also considered.

This preserves genuine trade-offs. For example, a cheaper/slower path and a faster/more-expensive path both survive for the later business-policy optimizer.

Capacity utilization is not part of dominance because preserving spare capacity can be strategically valuable when optimizing a shipment portfolio.

## Deliberate future extensions

The current contract leaves explicit extension points for:

- distance-aware pricing and emissions
- transfer compatibility matrices
- provider-specific transfer rules
- richer cargo restrictions
- path rejection diagnostics
- benchmark instrumentation
- portfolio-level shared-segment consolidation
