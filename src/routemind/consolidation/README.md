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

## Capacity reservation

`CapacityReservationLedger` is the deterministic bridge between individual consolidation opportunities and a future portfolio optimizer.

An accepted opportunity reserves capacity against the **exact scheduled segment identity**. Subsequent opportunities are checked against the capacity already reserved on that segment, so independently feasible opportunities cannot both consume the same remaining capacity.

The ledger also prevents a shipment from being reserved by more than one accepted opportunity in the same portfolio plan. Reservation is atomic across all segments in an opportunity: if any segment is infeasible, no segment is committed.

The ledger is intentionally deterministic and optimizer-independent. `reserve_opportunities()` applies opportunities in supplied order and reports an explicit result for each attempt; M5 can later use the same resource model while making the global selection decision.

## Scope

This module does not yet solve portfolio optimization, enumerate all hub-and-spoke structures, or choose the globally best set of opportunities. It provides a reliable deterministic resource-consumption contract for those subsequent layers.
