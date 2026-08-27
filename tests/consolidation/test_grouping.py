from datetime import UTC, datetime
from decimal import Decimal

from routemind.consolidation.grouping import (
    candidate_paths_by_shipment,
    generate_consolidation_groups,
    generate_shipment_groups,
    reject_unknown_shipments,
)
from routemind.consolidation.models import ConsolidationRejectionReason
from routemind.domain.models import Location, Shipment
from routemind.paths.models import CandidatePath


def shipment(id_: str) -> Shipment:
    location = Location(id="NBO", name="Nairobi")
    from routemind.domain.models import Package
    return Shipment(
        id=id_, origin=location, destination=location,
        packages=[Package(id=f"P-{id_}", weight_kg=1, length_m=.1, width_m=.1, height_m=.1)],
        ready_at=datetime(2026, 8, 27, 7, tzinfo=UTC),
        deadline=datetime(2026, 8, 27, 20, tzinfo=UTC),
    )


def candidate(shipment_id: str, marker: str) -> CandidatePath:
    return CandidatePath(
        shipment_id=shipment_id, legs=(), total_cost=Decimal(marker), currency="KES",
        transit_seconds=0, waiting_seconds=0, number_of_transfers=0,
        reliability=1.0, modes=(), providers=(), capacity_utilization=0.0,
        deadline_feasible=True,
    )


def test_generate_shipment_groups_is_deterministic_and_unique():
    assert generate_shipment_groups(("A", "B", "C")) == (
        ("A", "B"), ("A", "C"), ("B", "C"), ("A", "B", "C")
    )


def test_group_size_bounds_are_respected():
    assert generate_shipment_groups(("A", "B", "C", "D"), min_group_size=2, max_group_size=2) == (
        ("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "D")
    )


def test_duplicate_ids_are_removed_without_changing_first_seen_order():
    assert generate_shipment_groups(("B", "A", "B"), min_group_size=2) == (("B", "A"),)


def test_candidate_paths_are_grouped_by_shipment():
    a1, a2, b1 = candidate("A", "10"), candidate("A", "20"), candidate("B", "30")
    assert candidate_paths_by_shipment((a1, b1, a2)) == {"A": (a1, a2), "B": (b1,)}


def test_consolidation_groups_expand_candidate_path_combinations():
    a1, a2, b1, b2 = candidate("A", "10"), candidate("A", "20"), candidate("B", "30"), candidate("B", "40")
    groups = generate_consolidation_groups(
        (a1, a2, b1, b2), {"A": shipment("A"), "B": shipment("B")}
    )
    assert groups == ((a1, b1), (a1, b2), (a2, b1), (a2, b2))


def test_missing_shipment_is_reported_structurally():
    rejections = reject_unknown_shipments(("A", "B"), {"A": shipment("A")})
    assert len(rejections) == 1
    assert rejections[0].reason == ConsolidationRejectionReason.UNKNOWN_SHIPMENT
