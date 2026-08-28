# Candidate Path Discovery & Consolidation

The `paths` package generates feasible shipment-level transportation strategies and identifies deterministic opportunities for multiple strategies to share concrete scheduled transport capacity. It is independent of Google ADK and the future OR-Tools optimizer.

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

## Tool/API contract

`CandidatePathContract` is a read-only serialization DTO for ADK/API consumers. Consumers should use `serialize_candidate_paths()` on validated domain candidates instead of constructing `CandidatePath` from LLM-generated dictionaries.

A complete leg requires:

- `option_id`
- origin and destination `Location`
- concrete departure timestamp
- concrete arrival timestamp
- allocated weight
- allocated volume

This boundary prevents legacy/partial payloads such as `path_id`/`leg_id` with null locations from entering the deterministic domain model.

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
- distance-aware pricing and optional emissions

## Pareto filtering

After candidate generation, `remove_dominated_paths()` removes a path only when another path is no worse on cost, transit time, waiting time, transfer count and reliability, and strictly better on at least one. When both paths contain emissions estimates, emissions are also considered.

Capacity utilization is not part of dominance because preserving spare capacity can be strategically valuable when optimizing a shipment portfolio.

## Shipment consolidation foundation

`ConsolidationEngine` detects shared **scheduled transport instances**, not merely matching geographic routes. A `SharedSegment` is keyed by:

- transport option
- origin
- destination
- scheduled departure
- scheduled arrival

This distinction prevents two different buses/services on the same route from being treated as the same capacity.

`ConsolidationEngine.evaluate()` then checks aggregate:

- weight
- volume
- cargo restrictions
- deadline feasibility
- service availability

and evaluates segment economics under the supported pricing models. Fixed/quoted services can create direct consolidation savings; usage-based pricing may produce zero savings because aggregate usage remains additive.

The engine identifies opportunities but does **not** choose which portfolio combination to use. That decision belongs to the future optimization layer.
