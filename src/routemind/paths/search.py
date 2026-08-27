"""Time-dependent, capacity-aware candidate path discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from heapq import heappop, heappush

from routemind.domain.models import (
    Shipment,
    TransportLeg,
    TransportMode,
    TransportOption,
    TransportSchedule,
)
from routemind.domain.validation import transport_can_carry_shipment

from .dominance import remove_dominated_paths
from .models import CandidatePath


@dataclass(frozen=True, slots=True)
class PathSearchConfig:
    max_legs: int = 4
    max_candidates: int = 10
    min_reliability: float = 0.0
    min_transfer_seconds: int = 0
    transfer_handling_cost: Decimal = Decimal("0")
    max_transfers: int | None = None
    allowed_modes: frozenset[TransportMode] | None = None
    excluded_modes: frozenset[TransportMode] = frozenset()
    allowed_provider_ids: frozenset[str] | None = None
    excluded_provider_ids: frozenset[str] = frozenset()
    remove_dominated: bool = True


@dataclass(frozen=True, slots=True)
class _State:
    location_id: str
    ready_at: datetime
    legs: tuple[TransportLeg, ...]
    cost: Decimal
    reliability: float
    transit_seconds: float
    waiting_seconds: float
    capacity_utilization: float


class PathSearchEngine:
    """Enumerate feasible transportation strategies for one shipment.

    This is a candidate generator, not the final optimizer. It preserves
    multiple feasible alternatives and applies Pareto filtering only after
    candidate generation.
    """

    def __init__(self, options: list[TransportOption], config: PathSearchConfig | None = None) -> None:
        self._config = config or PathSearchConfig()
        self._by_origin: dict[str, list[TransportOption]] = {}
        self._options: dict[str, TransportOption] = {}
        for option in options:
            if option.id in self._options:
                raise ValueError(f"Duplicate transport option: {option.id}")
            self._options[option.id] = option
            if option.available:
                self._by_origin.setdefault(option.origin.id, []).append(option)

    def discover(self, shipment: Shipment) -> CandidatePath | None:
        """Return the first retained candidate, or ``None`` if none exists."""
        paths = self.discover_paths(shipment)
        return paths[0] if paths else None

    def discover_paths(self, shipment: Shipment) -> list[CandidatePath]:
        """Discover multiple feasible direct and multi-leg candidate paths."""
        if not shipment_timing_ok(shipment):
            return []

        queue: list[tuple[Decimal, int, _State]] = []
        counter = 0
        heappush(
            queue,
            (
                Decimal("0"),
                counter,
                _State(shipment.origin.id, shipment.ready_at, (), Decimal("0"), 1.0, 0.0, 0.0, 0.0),
            ),
        )
        candidates: list[CandidatePath] = []
        seen: set[tuple[str, datetime, tuple[str, ...]]] = set()

        while queue and len(candidates) < self._config.max_candidates:
            _, _, state = heappop(queue)
            if state.location_id == shipment.destination.id and state.legs:
                candidates.append(self._build_candidate(shipment, state))
                continue
            if len(state.legs) >= self._config.max_legs:
                continue

            used_option_ids = {leg.option_id for leg in state.legs}
            for option in self._by_origin.get(state.location_id, []):
                if option.id in used_option_ids or not self._option_allowed(option):
                    continue
                if not self._cargo_compatible(shipment, option):
                    continue
                if self._config.max_transfers is not None and len(state.legs) >= self._config.max_transfers + 1:
                    continue

                for schedule in option.schedules:
                    if not self._schedule_feasible(shipment, state, option, schedule):
                        continue

                    available_weight = schedule.available_weight_kg
                    available_volume = schedule.available_volume_m3
                    if not transport_can_carry_shipment(
                        shipment,
                        option,
                        available_weight_kg=available_weight,
                        available_volume_m3=available_volume,
                    ):
                        continue

                    reliability = state.reliability * option.reliability
                    if reliability < self._config.min_reliability:
                        continue

                    leg = TransportLeg(
                        option_id=option.id,
                        origin=option.origin,
                        destination=option.destination,
                        departure_at=schedule.departure_at,
                        arrival_at=schedule.arrival_at,
                        allocated_weight_kg=shipment.weight_kg,
                        allocated_volume_m3=shipment.volume_m3,
                    )
                    ids = tuple(item.option_id for item in state.legs) + (option.id,)
                    key = (option.destination.id, schedule.arrival_at, ids)
                    if key in seen:
                        continue
                    seen.add(key)

                    weight_capacity = min(
                        option.capacity.max_weight_kg,
                        available_weight if available_weight is not None else option.capacity.max_weight_kg,
                    )
                    utilization = shipment.weight_kg / weight_capacity
                    if option.capacity.max_volume_m3 is not None:
                        volume_capacity = min(
                            option.capacity.max_volume_m3,
                            available_volume if available_volume is not None else option.capacity.max_volume_m3,
                        )
                        utilization = max(utilization, shipment.volume_m3 / volume_capacity)

                    waiting = (schedule.departure_at - state.ready_at).total_seconds()
                    if waiting < 0:
                        continue

                    cost = state.cost + self._price_for_shipment(option, shipment)
                    if state.legs:
                        cost += self._config.transfer_handling_cost

                    next_state = _State(
                        option.destination.id,
                        schedule.arrival_at,
                        state.legs + (leg,),
                        cost,
                        reliability,
                        state.transit_seconds + schedule.transit_seconds,
                        state.waiting_seconds + waiting,
                        max(state.capacity_utilization, utilization),
                    )
                    counter += 1
                    priority = cost + Decimal(str(schedule.transit_seconds / 3600 * 0.01))
                    heappush(queue, (priority, counter, next_state))

        if self._config.remove_dominated:
            return remove_dominated_paths(candidates)
        return candidates

    def _build_candidate(self, shipment: Shipment, state: _State) -> CandidatePath:
        return CandidatePath(
            shipment_id=shipment.id,
            legs=state.legs,
            total_cost=state.cost,
            currency=self._currency_for(state.legs),
            transit_seconds=state.transit_seconds,
            waiting_seconds=state.waiting_seconds,
            number_of_transfers=max(0, len(state.legs) - 1),
            reliability=state.reliability,
            modes=tuple(self._options[leg.option_id].mode for leg in state.legs),
            providers=tuple(self._options[leg.option_id].provider_id for leg in state.legs),
            capacity_utilization=state.capacity_utilization,
            deadline_feasible=shipment.deadline is None or state.legs[-1].arrival_at <= shipment.deadline,
            metadata={
                "search": "time_dependent",
                "pricing": "shipment_evaluable",
            },
        )

    def _currency_for(self, legs: tuple[TransportLeg, ...]) -> str:
        currencies = {self._options[leg.option_id].price.currency for leg in legs}
        if len(currencies) != 1:
            raise ValueError("Candidate paths cannot combine transport prices in different currencies")
        return currencies.pop()

    def _option_allowed(self, option: TransportOption) -> bool:
        if option.mode in self._config.excluded_modes:
            return False
        if self._config.allowed_modes is not None and option.mode not in self._config.allowed_modes:
            return False
        if option.provider_id in self._config.excluded_provider_ids:
            return False
        if self._config.allowed_provider_ids is not None and option.provider_id not in self._config.allowed_provider_ids:
            return False
        return True

    @staticmethod
    def _cargo_compatible(shipment: Shipment, option: TransportOption) -> bool:
        restrictions = {item.lower() for item in option.restrictions}
        if "no_fragile" in restrictions and any(package.fragile for package in shipment.packages):
            return False
        if "no_temperature_controlled" in restrictions and any(
            package.temperature_controlled for package in shipment.packages
        ):
            return False
        if "fragile_only" in restrictions and not all(package.fragile for package in shipment.packages):
            return False
        if "temperature_controlled_only" in restrictions and not all(
            package.temperature_controlled for package in shipment.packages
        ):
            return False
        return True

    def _schedule_feasible(
        self,
        shipment: Shipment,
        state: _State,
        option: TransportOption,
        schedule: TransportSchedule,
    ) -> bool:
        if schedule.departure_at < state.ready_at:
            return False
        if schedule.arrival_at <= schedule.departure_at:
            return False
        if shipment.deadline and schedule.arrival_at > shipment.deadline:
            return False
        if state.legs:
            minimum_departure = state.legs[-1].arrival_at + timedelta(seconds=self._config.min_transfer_seconds)
            if schedule.departure_at < minimum_departure:
                return False
        return self._price_supported(option)

    @staticmethod
    def _price_supported(option: TransportOption) -> bool:
        # Per-km pricing cannot be evaluated correctly until transport distance
        # is attached to the service/graph model. It is therefore excluded
        # rather than silently treating a rate as a total price.
        return option.price.model.value in {"fixed", "per_kg", "per_volume", "quoted"}

    @staticmethod
    def _price_for_shipment(option: TransportOption, shipment: Shipment) -> Decimal:
        model = option.price.model.value
        amount = option.price.amount
        if model in {"fixed", "quoted"}:
            return amount
        if model == "per_kg":
            return amount * Decimal(str(shipment.weight_kg))
        if model == "per_volume":
            return amount * Decimal(str(shipment.volume_m3))
        raise ValueError(f"Unsupported path-search pricing model: {model}")


def shipment_timing_ok(shipment: Shipment) -> bool:
    return shipment.deadline is None or shipment.deadline > shipment.ready_at
