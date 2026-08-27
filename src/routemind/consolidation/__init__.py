"""Deterministic shipment consolidation primitives."""

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

__all__ = [
    "ConsolidationOpportunity",
    "ConsolidationRejection",
    "ConsolidationRejectionReason",
    "SharedTransportSegment",
    "candidate_paths_by_shipment",
    "detect_shared_segments",
    "evaluate_consolidation",
    "generate_consolidation_groups",
    "generate_shipment_groups",
    "reject_unknown_shipments",
]
