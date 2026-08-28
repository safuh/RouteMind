"""Generate deterministic logistics scenarios for development and benchmarking."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location,
    Package,
    PricingModel,
    Shipment,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)


class SyntheticScenario:
    """A complete generated logistics dataset."""

    def __init__(
        self,
        locations: list[Location],
        transport_options: list[TransportOption],
        shipments: list[Shipment],
    ) -> None:
        self.locations = locations
        self.transport_options = transport_options
        self.shipments = shipments


def generate_scenario(seed: int = 42, shipment_count: int = 20) -> SyntheticScenario:
    """Generate a small, reproducible Kenya-inspired transport network.

    The data is synthetic and intentionally avoids claiming to represent live
    carrier schedules or real prices. It is used to exercise RouteMind's
    domain, graph and optimization layers.
    """
    if shipment_count < 1:
        raise ValueError("shipment_count must be at least 1")

    rng = random.Random(seed)
    locations = _locations()
    location_by_id = {location.id: location for location in locations}
    now = datetime(2026, 8, 26, 6, tzinfo=UTC)

    options = _transport_options(rng, location_by_id, now)
    shipments = _shipments(rng, locations, now, shipment_count)
    return SyntheticScenario(locations, options, shipments)


def _locations() -> list[Location]:
    return [
        Location(id="nbo", name="Nairobi", latitude=-1.2864, longitude=36.8172),
        Location(id="nku", name="Nakuru", latitude=-0.3031, longitude=36.0800),
        Location(id="ksm", name="Kisumu", latitude=-0.0917, longitude=34.7680),
        Location(id="eld", name="Eldoret", latitude=0.5143, longitude=35.2698),
        Location(id="kak", name="Kakamega", latitude=0.2827, longitude=34.7519),
        Location(id="mmb", name="Mombasa", latitude=-4.0435, longitude=39.6682),
    ]


def _transport_options(
    rng: random.Random,
    locations: dict[str, Location],
    now: datetime,
) -> list[TransportOption]:
    # Each tuple is a synthetic service corridor, not a claim about a real provider.
    corridors = [
        ("nbo", "nku", TransportMode.TRUCK, 1200, 12, 7),
        ("nbo", "nku", TransportMode.BUS, 180, 3, 5),
        ("nku", "ksm", TransportMode.TRUCK, 900, 10, 6),
        ("nku", "ksm", TransportMode.BUS, 160, 2, 5),
        ("nku", "eld", TransportMode.TRUCK, 1000, 8, 5),
        ("nku", "eld", TransportMode.BUS, 180, 2, 4),
        ("eld", "kak", TransportMode.VAN, 350, 5, 3),
        ("nbo", "mmb", TransportMode.RAIL, 1500, 18, 8),
        ("mmb", "nbo", TransportMode.RAIL, 1500, 18, 8),
    ]

    options: list[TransportOption] = []
    for index, (origin, destination, mode, weight, hours, base_price) in enumerate(corridors):
        departure = now + timedelta(hours=rng.choice([1, 3, 6, 12]))
        arrival = departure + timedelta(hours=hours)
        volume = max(1.0, weight / 250)
        options.append(
            TransportOption(
                id=f"SVC-{index + 1:03d}",
                provider_id=f"PROV-{mode.value}",
                provider_name=f"Synthetic {mode.value.title()} Provider",
                mode=mode,
                origin=locations[origin],
                destination=locations[destination],
                capacity=TransportCapacity(
                    max_weight_kg=float(weight),
                    max_volume_m3=volume,
                ),
                schedules=[
                    TransportSchedule(
                        departure_at=departure,
                        arrival_at=arrival,
                    )
                ],
                price=TransportPrice(
                    model=PricingModel.PER_KG,
                    amount=Decimal(str(base_price)),
                    currency="KES",
                ),
                reliability=round(rng.uniform(0.82, 0.98), 3),
            )
        )

    # Final-mile motorcycle capacity makes the model genuinely multimodal.
    for index, destination in enumerate(["ksm", "eld", "kak"]):
        departure = now + timedelta(hours=2 + index)
        options.append(
            TransportOption(
                id=f"MOTO-{index + 1:03d}",
                provider_id="PROV-MOTO",
                provider_name="Synthetic Motorcycle Network",
                mode=TransportMode.MOTORCYCLE,
                origin=locations[destination],
                destination=locations[destination],
                capacity=TransportCapacity(max_weight_kg=30, max_volume_m3=0.15),
                schedules=[
                    TransportSchedule(
                        departure_at=departure,
                        arrival_at=departure + timedelta(minutes=45),
                    )
                ],
                price=TransportPrice(
                    model=PricingModel.FIXED,
                    amount=Decimal("250"),
                    currency="KES",
                ),
                reliability=0.93,
            )
        )
    return options


def _shipments(
    rng: random.Random,
    locations: list[Location],
    now: datetime,
    count: int,
) -> list[Shipment]:
    origin = next(location for location in locations if location.id == "nbo")
    destinations = [location for location in locations if location.id != "nbo"]
    shipments: list[Shipment] = []

    for index in range(count):
        destination = destinations[index % len(destinations)]
        weight = round(rng.uniform(1, 25), 2)
        side = round(rng.uniform(0.15, 0.55), 2)
        ready_at = now + timedelta(minutes=rng.randint(0, 240))
        shipments.append(
            Shipment(
                id=f"SHIP-{index + 1:04d}",
                origin=origin,
                destination=destination,
                packages=[
                    Package(
                        id=f"PKG-{index + 1:04d}",
                        weight_kg=weight,
                        length_m=side,
                        width_m=side,
                        height_m=side,
                    )
                ],
                ready_at=ready_at,
                deadline=ready_at + timedelta(hours=rng.choice([12, 18, 24, 36])),
                priority=rng.choice([0, 0, 0, 1, 2]),
            )
        )
    return shipments
