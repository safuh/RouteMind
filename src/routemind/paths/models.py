"""Candidate path models and Pareto-dominance helpers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from routemind.domain.models import TransportLeg, TransportMode


class PathStatus(StrEnum):
    """Lifecycle state for a generated candidate path."""

    FEASIBLE = "feasible"


class CandidatePath(BaseModel):
    """A feasible ordered sequence of transport legs for one shipment."""

    model_config = ConfigDict(frozen=True)

    shipment_id: str
    legs: tuple[TransportLeg, ...]
    total_cost: Decimal = Field(ge=Decimal("0"))
    currency: str
    transit_seconds: float = Field(ge=0)
    waiting_seconds: float = Field(ge=0)
    number_of_transfers: int = Field(ge=0)
    reliability: float = Field(ge=0, le=1)
    modes: tuple[TransportMode, ...]
    providers: tuple[str, ...]
    capacity_utilization: float = Field(ge=0)
    deadline_feasible: bool
    emissions_kg_co2e: float | None = Field(default=None, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)

    @property
    def departure_at(self) -> datetime:
        """Return the departure time of the path's first leg."""
        return self.legs[0].departure_at

    @property
    def arrival_at(self) -> datetime:
        """Return the arrival time of the path's final leg."""
        return self.legs[-1].arrival_at

    @property
    def elapsed_seconds(self) -> float:
        return self.transit_seconds + self.waiting_seconds

    @property
    def departure_at(self) -> datetime:
        """Departure timestamp of the first leg, used by time-window checks."""
        return self.legs[0].departure_at

    @property
    def arrival_at(self) -> datetime:
        """Arrival timestamp of the final leg, used by time-window checks."""
        return self.legs[-1].arrival_at

    @property
    def option_ids(self) -> tuple[str, ...]:
        return tuple(leg.option_id for leg in self.legs)

    @model_validator(mode="after")
    def validate_leg_continuity(self) -> CandidatePath:
        for previous, current in zip(self.legs, self.legs[1:], strict=False):
            if previous.destination.id != current.origin.id:
                raise ValueError("Candidate path legs must form a continuous journey")
            if current.departure_at < previous.arrival_at:
                raise ValueError("Candidate path legs cannot overlap")
        if self.number_of_transfers != len(self.legs) - 1:
            raise ValueError("number_of_transfers must equal number of connections")
        return self

    def dominates(self, other: CandidatePath) -> bool:
        """Return whether this path is no worse on all optimization dimensions."""
        return (
            self.total_cost <= other.total_cost
            and self.elapsed_seconds <= other.elapsed_seconds
            and self.reliability >= other.reliability
            and self.capacity_utilization <= other.capacity_utilization
            and (
                self.emissions_kg_co2e is None
                or other.emissions_kg_co2e is None
                or self.emissions_kg_co2e <= other.emissions_kg_co2e
            )
            and (
                self.total_cost < other.total_cost
                or self.elapsed_seconds < other.elapsed_seconds
                or self.reliability > other.reliability
                or self.capacity_utilization < other.capacity_utilization
                or (
                    self.emissions_kg_co2e is not None
                    and other.emissions_kg_co2e is not None
                    and self.emissions_kg_co2e < other.emissions_kg_co2e
                )
            )
        )


def remove_dominated_paths(paths: Sequence[CandidatePath]) -> list[CandidatePath]:
    """Return paths not dominated by another candidate."""
    return [
        candidate
        for index, candidate in enumerate(paths)
        if not any(
            other.dominates(candidate)
            for other_index, other in enumerate(paths)
            if index != other_index
        )
    ]
