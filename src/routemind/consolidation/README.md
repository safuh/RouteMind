# Shipment Consolidation

The `consolidation` package is the first M4 foundation. It is deterministic and independent of Google ADK and the future OR-Tools optimizer.

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

No assumption is made that consolidation is economically beneficial. The optimizer in M5 can later choose between feasible opportunities using business policy.

## Scope of this brick

This module intentionally does **not** solve portfolio optimization, reserve capacity globally, enumerate all possible shipment subsets, or perform hub-and-spoke optimization. Those are subsequent M4/M5 responsibilities. The current contract provides a reliable input for those layers.
