from datetime import datetime, timezone
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
)
from routemind.domain.policies import (
    calculate_transport_price,
    option_is_feasible,
    shipment_fits_capacity,
)


UTC = timezone.utc


def location(identifier: str, name: str) -> Location:
    return Location(id=identifier, name=name)


def shipment(weight: float = 10.0) -> Shipment:
    return Shipment(
        id="S-1",
        origin=location("NBO", "Nairobi"),
        destination=location("KSM", "Kisumu"),
        packages=[
            Package(
                id="P-1",
                weight_kg=weight,
                length_m=0.4,
                width_m=0.3,
                height_m=0.2,
            )
        ],
        ready_at=datetime(2026, 8, 26, 8, tzinfo=UTC),
    )


def transport(max_weight: float = 100.0) -> TransportOption:
    return TransportOption(
        id="T-1",
        provider_id="P-1",
        provider_name="Example Carrier",
        mode=TransportMode.BUS,
        origin=location("NBO", "Nairobi"),
        destination=location("KSM", "Kisumu"),
        capacity=TransportCapacity(max_weight_kg=max_weight, max_volume_m3=10),
        price=TransportPrice(
            model=PricingModel.PER_KG,
            amount=Decimal("50"),
            currency="KES",
        ),
        reliability=0.95,
    )


def test_package_volume_accounts_for_quantity() -> None:
    package = Package(
        id="P",
        weight_kg=2,
        length_m=1,
        width_m=0.5,
        height_m=0.2,
        quantity=3,
    )
    assert package.volume_m3 == 0.3


def test_shipment_aggregates_weight_and_volume() -> None:
    result = shipment()
    assert result.weight_kg == 10
    assert result.volume_m3 == 0.024


def test_capacity_rejects_overweight_shipment() -> None:
    assert not shipment_fits_capacity(shipment(101), transport(100))


def test_option_feasibility_accepts_matching_direct_service() -> None:
    assert option_is_feasible(shipment(), transport())


def test_direct_per_kg_price_is_calculated() -> None:
    assert calculate_transport_price(shipment(10), transport()) == Decimal("500")
