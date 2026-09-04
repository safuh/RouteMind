"""Incremental, deterministic recovery after a logistics disruption."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta

from routemind.domain.models import (
    OptimizationPolicy,
    OptimizationResult,
    Shipment,
    TransportLeg,
    TransportOption,
    TransportPlan,
)
from routemind.optimization import optimize_portfolio
from routemind.paths import PathSearchEngine
from routemind.paths.models import CandidatePath

from .models import (
    DecisionAuditEntry,
    DisruptionEvent,
    DisruptionType,
    EventImpact,
    ReoptimizationResult,
)


def reoptimize_portfolio(
    current_result: OptimizationResult,
    candidate_paths: Iterable[CandidatePath],
    transport_options: dict[str, TransportOption],
    event: DisruptionEvent,
    policy: OptimizationPolicy | None = None,
    shipments: Iterable[Shipment] = (),
    max_time_seconds: float = 30.0,
) -> ReoptimizationResult:
    """Recover from one event while retaining unaffected selected assignments.

    Candidate paths are immutable snapshots. A changed or cancelled scheduled
    service invalidates every candidate that uses its affected schedule. When
    shipment facts are supplied, replacement candidates are discovered from the
    event-adjusted transport data before recovery. Unaffected shipments are
    constrained to their existing selected path, making the solve incremental
    while retaining exact shared-capacity accounting.
    """
    paths = tuple(candidate_paths)
    selected_by_shipment = _selected_paths(current_result.plans, paths)
    impacted_ids = _impacted_shipments(current_result.plans, event)
    expected_ids = set(selected_by_shipment)
    if event.type is DisruptionType.NEW_ORDER and event.new_shipment_id:
        expected_ids.add(event.new_shipment_id)

    valid_paths, invalidated = _valid_paths(paths, event)
    recovery_ids = impacted_ids | ({event.new_shipment_id} if event.new_shipment_id else set())
    refreshed_paths = discover_recovery_paths(
        (shipment for shipment in shipments if shipment.id in recovery_ids),
        transport_options,
        event,
    )
    if refreshed_paths:
        valid_paths = valid_paths + refreshed_paths
    preserved_ids = sorted(expected_ids - impacted_ids - ({event.new_shipment_id} if event.new_shipment_id else set()))
    incremental_paths = [
        path
        for path in valid_paths
        if path.shipment_id in impacted_ids
        or path.shipment_id == event.new_shipment_id
        or selected_by_shipment.get(path.shipment_id) == path
    ]
    missing = sorted(expected_ids - {path.shipment_id for path in incremental_paths})
    audit = [
        DecisionAuditEntry(
            event_id=event.id,
            action="event_received",
            detail=_event_description(event),
        ),
        DecisionAuditEntry(
            event_id=event.id,
            action="preserved_assignments",
            shipment_ids=preserved_ids,
            detail="Unaffected shipments remain fixed to their selected candidate path.",
        ),
    ]
    if invalidated:
        audit.append(
            DecisionAuditEntry(
                event_id=event.id,
                action="invalidated_candidates",
                detail=f"Removed {invalidated} candidate path(s) affected by the event.",
            )
        )
    if refreshed_paths:
        audit.append(
            DecisionAuditEntry(
                event_id=event.id,
                action="recovery_candidates_discovered",
                shipment_ids=sorted({path.shipment_id for path in refreshed_paths}),
                detail=f"Discovered {len(refreshed_paths)} replacement candidate path(s) from refreshed transport data.",
            )
        )

    impact = EventImpact(
        event_id=event.id,
        impacted_shipment_ids=sorted(impacted_ids),
        preserved_shipment_ids=preserved_ids,
        invalidated_candidate_count=invalidated,
        reason=_event_description(event),
    )
    if missing:
        audit.append(
            DecisionAuditEntry(
                event_id=event.id,
                action="recovery_infeasible",
                shipment_ids=missing,
                detail="No valid candidate path remains for the listed shipment(s).",
            )
        )
        return ReoptimizationResult(
            result=OptimizationResult(
                plans=[], objective_value=0.0, feasible=False,
                warnings=[f"Recovery requires replacement candidate paths for: {', '.join(missing)}."],
            ),
            impact=impact,
            audit_trail=audit,
        )

    adjusted_options = _adjusted_options(transport_options, event)
    result = optimize_portfolio(
        incremental_paths, adjusted_options, policy, max_time_seconds=max_time_seconds
    )
    audit.append(
        DecisionAuditEntry(
            event_id=event.id,
            action="reoptimized" if result.feasible else "recovery_infeasible",
            shipment_ids=sorted(expected_ids),
            detail="Incremental deterministic portfolio optimization completed."
            if result.feasible
            else "; ".join(result.warnings),
        )
    )
    return ReoptimizationResult(result=result, impact=impact, audit_trail=audit)


def discover_recovery_paths(
    shipments: Iterable[Shipment],
    transport_options: dict[str, TransportOption],
    event: DisruptionEvent,
) -> tuple[CandidatePath, ...]:
    """Discover fresh candidate paths against the transport state after an event.

    This function is deliberately deterministic and accepts only typed shipment
    and transport data. It does not infer replacement services or schedules.
    """
    engine = PathSearchEngine(list(_adjusted_options(transport_options, event).values()))
    return tuple(path for shipment in shipments for path in engine.discover_paths(shipment))


def _selected_paths(plans: Iterable[TransportPlan], paths: Iterable[CandidatePath]) -> dict[str, CandidatePath]:
    by_key = {
        (path.shipment_id, _leg_signature(path.legs), path.currency): path
        for path in paths
    }
    return {
        plan.shipment_id: by_key[(plan.shipment_id, _leg_signature(plan.legs), plan.currency)]
        for plan in plans
        if (plan.shipment_id, _leg_signature(plan.legs), plan.currency) in by_key
    }


def _leg_signature(legs: Iterable[TransportLeg]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            leg.option_id,
            leg.origin.id,
            leg.destination.id,
            leg.departure_at,
            leg.arrival_at,
            leg.allocated_weight_kg,
            leg.allocated_volume_m3,
        )
        for leg in legs
    )


def _impacted_shipments(plans: Iterable[TransportPlan], event: DisruptionEvent) -> set[str]:
    if event.type is DisruptionType.NEW_ORDER:
        return set()
    return {
        plan.shipment_id
        for plan in plans
        if any(_leg_matches_event(leg.option_id, leg.departure_at, event) for leg in plan.legs)
    }


def _valid_paths(paths: Iterable[CandidatePath], event: DisruptionEvent) -> tuple[tuple[CandidatePath, ...], int]:
    if event.type is DisruptionType.NEW_ORDER:
        values = tuple(paths)
        return values, 0
    valid = tuple(
        path
        for path in paths
        if not any(_leg_matches_event(leg.option_id, leg.departure_at, event) for leg in path.legs)
    )
    return valid, len(tuple(paths)) - len(valid)


def _leg_matches_event(option_id: str, departure_at: object, event: DisruptionEvent) -> bool:
    return option_id == event.option_id and (
        event.schedule_departure_at is None or departure_at == event.schedule_departure_at
    )


def _adjusted_options(
    options: dict[str, TransportOption], event: DisruptionEvent
) -> dict[str, TransportOption]:
    if event.type is DisruptionType.NEW_ORDER or event.option_id not in options:
        return options
    option = options[event.option_id]
    if event.type is DisruptionType.SERVICE_CANCELLATION:
        return {**options, event.option_id: option.model_copy(update={"available": False})}
    if event.type is DisruptionType.SCHEDULE_DELAY:
        delay = timedelta(seconds=event.delay_seconds or 0)
        schedules = [
            schedule.model_copy(
                update={
                    "departure_at": schedule.departure_at + delay,
                    "arrival_at": schedule.arrival_at + delay,
                }
            )
            if event.schedule_departure_at is None or schedule.departure_at == event.schedule_departure_at
            else schedule
            for schedule in option.schedules
        ]
        return {**options, event.option_id: option.model_copy(update={"schedules": schedules})}
    if event.type is not DisruptionType.CAPACITY_REDUCTION:
        return options
    schedules = [
        schedule.model_copy(
            update={
                "available_weight_kg": event.available_weight_kg
                if event.available_weight_kg is not None else schedule.available_weight_kg,
                "available_volume_m3": event.available_volume_m3
                if event.available_volume_m3 is not None else schedule.available_volume_m3,
            }
        )
        if event.schedule_departure_at is None or schedule.departure_at == event.schedule_departure_at
        else schedule
        for schedule in option.schedules
    ]
    return {**options, event.option_id: option.model_copy(update={"schedules": schedules})}


def _event_description(event: DisruptionEvent) -> str:
    if event.type is DisruptionType.NEW_ORDER:
        return f"New shipment {event.new_shipment_id} inserted into the portfolio."
    if event.type is DisruptionType.SERVICE_CANCELLATION:
        return f"Service {event.option_id} was cancelled."
    if event.type is DisruptionType.SCHEDULE_DELAY:
        return f"Service {event.option_id} was delayed by {timedelta(seconds=event.delay_seconds or 0)}."
    return f"Service {event.option_id} capacity was reduced."
