"""Time-dependent, capacity-aware candidate path discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from heapq import heappop, heappush

from routemind.domain.models import Shipment, TransportLeg, TransportMode, TransportOption, TransportSchedule
from routemind.domain.validation import transport_can_carry_shipment

from .diagnostics import PathRejection, PathSearchDiagnostics, RejectionReason
from .dominance import remove_dominated_paths
from .models import CandidatePath


@dataclass(frozen=True, slots=True)
class PathSearchConfig:
    max_legs: int = 4
    max_candidates: int = 10
    max_expansions: int = 10_000
    max_diagnostics: int = 1_000
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
    ready_at: object
    legs: tuple[TransportLeg, ...]
    cost: Decimal
    reliability: float
    transit_seconds: float
    waiting_seconds: float
    capacity_utilization: float
    emissions_kg_co2e: float


class PathSearchEngine:
    """Enumerate feasible transportation strategies for one shipment."""

    def __init__(self, options: list[TransportOption], config: PathSearchConfig | None = None) -> None:
        self._config = config or PathSearchConfig()
        self._by_origin: dict[str, list[TransportOption]] = {}
        self._options: dict[str, TransportOption] = {}
        for option in options:
            if option.id in self._options:
                raise ValueError(f"Duplicate transport option: {option.id}")
            self._options[option.id] = option
            self._by_origin.setdefault(option.origin.id, []).append(option)
        self.last_diagnostics = PathSearchDiagnostics(expansions=0, generated_candidates=0, retained_candidates=0)

    def discover(self, shipment: Shipment) -> CandidatePath | None:
        paths = self.discover_paths(shipment)
        return paths[0] if paths else None

    def discover_paths(self, shipment: Shipment) -> list[CandidatePath]:
        rejected: list[PathRejection] = []
        generated = 0
        if not shipment_timing_ok(shipment):
            self._record(rejected, PathRejection(reason=RejectionReason.INVALID_SHIPMENT_TIMING, message="Shipment deadline must be after readiness"))
            self._finish(0, generated, [], rejected, False)
            return []

        queue: list[tuple[Decimal, int, _State]] = []
        counter = 0
        initial = _State(
            shipment.origin.id,
            shipment.ready_at,
            (),
            Decimal("0"),
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
        heappush(queue, (Decimal("0"), counter, initial))
        candidates: list[CandidatePath] = []
        seen: set[tuple[str, object, tuple[str, ...]]] = set()
        expansions = 0

        while queue and expansions < self._config.max_expansions:
            _, _, state = heappop(queue)
            expansions += 1
            if state.location_id == shipment.destination.id and state.legs:
                candidates.append(self._build_candidate(shipment, state))
                generated += 1
                continue
            if len(state.legs) >= self._config.max_legs:
                continue

            used_option_ids = {leg.option_id for leg in state.legs}
            for option in self._by_origin.get(state.location_id, []):
                if option.id in used_option_ids:
                    self._record(rejected, PathRejection(option_id=option.id, reason=RejectionReason.CYCLE, message="Transport option already occurs in this path"))
                    continue
                policy_reason = self._policy_rejection(option)
                if policy_reason:
                    self._record(rejected, PathRejection(option_id=option.id, reason=policy_reason[0], message=policy_reason[1]))
                    continue
                if not option.available:
                    self._record(rejected, PathRejection(option_id=option.id, reason=RejectionReason.UNAVAILABLE, message="Transport option is unavailable"))
                    continue
                if not self._cargo_compatible(shipment, option):
                    self._record(rejected, PathRejection(option_id=option.id, reason=RejectionReason.CARGO_RESTRICTION, message="Shipment is incompatible with transport restrictions"))
                    continue
                if self._config.max_transfers is not None and len(state.legs) - 1 >= self._config.max_transfers:
                    self._record(rejected, PathRejection(option_id=option.id, reason=RejectionReason.MAX_TRANSFERS, message="Maximum transfer policy reached"))
                    continue
                if not self._price_supported(option):
                    self._record(rejected, PathRejection(option_id=option.id, reason=RejectionReason.UNSUPPORTED_PRICING, message=f"Pricing model {option.price.model.value} requires distance_km"))
                    continue

                for schedule_index, schedule in enumerate(option.schedules):
                    reason = self._schedule_rejection(shipment, state, schedule)
                    if reason:
                        self._record(rejected, PathRejection(option_id=option.id, schedule_departure=schedule.departure_at.isoformat(), reason=reason[0], message=reason[1]))
                        continue
                    if not transport_can_carry_shipment(shipment, option, available_weight_kg=schedule.available_weight_kg, available_volume_m3=schedule.available_volume_m3):
                        reason = RejectionReason.WEIGHT_CAPACITY if schedule.available_weight_kg is not None and shipment.weight_kg > schedule.available_weight_kg else RejectionReason.VOLUME_CAPACITY
                        self._record(rejected, PathRejection(option_id=option.id, schedule_departure=schedule.departure_at.isoformat(), reason=reason, message="Shipment exceeds schedule-specific capacity"))
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
                    arrival = schedule.arrival_at
                    if state.legs and arrival < state.ready_at:
                        continue
                    transfer_wait = max(0.0, (schedule.departure_at - state.ready_at).total_seconds()) if state.legs else max(0.0, (schedule.departure_at - shipment.ready_at).total_seconds())
                    transit = state.transit_seconds + schedule.transit_seconds
                    waiting = state.waiting_seconds + transfer_wait
                    cost = state.cost + self._leg_cost(shipment, option) + (self._config.transfer_handling_cost if state.legs else Decimal("0"))
                    reliability = state.reliability * option.reliability
                    emissions = state.emissions_kg_co2e + self._leg_emissions(option, leg)
                    utilization = max(
                        state.capacity_utilization,
                        shipment.weight_kg / option.capacity.max_weight_kg,
                        shipment.volume_m3 / option.capacity.max_volume_m3 if option.capacity.max_volume_m3 else 0.0,
                    )
                    next_state = _State(option.destination.id, arrival, state.legs + (leg,), cost, reliability, transit, waiting, utilization, emissions)
                    key = (next_state.location_id, next_state.ready_at, tuple(item.option_id for item in next_state.legs))
                    if key not in seen:
                        seen.add(key)
                        counter += 1
                        heappush(queue, (next_state.cost, counter, next_state))

        retained = remove_dominated_paths(candidates) if self._config.remove_dominated else candidates
        retained = retained[: self._config.max_candidates]
        self._finish(expansions, generated, retained, rejected, bool(queue))
        return retained

    def _build_candidate(self, shipment: Shipment, state: _State) -> CandidatePath:
        return CandidatePath(
            shipment_id=shipment.id,
            legs=state.legs,
            total_cost=state.cost,
            currency=self._options[state.legs[0].option_id].price.currency,
            transit_seconds=state.transit_seconds,
            waiting_seconds=state.waiting_seconds,
            number_of_transfers=max(0, len(state.legs) - 1),
            reliability=state.reliability,
            modes=tuple(self._options[leg.option_id].mode for leg in state.legs),
            providers=tuple(self._options[leg.option_id].provider_id for leg in state.legs),
            capacity_utilization=min(1.0, state.capacity_utilization),
            deadline_feasible=shipment.deadline is None or state.ready_at <= shipment.deadline,
            emissions_kg_co2e=state.emissions_kg_co2e,
        )

    def _policy_rejection(self, option: TransportOption) -> tuple[RejectionReason, str] | None:
        if self._config.allowed_modes is not None and option.mode not in self._config.allowed_modes:
            return RejectionReason.MODE_POLICY, "Transport mode is not allowed"
        if option.mode in self._config.excluded_modes:
            return RejectionReason.MODE_POLICY, "Transport mode is excluded"
        if self._config.allowed_provider_ids is not None and option.provider_id not in self._config.allowed_provider_ids:
            return RejectionReason.PROVIDER_POLICY, "Provider is not allowed"
        if option.provider_id in self._config.excluded_provider_ids:
            return RejectionReason.PROVIDER_POLICY, "Provider is excluded"
        if option.reliability < self._config.min_reliability:
            return RejectionReason.RELIABILITY, "Provider reliability is below policy threshold"
        return None

    def _cargo_compatible(self, shipment: Shipment, option: TransportOption) -> bool:
        return all(transport_can_carry_shipment(shipment, option) for _ in (0,))

    def _price_supported(self, option: TransportOption) -> bool:
        return option.price.model.value not in {"per_km", "per_kg_km"} or option.distance_km is not None

    def _leg_cost(self, shipment: Shipment, option: TransportOption) -> Decimal:
        amount = option.price.amount
        model = option.price.model.value
        if model in {"fixed", "quoted"}:
            return amount
        if model == "per_kg":
            return amount * Decimal(str(shipment.weight_kg))
        if model == "per_volume":
            return amount * Decimal(str(shipment.volume_m3))
        if option.distance_km is None:
            raise ValueError(f"distance_km is required for {model} pricing on {option.id!r}")
        distance = Decimal(str(option.distance_km))
        if model == "per_km":
            return amount * distance
        if model == "per_kg_km":
            return amount * distance * Decimal(str(shipment.weight_kg))
        raise ValueError(f"Unsupported pricing model: {model}")

    def _leg_emissions(self, option: TransportOption, leg: TransportLeg) -> float:
        if option.carbon_kg_co2e_per_km is None or option.distance_km is None:
            return 0.0
        return option.carbon_kg_co2e_per_km * option.distance_km

    def _schedule_rejection(self, shipment: Shipment, state: _State, schedule: TransportSchedule) -> tuple[RejectionReason, str] | None:
        earliest = max(shipment.ready_at, state.ready_at)
        if schedule.departure_at < earliest:
            return RejectionReason.READINESS, "Shipment or transfer is not ready before departure"
        if shipment.deadline is not None and schedule.arrival_at > shipment.deadline:
            return RejectionReason.DEADLINE, "Transport schedule arrives after shipment deadline"
        if state.legs and (schedule.departure_at - state.ready_at).total_seconds() < self._config.min_transfer_seconds:
            return RejectionReason.TRANSFER_TIME, "Transfer wait is below configured minimum"
        return None

    def _record(self, rejected: list[PathRejection], item: PathRejection) -> None:
        if len(rejected) < self._config.max_diagnostics:
            rejected.append(item)

    def _finish(self, expansions: int, generated: int, retained: list[CandidatePath], rejected: list[PathRejection], exhausted: bool) -> None:
        self.last_diagnostics = PathSearchDiagnostics(
            expansions=expansions,
            generated_candidates=generated,
            retained_candidates=len(retained),
            rejected=rejected,
            expansion_budget_exhausted=exhausted,
        )


def shipment_timing_ok(shipment: Shipment) -> bool:
    return shipment.deadline is None or shipment.deadline > shipment.ready_at
