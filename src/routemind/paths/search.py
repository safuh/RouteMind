"""Time-dependent, capacity-aware candidate path discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from heapq import heappop, heappush

from routemind.domain.models import Shipment, TransportLeg, TransportOption
from routemind.domain.validation import transport_can_carry_shipment


@dataclass(frozen=True, slots=True)
class PathSearchConfig:
    max_legs: int = 4
    max_candidates: int = 10
    min_reliability: float = 0.0


@dataclass(frozen=True, slots=True)
class _State:
    location_id: str
    ready_at: datetime
    legs: tuple[TransportLeg, ...]
    cost: float
    reliability: float


class PathSearchEngine:
    """Enumerate feasible transportation strategies for one shipment.

    This is a candidate generator, not the final optimizer. It keeps multiple
    feasible alternatives so consolidation and optimization can choose later.
    """

    def __init__(self, options: list[TransportOption], config: PathSearchConfig | None = None) -> None:
        self._config = config or PathSearchConfig()
        self._by_origin: dict[str, list[TransportOption]] = {}
        for option in options:
            if option.available:
                self._by_origin.setdefault(option.origin.id, []).append(option)

    def discover(self, shipment: Shipment) -> list[TransportLeg]:
        """Return the cheapest-first feasible candidate, or an empty list."""
        paths = self.discover_paths(shipment)
        return list(paths[0]) if paths else []

    def discover_paths(self, shipment: Shipment) -> list[tuple[TransportLeg, ...]]:
        """Discover feasible direct and multi-leg paths in cost order."""
        if not shipment_timing_ok(shipment):
            return []

        queue: list[tuple[float, int, _State]] = []
        counter = 0
        heappush(queue, (0.0, counter, _State(shipment.origin.id, shipment.ready_at, (), 0.0, 1.0)))
        candidates: list[tuple[TransportLeg, ...]] = []
        seen: set[tuple[str, datetime, tuple[str, ...]]] = set()

        while queue and len(candidates) < self._config.max_candidates:
            _, _, state = heappop(queue)
            if state.location_id == shipment.destination.id and state.legs:
                candidates.append(state.legs)
                continue
            if len(state.legs) >= self._config.max_legs:
                continue

            used_option_ids = {leg.option_id for leg in state.legs}
            for option in self._by_origin.get(state.location_id, []):
                # An option cannot be reused within one candidate. This prevents
                # cycles, including self-loop/final-mile services.
                if option.id in used_option_ids:
                    continue
                if not transport_can_carry_shipment(shipment, option):
                    continue

                for schedule in option.schedules:
                    if schedule.departure_at < state.ready_at:
                        continue
                    if schedule.arrival_at <= schedule.departure_at:
                        continue
                    if shipment.deadline and schedule.arrival_at > shipment.deadline:
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
                    counter += 1
                    cost = state.cost + float(option.price.amount)
                    priority = cost + schedule.transit_seconds / 3600 * 0.01
                    heappush(
                        queue,
                        (priority, counter, _State(option.destination.id, schedule.arrival_at, state.legs + (leg,), cost, reliability)),
                    )

        return candidates


def shipment_timing_ok(shipment: Shipment) -> bool:
    return shipment.deadline is None or shipment.deadline > shipment.ready_at
