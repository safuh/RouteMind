"""Deterministic shipment consolidation primitives."""

from .engine import detect_shared_segments, evaluate_consolidation
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
    "detect_shared_segments",
    "evaluate_consolidation",
]
