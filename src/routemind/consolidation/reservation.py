"""Deterministic reservation of shared transport capacity across opportunities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from routemind.domain.models import Shipment, TransportOption

from .models import ConsolidationOpportunity, SharedTransportSegment


@dataclass(frozen=True, slots=True)
class CapacityReservation:
    """Capacity consumed by one accepted consolidation opportunity on one service."""

    opportunity_key: tuple[str, ...]
    segment: SharedTransportSegment
    shipment_ids: tuple[str, ...]
    weight_kg: float
    volume_m3: float
    package_count: int


@dataclass(frozen=True, slots=True)
class CapacityReservationRejection:
    """Structured reason why an opportunity cannot reserve shared capacity."""

    reason: str
    message: str
    segment: SharedTransportSegment | None = None
    shipment_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapacityReservationResult:
    """Result of an atomic reservation attempt."""

    accepted: bool
    reservations: tuple[CapacityReservation, ...] = ()
    rejections: tuple[CapacityReservationRejection, ...] = ()


class CapacityReservationLedger:
    """In-memory deterministic ledger for competing consolidation opportunities.

    The ledger is deliberately independent of the optimizer. Each accepted
    opportunity consumes capacity on every concrete scheduled segment it shares.
    A shipment may belong to at most one accepted consolidation opportunity,
    preventing a shipment's weight/volume from being counted twice on the same
    portfolio plan.
    """

    def __init__(self) -> None:
        self._reservations: list[CapacityReservation] = []
        self._reserved_shipments: set[str] = set()

    @property
    def reservations(self) -> tuple[CapacityReservation, ...]:
        return tuple(self._reservations)

    def reserved_weight_kg(self, segment: SharedTransportSegment) -> float:
        return sum(
            item.weight_kg
            for item in self._reservations
            if item.segment.identity == segment.identity
        )

    def reserved_volume_m3(self, segment: SharedTransportSegment) -> float:
        return sum(
            item.volume_m3
            for item in self._reservations
            if item.segment.identity == segment.identity
        )

    def reserved_package_count(self, segment: SharedTransportSegment) -> int:
        return sum(
            item.package_count
            for item in self._reservations
            if item.segment.identity == segment.identity
        )

    def reserve(
        self,
        opportunity: ConsolidationOpportunity,
        shipments: dict[str, Shipment],
        transport_options: dict[str, TransportOption],
    ) -> CapacityReservationResult:
        """Atomically reserve an opportunity if all shared resources remain feasible.

        Validation is performed for every shared segment before mutating the
        ledger. A rejected opportunity therefore consumes no capacity.
        """
        shipment_ids = tuple(opportunity.shipment_ids)
        duplicate_shipments = tuple(sorted(set(shipment_ids) & self._reserved_shipments))
        if duplicate_shipments:
            return CapacityReservationResult(
                accepted=False,
                rejections=(
                    CapacityReservationRejection(
                        reason="shipment_already_reserved",
                        message=(
                            "Shipment(s) "
                            f"{', '.join(duplicate_shipments)} already belong to an accepted "
                            "consolidation opportunity."
                        ),
                        shipment_ids=duplicate_shipments,
                    ),
                ),
            )

        missing_shipments = tuple(item for item in shipment_ids if item not in shipments)
        if missing_shipments:
            return CapacityReservationResult(
                accepted=False,
                rejections=(
                    CapacityReservationRejection(
                        reason="unknown_shipment",
                        message=f"Unknown shipment(s): {', '.join(missing_shipments)}.",
                        shipment_ids=missing_shipments,
                    ),
                ),
            )

        reservations: list[CapacityReservation] = []
        rejections: list[CapacityReservationRejection] = []
        for segment in opportunity.shared_segments:
            option = transport_options.get(segment.option_id)
            if option is None:
                rejections.append(
                    CapacityReservationRejection(
                        reason="unknown_transport_service",
                        message=f"Transport option {segment.option_id!r} is unavailable.",
                        segment=segment,
                        shipment_ids=shipment_ids,
                    )
                )
                continue

            schedule = next(
                (
                    item
                    for item in option.schedules
                    if item.departure_at == segment.departure_at
                    and item.arrival_at == segment.arrival_at
                ),
                None,
            )
            if schedule is None:
                rejections.append(
                    CapacityReservationRejection(
                        reason="unknown_transport_schedule",
                        message="The shared segment does not match a concrete transport schedule.",
                        segment=segment,
                        shipment_ids=shipment_ids,
                    )
                )
                continue

            weight = sum(shipments[item].weight_kg for item in shipment_ids)
            volume = sum(shipments[item].volume_m3 for item in shipment_ids)
            packages = sum(
                package.quantity
                for item in shipment_ids
                for package in shipments[item].packages
            )

            weight_capacity = (
                schedule.available_weight_kg
                if schedule.available_weight_kg is not None
                else option.capacity.max_weight_kg
            )
            volume_capacity = schedule.available_volume_m3
            if volume_capacity is None:
                volume_capacity = option.capacity.max_volume_m3

            remaining_weight = weight_capacity - self.reserved_weight_kg(segment)
            if weight > remaining_weight:
                rejections.append(
                    CapacityReservationRejection(
                        reason="capacity_weight",
                        message=(
                            f"Opportunity requires {weight:g} kg, but only "
                            f"{remaining_weight:g} kg remains on the scheduled service."
                        ),
                        segment=segment,
                        shipment_ids=shipment_ids,
                    )
                )

            if volume_capacity is not None:
                remaining_volume = volume_capacity - self.reserved_volume_m3(segment)
                if volume > remaining_volume:
                    rejections.append(
                        CapacityReservationRejection(
                            reason="capacity_volume",
                            message=(
                                f"Opportunity requires {volume:g} m³, but only "
                                f"{remaining_volume:g} m³ remains on the scheduled service."
                            ),
                            segment=segment,
                            shipment_ids=shipment_ids,
                        )
                    )

            reservations.append(
                CapacityReservation(
                    opportunity_key=shipment_ids,
                    segment=segment,
                    shipment_ids=shipment_ids,
                    weight_kg=weight,
                    volume_m3=volume,
                    package_count=packages,
                )
            )

        if rejections:
            return CapacityReservationResult(accepted=False, rejections=tuple(rejections))

        self._reservations.extend(reservations)
        self._reserved_shipments.update(shipment_ids)
        return CapacityReservationResult(accepted=True, reservations=tuple(reservations))


def reserve_opportunities(
    opportunities: Iterable[ConsolidationOpportunity],
    shipments: dict[str, Shipment],
    transport_options: dict[str, TransportOption],
) -> tuple[CapacityReservationLedger, tuple[CapacityReservationResult, ...]]:
    """Apply opportunities in deterministic input order and report each result."""
    ledger = CapacityReservationLedger()
    results = tuple(
        ledger.reserve(opportunity, shipments, transport_options)
        for opportunity in opportunities
    )
    return ledger, results
