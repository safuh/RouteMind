"""Stable serialization contracts for exposing deterministic path results."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from routemind.domain.models import Location, TransportMode
from routemind.paths.models import CandidatePath


class TransportLegContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    option_id: str
    origin: Location
    destination: Location
    departure_at: datetime
    arrival_at: datetime
    allocated_weight_kg: float
    allocated_volume_m3: float


class CandidatePathContract(BaseModel):
    """Public/tool-facing representation of a validated CandidatePath."""

    model_config = ConfigDict(frozen=True)

    shipment_id: str
    legs: tuple[TransportLegContract, ...]
    total_cost: Decimal
    currency: str
    transit_seconds: float
    waiting_seconds: float
    number_of_transfers: int
    reliability: float
    modes: tuple[TransportMode, ...]
    providers: tuple[str, ...]
    capacity_utilization: float
    deadline_feasible: bool
    emissions_kg_co2e: float | None


def serialize_candidate_path(path: CandidatePath) -> CandidatePathContract:
    return CandidatePathContract(
        shipment_id=path.shipment_id,
        legs=tuple(TransportLegContract.model_validate(leg.model_dump()) for leg in path.legs),
        total_cost=path.total_cost,
        currency=path.currency,
        transit_seconds=path.transit_seconds,
        waiting_seconds=path.waiting_seconds,
        number_of_transfers=path.number_of_transfers,
        reliability=path.reliability,
        modes=path.modes,
        providers=path.providers,
        capacity_utilization=path.capacity_utilization,
        deadline_feasible=path.deadline_feasible,
        emissions_kg_co2e=path.emissions_kg_co2e,
    )


def serialize_candidate_paths(paths: list[CandidatePath]) -> list[CandidatePathContract]:
    return [serialize_candidate_path(path) for path in paths]
