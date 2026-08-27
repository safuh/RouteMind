"""Small deterministic benchmark scenarios for candidate path discovery.

These benchmarks validate search behavior, not real-world transport data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.domain.models import (
    Location,
    Package,
    Shipment,
    TransportCapacity,
    TransportMode,
    TransportOption,
    TransportPrice,
    TransportSchedule,
)

from .search import PathSearchConfig, PathSearchEngine


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    name: str
    feasible: bool
    candidate_count: int
    best_cost: Decimal | None
    best_elapsed_seconds: float | None
    diagnostics: dict[str, float]


def run_benchmark(name: str) -> BenchmarkResult:
    scenarios = {
        "cheapest_route": _cheapest_route,
        "fastest_route": _fastest_route,
        "deadline_eliminates_cheap": _deadline_eliminates_cheap,
        "capacity_eliminates_direct": _capacity_eliminates_direct,
        "multimodal_beats_direct": _multimodal_beats_direct,
        "reliability_tradeoff": _reliability_tradeoff,
        "transfer_cost_tradeoff": _transfer_cost_tradeoff,
        "no_feasible_route": _no_feasible_route,
    }
    try:
        options, shipment = scenarios[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown benchmark scenario: {name}") from exc

    engine = PathSearchEngine(options, PathSearchConfig(remove_dominated=False, max_candidates=20))
    paths = engine.discover_paths(shipment)
    best_cost = min((path.total_cost for path in paths), default=None)
    best_elapsed = min((path.elapsed_seconds for path in paths), default=None)
    return BenchmarkResult(name, bool(paths), len(paths), best_cost, best_elapsed, engine.last_diagnostics.by_reason() | engine.last_diagnostics.as_metrics())


def run_all_benchmarks() -> list[BenchmarkResult]:
    names = [
        "cheapest_route", "fastest_route", "deadline_eliminates_cheap",
        "capacity_eliminates_direct", "multimodal_beats_direct",
        "reliability_tradeoff", "transfer_cost_tradeoff", "no_feasible_route",
    ]
    return [run_benchmark(name) for name in names]


def _base() -> tuple[Location, Location, Location, datetime, Shipment]:
    n = Location(id="NBO", name="Nairobi")
    k = Location(id="NKR", name="Nakuru")
    e = Location(id="ELD", name="Eldoret")
    ready = datetime(2026, 8, 27, 8, tzinfo=UTC)
    shipment = Shipment(
        id="B1", origin=n, destination=e,
        packages=[Package(id="PKG", weight_kg=10, length_m=1, width_m=1, height_m=0.1)],
        ready_at=ready, deadline=ready + timedelta(hours=24),
    )
    return n, k, e, ready, shipment


def _option(i: str, origin: Location, destination: Location, departure: datetime, hours: int, price: str, *, weight: float = 100, reliability: float = .95) -> TransportOption:
    return TransportOption(
        id=i, provider_id=i, provider_name=i, mode=TransportMode.BUS,
        origin=origin, destination=destination,
        capacity=TransportCapacity(max_weight_kg=weight),
        schedules=[TransportSchedule(departure_at=departure, arrival_at=departure + timedelta(hours=hours))],
        price=TransportPrice(model="fixed", amount=Decimal(price), currency="KES"),
        reliability=reliability,
    )


def _cheapest_route():
    n, _, e, t, s = _base()
    return [_option("CHEAP", n, e, t, 8, "500"), _option("EXP", n, e, t, 5, "1000")], s


def _fastest_route():
    n, _, e, t, s = _base()
    return [_option("SLOW", n, e, t, 8, "500"), _option("FAST", n, e, t, 5, "1000")], s


def _deadline_eliminates_cheap():
    n, _, e, t, s = _base()
    s = s.model_copy(update={"deadline": t + timedelta(hours=6)})
    return [_option("CHEAP", n, e, t, 8, "500"), _option("FAST", n, e, t, 5, "1000")], s


def _capacity_eliminates_direct():
    n, k, e, t, s = _base()
    return [_option("DIRECT", n, e, t, 8, "700", weight=5), _option("N-K", n, k, t, 3, "300"), _option("K-E", k, e, t + timedelta(hours=4), 3, "300")], s


def _multimodal_beats_direct():
    n, k, e, t, s = _base()
    return [_option("DIRECT", n, e, t, 10, "1200"), _option("N-K", n, k, t, 3, "300"), _option("K-E", k, e, t + timedelta(hours=3), 3, "300")], s


def _reliability_tradeoff():
    n, _, e, t, s = _base()
    return [_option("CHEAP", n, e, t, 6, "500", reliability=.70), _option("RELIABLE", n, e, t, 7, "700", reliability=.99)], s


def _transfer_cost_tradeoff():
    n, k, e, t, s = _base()
    return [_option("DIRECT", n, e, t, 8, "900"), _option("N-K", n, k, t, 2, "300"), _option("K-E", k, e, t + timedelta(hours=2), 2, "300")], s


def _no_feasible_route():
    n, _, e, t, s = _base()
    return [_option("TOO_SMALL", n, e, t, 4, "300", weight=5)], s
