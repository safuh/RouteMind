"""Deterministic shipment consolidation primitives."""

from .allocation import ConsolidationAllocation, SegmentAllocation, allocate_consolidation
from .engine import detect_shared_segments, evaluate_consolidation
from .grouping import (
    candidate_paths_by_shipment,
    generate_consolidation_groups,
    generate_shipment_groups,
    reject_unknown_shipments,
)
from .models import (
    ConsolidationOpportunity,
    ConsolidationRejection,
    ConsolidationRejectionReason,
    SharedTransportSegment,
)
from .time_windows import check_group_time_windows, check_path_time_window

__all__ = [
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
    "detect_shared_segments",
    "evaluate_consolidation",
    "generate_consolidation_groups",
    "generate_shipment_groups",
    "reject_unknown_shipments",
]
