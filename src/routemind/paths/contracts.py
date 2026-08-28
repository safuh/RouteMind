"""Stable serialization contracts between deterministic path discovery and tools.

The domain ``CandidatePath`` remains the internal optimization handoff. Tool/API
callers should consume this DTO rather than constructing domain objects from
partial LLM-generated dictionaries.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from routemind.domain.models import Location, TransportMode

from .models import CandidatePath


class TransportLegContract(BaseModel):
    """Complete, tool-safe representation of one scheduled transport leg."""

    model_config = ConfigDict(frozen=True)

    option_id: str
    origin: Location
    destination: Location
    departure_at: str
    arrival_at: str
    allocated_weight_kg: float = Field(ge=0)
    allocated_volume_m3: float = Field(ge=0)


class CandidatePathContract(BaseModel):
    """Read-only response contract for ADK/API consumers."""

    model_config = ConfigDict(frozen=True)

    shipment_id: str
    legs: tuple[TransportLegContract, ...] = Field(min_length=1)
    total_cost: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    transit_seconds: float = Field(ge=0)
    waiting_seconds: float = Field(ge=0)
    number_of_transfers: int = Field(ge=0)
    reliability: float = Field(ge=0, le=1)
    modes: tuple[TransportMode, ...] = Field(min_length=1)
    providers: tuple[str, ...] = Field(min_length=1)
    capacity_utilization: float = Field(ge=0, le=1)
    deadline_feasible: bool
    emissions_kg_co2e: float | None = Field(default=None, ge=0)
    status: str
    reason: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, path: CandidatePath) -> "CandidatePathContract":
        """Serialize a validated domain path without accepting partial input."""
        return cls(
            shipment_id=path.shipment_id,
            legs=tuple(
                TransportLegContract(
                    option_id=leg.option_id,
                    origin=leg.origin,
                    destination=leg.destination,
                    departure_at=leg.departure_at.isoformat(),
                    arrival_at=leg.arrival_at.isoformat(),
                    allocated_weight_kg=leg.allocated_weight_kg,
                    allocated_volume_m3=leg.allocated_volume_m3,
                )
                for leg in path.legs
            ),
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
            status=path.status.value,
            reason=path.reason,
            metadata=path.metadata,
        )


def serialize_candidate_paths(paths: list[CandidatePath]) -> list[CandidatePathContract]:
    """Serialize only already-validated domain candidates."""
    return [CandidatePathContract.from_domain(path) for path in paths]
