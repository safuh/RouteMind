"""Typed models for dynamic logistics re-optimization."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from routemind.domain.models import OptimizationResult


class DisruptionType(StrEnum):
    SERVICE_CANCELLATION = "service_cancellation"
    SCHEDULE_DELAY = "schedule_delay"
    CAPACITY_REDUCTION = "capacity_reduction"
    NEW_ORDER = "new_order"


class DisruptionEvent(BaseModel):
    """A fact supplied by an integration or operator that requires recovery."""

    id: str
    occurred_at: datetime
    type: DisruptionType
    option_id: str | None = None
    schedule_departure_at: datetime | None = None
    delay_seconds: int | None = Field(default=None, gt=0)
    available_weight_kg: float | None = Field(default=None, gt=0)
    available_volume_m3: float | None = Field(default=None, gt=0)
    new_shipment_id: str | None = None

    @model_validator(mode="after")
    def validate_event_fields(self) -> DisruptionEvent:
        if self.type is DisruptionType.NEW_ORDER:
            if not self.new_shipment_id:
                raise ValueError("new_order events require new_shipment_id")
            return self
        if not self.option_id:
            raise ValueError(f"{self.type.value} events require option_id")
        if self.type is DisruptionType.SCHEDULE_DELAY and self.delay_seconds is None:
            raise ValueError("schedule_delay events require delay_seconds")
        if self.type is DisruptionType.CAPACITY_REDUCTION and (
            self.available_weight_kg is None and self.available_volume_m3 is None
        ):
            raise ValueError("capacity_reduction events require an available capacity value")
        return self


class EventImpact(BaseModel):
    event_id: str
    impacted_shipment_ids: list[str] = Field(default_factory=list)
    preserved_shipment_ids: list[str] = Field(default_factory=list)
    invalidated_candidate_count: int = Field(ge=0)
    reason: str


class DecisionAuditEntry(BaseModel):
    event_id: str
    action: str
    shipment_ids: list[str] = Field(default_factory=list)
    detail: str


class ReoptimizationResult(BaseModel):
    result: OptimizationResult
    impact: EventImpact
    audit_trail: list[DecisionAuditEntry] = Field(default_factory=list)
