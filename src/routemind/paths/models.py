"""Path-level domain objects and metrics for candidate transportation strategies."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from routemind.domain.models import TransportLeg, TransportMode


class PathStatus(StrEnum):
    FEASIBLE = "feasible"


class CandidatePath(BaseModel):
    """A complete feasible strategy for moving one shipment.

    CandidatePath deliberately contains decision metrics but does not select a
    winner. The optimization layer can compare these alternatives later using
    a configurable business objective.
    """

    model_config = ConfigDict(frozen=True)

    shipment_id: str
    legs: tuple[TransportLeg, ...] = Field(min_length=1)
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
    status: PathStatus = PathStatus.FEASIBLE
    reason: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def departure_at(self) -> datetime:
        return self.legs[0].departure_at

    @property
    def arrival_at(self) -> datetime:
        return self.legs[-1].arrival_at

    @property
    def elapsed_seconds(self) -> float:
        return self.transit_seconds + self.waiting_seconds

    @property
    def option_ids(self) -> tuple[str, ...]:
        return tuple(leg.option_id for leg in self.legs)

    @model_validator(mode="after")
    def validate_leg_continuity(self) -> CandidatePath:
        for previous, current in zip(self.legs, self.legs[1:], strict=True):
            if previous.destination.id != current.origin.id:
                raise ValueError("Candidate path legs must form a continuous journey")
            if current.departure_at < previous.arrival_at:
                raise ValueError("Candidate path legs cannot overlap")
        if self.number_of_transfers != len(self.legs) - 1:
            raise ValueError("number_of_transfers must equal number of connections")
        return self

    def dominates(self, other: CandidatePath) -> bool:
        """Return whether this path Pareto-dominates another path.

        Lower cost/time/transfers/emissions and higher reliability are better.
        Emissions are compared only when both candidates have an estimate.
        Capacity utilization is intentionally excluded: preserving spare
        capacity can be valuable to a portfolio optimizer and is policy-driven.
        """
        if self.currency != other.currency:
            return False

        no_worse = (
            self.total_cost <= other.total_cost
            and self.transit_seconds <= other.transit_seconds
            and self.waiting_seconds <= other.waiting_seconds
            and self.number_of_transfers <= other.number_of_transfers
            and self.reliability >= other.reliability
        )
        strictly_better = (
            self.total_cost < other.total_cost
            or self.transit_seconds < other.transit_seconds
            or self.waiting_seconds < other.waiting_seconds
            or self.number_of_transfers < other.number_of_transfers
            or self.reliability > other.reliability
        )

        if self.emissions_kg_co2e is not None and other.emissions_kg_co2e is not None:
            no_worse = no_worse and self.emissions_kg_co2e <= other.emissions_kg_co2e
            strictly_better = strictly_better or self.emissions_kg_co2e < other.emissions_kg_co2e

        return no_worse and strictly_better
