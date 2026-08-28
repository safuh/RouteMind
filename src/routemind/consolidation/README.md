# Shipment Consolidation

The `consolidation` package is a deterministic M4 foundation independent of Google ADK and the future OR-Tools optimizer.

## Shared segment identity

A shared segment is a **concrete scheduled transport instance**, identified by:

- transport option ID
- origin
- departure timestamp
- arrival timestamp

Therefore, two services with the same geographic origin/destination do not share capacity unless they are the same scheduled transport instance. Two paths can share a first leg and diverge later without their downstream legs becoming shared.

## Feasibility

`evaluate_consolidation()` checks the proposed shipment group against the concrete service schedule and existing domain cargo restrictions. It aggregates:

- weight
- volume
- package quantity

It uses schedule-specific remaining capacity when supplied, rather than assuming the transport option's headline capacity is still available.

Candidate paths already enforce shipment readiness, transfer timing, and deadline feasibility. Consolidation does not weaken those constraints. A service is still required to match the same scheduled instance for all participating paths.

Cargo compatibility delegates to the existing domain policy (`shipment_is_compatible`) instead of creating a second incompatible restriction system.

## Economics

The engine compares the cost of charging each shipment independently on the shared segment with the cost of the consolidated service:

- `fixed` / `quoted`: one shared charge, so consolidation can create savings.
- `per_kg` / `per_volume`: charges remain additive, so feasibility does not imply savings.
- `per_km` / `per_kg_km`: charges remain additive and require `distance_km`.

No assumption is made that consolidation is economically beneficial. M5 can later choose between feasible opportunities using business policy.

## Candidate opportunity generation

`generate_consolidation_opportunities()` expands the deterministic shipment subsets and all candidate-path combinations for those subsets before evaluating feasibility. This is important because the first discovered path for a shipment is not necessarily the path that can participate in a shared scheduled service.

Only opportunities that are actually feasible are returned. Their original deterministic ordering is preserved.

## Coexisting opportunity portfolios

`generate_coexisting_opportunity_combinations()` enumerates feasible combinations of the generated opportunities. It uses the same capacity reservation contract as the standalone reservation layer, so a combination is accepted only when:

- no shipment is reserved by two consolidation opportunities;
- every exact scheduled segment remains within weight capacity;
- every exact scheduled segment remains within volume capacity when modeled; and
- all reservations in the combination can be committed atomically in deterministic order.

The empty combination is included as the no-consolidation baseline. An opportunity can therefore be individually feasible while a larger combination is rejected because the opportunities compete for the same scheduled capacity.

## Capacity reservation

`CapacityReservationLedger` is the deterministic bridge between individual consolidation opportunities and a future portfolio optimizer.

An accepted opportunity reserves capacity against the **exact scheduled segment identity**. Subsequent opportunities are checked against the capacity already reserved on that segment, so independently feasible opportunities cannot both consume the same remaining capacity.

The ledger also prevents a shipment from being reserved by more than one accepted opportunity in the same portfolio plan. Reservation is atomic across all segments in an opportunity: if any segment is infeasible, no segment is committed.

The ledger is intentionally deterministic and optimizer-independent. `reserve_opportunities()` applies opportunities in supplied order and reports an explicit result for each attempt; M5 can use the same resource model while making the global selection decision.

## Scope

The remaining M4 work is to generate new hub-and-spoke structures when they are not already represented by discovered candidate paths, then connect those generated opportunities to the M5 portfolio optimizer and benchmark their value against unconsolidated/direct baselines.
