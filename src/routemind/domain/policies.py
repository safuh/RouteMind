"""Pure domain policies used by optimization components."""

from __future__ import annotations

from decimal import Decimal

from routemind.domain.models import Package, Shipment, TransportOption


def shipment_fits_capacity(shipment: Shipment, option: TransportOption) -> bool:
    """Return whether the shipment fits the resource's declared capacity."""
    capacity = option.capacity
    if shipment.weight_kg > capacity.max_weight_kg:
        return False
    if capacity.max_volume_m3 is not None and shipment.volume_m3 > capacity.max_volume_m3:
        return False

    for package in shipment.packages:
        if capacity.max_length_m is not None and package.length_m > capacity.max_length_m:
            return False
        if capacity.max_width_m is not None and package.width_m > capacity.max_width_m:
            return False
        if capacity.max_height_m is not None and package.height_m > capacity.max_height_m:
            return False

    return True


def package_is_compatible(package: Package, option: TransportOption) -> bool:
    """Check restrictions declared by a transport option against one package."""
    restrictions = option.restrictions
    if package.fragile and "no_fragile" in restrictions:
        return False
    if package.temperature_controlled and "no_temperature_controlled" in restrictions:
        return False
    return True


def shipment_is_compatible(shipment: Shipment, option: TransportOption) -> bool:
    return all(package_is_compatible(package, option) for package in shipment.packages)


def option_is_feasible(shipment: Shipment, option: TransportOption) -> bool:
    """Apply basic feasibility checks before an option enters optimization."""
    if not option.available:
        return False
    if option.origin.id != shipment.origin.id or option.destination.id != shipment.destination.id:
        return False
    return shipment_fits_capacity(shipment, option) and shipment_is_compatible(shipment, option)


def calculate_transport_price(shipment: Shipment, option: TransportOption) -> Decimal:
    """Calculate the shipment charge for a single direct transport option.

    Route-distance-dependent pricing is intentionally deferred until the graph layer
    supplies the relevant segment distance.
    """
    base = option.price.amount
    model = option.price.model
    if model.value == "fixed" or model.value == "quoted":
        return base
    if model.value == "per_kg":
        return base * Decimal(str(shipment.weight_kg))
    if model.value == "per_volume":
        return base * Decimal(str(shipment.volume_m3))
    raise ValueError(f"Pricing model {model.value!r} requires route distance context")
