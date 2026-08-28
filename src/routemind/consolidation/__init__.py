"""Deterministic shipment consolidation primitives."""

from .allocation import ConsolidationAllocation, SegmentAllocation, allocate_consolidation
from .engine import detect_shared_segments, evaluate_consolidation
from .grouping import (
    candidate_paths_by_shipment,
    generate_consolidation_groups,
    generate_shipment_groups,
    reject_unknown_shipments,
)
from .hub_spoke import common_prefix_option_ids, generate_hub_spoke_groups
from .models import (
    ConsolidationOpportunity,
    ConsolidationRejection,
    ConsolidationRejectionReason,
    SharedTransportSegment,
)
from .reservation import (
    CapacityReservation,
    CapacityReservationLedger,
    CapacityReservationRejection,
    CapacityReservationResult,
    reserve_opportunities,
)
from .time_windows import check_group_time_windows, check_path_time_window

__all__ = [
    "CapacityReservation",
    "CapacityReservationLedger",
    "CapacityReservationRejection",
    "CapacityReservationResult",
    "ConsolidationAllocation",
    "ConsolidationOpportunity",
    "ConsolidationRejection",
    "ConsolidationRejectionReason",
    "SegmentAllocation",
    "SharedTransportSegment",
    "allocate_consolidation",
    "candidate_paths_by_shipment",
    "check_group_time_windows",
    "check_path_time_window",
    "common_prefix_option_ids",
    "detect_shared_segments",
    "evaluate_consolidation",
    "generate_consolidation_groups",
    "generate_hub_spoke_groups",
    "generate_shipment_groups",
    "reject_unknown_shipments",
    "reserve_opportunities",
]
