"""Structured diagnostics emitted while evaluating candidate path options."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RejectionReason(StrEnum):
    INVALID_SHIPMENT_TIMING = "invalid_shipment_timing"
    UNAVAILABLE = "unavailable"
    POLICY_MODE = "policy_mode"
    POLICY_PROVIDER = "policy_provider"
    CARGO_RESTRICTION = "cargo_restriction"
    MISSED_DEPARTURE = "missed_departure"
    INVALID_SCHEDULE = "invalid_schedule"
    DEADLINE = "deadline"
    TRANSFER_TIME = "transfer_time"
    WEIGHT_CAPACITY = "weight_capacity"
    VOLUME_CAPACITY = "volume_capacity"
    RELIABILITY = "reliability"
    UNSUPPORTED_PRICING = "unsupported_pricing"
    SEARCH_LIMIT = "search_limit"


class PathRejection(BaseModel):
    """Machine-readable explanation for excluding a transport alternative."""

    model_config = ConfigDict(frozen=True)

    option_id: str | None = None
    schedule_departure: str | None = None
    reason: RejectionReason
    message: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class PathSearchDiagnostics(BaseModel):
    """Auditable search counters and rejected alternatives."""

    model_config = ConfigDict(frozen=True)

    expansions: int = Field(ge=0)
    generated_candidates: int = Field(ge=0)
    retained_candidates: int = Field(ge=0)
    rejected: tuple[PathRejection, ...] = ()
    expansion_limit_reached: bool = False

    @property
    def rejection_count(self) -> int:
        return len(self.rejected)

    def by_reason(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for rejection in self.rejected:
            key = rejection.reason.value
            counts[key] = counts.get(key, 0) + 1
        return counts
