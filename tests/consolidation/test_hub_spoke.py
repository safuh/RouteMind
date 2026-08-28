from datetime import UTC, datetime, timedelta
from decimal import Decimal

from routemind.consolidation.hub_spoke import common_prefix_option_ids, generate_hub_spoke_groups
from routemind.domain.models import Location, TransportLeg, TransportMode
from routemind.paths.models import CandidatePath


NBO = Location(id="NBO", name="Nairobi")
KLA = Location(id="KLA", name="Kampala")
KGL = Location(id="KGL", name="Kigali")
GOM = Location(id="GOM", name="Goma")
T0 = datetime(2026, 8, 28, 8, tzinfo=UTC)
T1 = T0 + timedelta(hours=4)
T2 = T1 + timedelta(hours=4)


def path(shipment_id: str, downstream: str, *, shared_option: str = "BUS-1") -> CandidatePath:
    destination = KGL if downstream == "KGL" else GOM
    return CandidatePath(
        shipment_id=shipment_id,
        legs=(
            TransportLeg(
                option_id=shared_option,
                origin=NBO,
                destination=KLA,
                departure_at=T0,
                arrival_at=T1,
                allocated_weight_kg=1,
            ),
            TransportLeg(
                option_id=f"VAN-{downstream}",
                origin=KLA,
                destination=destination,
                departure_at=T1 + timedelta(minutes=30),
                arrival_at=T2,
                allocated_weight_kg=1,
            ),
        ),
        total_cost=Decimal("10"),
        currency="KES",
        transit_seconds=14400,
        waiting_seconds=1800,
        number_of_transfers=1,
        reliability=0.9,
        modes=(TransportMode.BUS, TransportMode.VAN),
        providers=("P1", "P2"),
        capacity_utilization=0.1,
        deadline_feasible=True,
    )


def test_common_prefix_requires_exact_scheduled_leg_identity():
    a = path("A", "KGL")
    b = path("B", "GOM")
    assert common_prefix_option_ids((a, b)) == ("BUS-1",)


def test_hub_spoke_group_detects_shared_prefix_then_branch():
    a = path("A", "KGL")
    b = path("B", "GOM")
    assert generate_hub_spoke_groups((a, b)) == ((a, b),)


def test_same_complete_path_is_not_hub_spoke():
    a = path("A", "KGL")
    b = path("B", "KGL")
    assert generate_hub_spoke_groups((a, b)) == ()


def test_different_shared_schedule_does_not_create_group():
    a = path("A", "KGL", shared_option="BUS-1")
    b = path("B", "GOM", shared_option="BUS-2")
    assert generate_hub_spoke_groups((a, b)) == ()
