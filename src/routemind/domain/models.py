"""Domain models for shipments and multimodal transportation resources."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

PositiveFloat = Annotated[float, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]


class TransportMode(StrEnum):
    MOTORCYCLE = "motorcycle"
    VAN = "van"
    TRUCK = "truck"
    BUS = "bus"
    RAIL = "rail"
    AIR = "air"
    SEA = "sea"
    COURIER = "courier"
    THREE_PL = "3pl"
    OTHER = "other"


class PricingModel(StrEnum):
    FIXED = "fixed"
    PER_KG = "per_kg"
    PER_VOLUME = "per_volume"
    PER_KM = "per_km"
    PER_KG_KM = "per_kg_km"
    QUOTED = "quoted"


class Location(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Package(BaseModel):
    id: str
    weight_kg: PositiveFloat
    length_m: PositiveFloat
    width_m: PositiveFloat
    height_m: PositiveFloat
    quantity: int = Field(default=1, ge=1)
    fragile: bool = False
    temperature_controlled: bool = False

    @property
    def volume_m3(self) -> float:
        return self.length_m * self.width_m * self.height_m * self.quantity


class Shipment(BaseModel):
    id: str
    origin: Location
    destination: Location
    packages: list[Package] = Field(min_length=1)
    ready_at: datetime
    deadline: datetime | None = None
    priority: int = Field(default=0, ge=0)
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def weight_kg(self) -> float:
        return sum(package.weight_kg * package.quantity for package in self.packages)

    @property
    def volume_m3(self) -> float:
        return sum(package.volume_m3 for package in self.packages)


class TransportCapacity(BaseModel):
    max_weight_kg: PositiveFloat
    max_volume_m3: PositiveFloat | None = None
    max_length_m: PositiveFloat | None = None
    max_width_m: PositiveFloat | None = None
    max_height_m: PositiveFloat | None = None


class TransportSchedule(BaseModel):
    departure_at: datetime
    arrival_at: datetime
    available_weight_kg: PositiveFloat | None = None
    available_volume_m3: PositiveFloat | None = None

    @property
    def transit_seconds(self) -> float:
        return (self.arrival_at - self.departure_at).total_seconds()


class TransportPrice(BaseModel):
    model: PricingModel
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class TransportOption(BaseModel):
    """A transportation service or capacity offering."""

    id: str
    provider_id: str
    provider_name: str
    mode: TransportMode
    origin: Location
    destination: Location
    capacity: TransportCapacity
    schedules: list[TransportSchedule] = Field(default_factory=list)
    price: TransportPrice
    reliability: float = Field(ge=0, le=1)
    available: bool = True
    distance_km: NonNegativeFloat | None = None
    carbon_kg_co2e_per_km: NonNegativeFloat | None = None
    restrictions: set[str] = Field(default_factory=set)


class TransportLeg(BaseModel):
    option_id: str
    origin: Location
    destination: Location
    departure_at: datetime
    arrival_at: datetime
    allocated_weight_kg: NonNegativeFloat = 0
    allocated_volume_m3: NonNegativeFloat = 0


class TransportPlan(BaseModel):
    shipment_id: str
    legs: list[TransportLeg] = Field(min_length=1)
    total_cost: Decimal = Decimal("0")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    total_transit_seconds: float = 0
    reliability: float = Field(ge=0, le=1)


class OptimizationPolicy(BaseModel):
    """Business preferences translated into a deterministic optimization policy."""

    cost_weight: NonNegativeFloat = 1.0
    time_weight: NonNegativeFloat = 0.0
    reliability_weight: NonNegativeFloat = 0.0
    carbon_weight: NonNegativeFloat = 0.0
    consolidation_weight: NonNegativeFloat = 0.0
    minimize_transfers: bool = True
    allow_external_providers: bool = True


class OptimizationResult(BaseModel):
    plans: list[TransportPlan]
    objective_value: float
    feasible: bool
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
