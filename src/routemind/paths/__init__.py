"""Feasible multimodal shipment path discovery and portfolio-sharing primitives."""

from .consolidation import (
    ConsolidationEngine,
    ConsolidationOpportunity,
    ConsolidationRejection,
    ConsolidationRejectionReason,
    SharedSegment,
)
from .contracts import CandidatePathContract, TransportLegContract, serialize_candidate_paths
from .diagnostics import PathRejection, PathSearchDiagnostics, RejectionReason
from .dominance import remove_dominated_paths
from .models import CandidatePath, PathStatus
from .search import PathSearchConfig, PathSearchEngine

__all__ = [
    "CandidatePath",
    "CandidatePathContract",
    "ConsolidationEngine",
    "ConsolidationOpportunity",
    "ConsolidationRejection",
    "ConsolidationRejectionReason",
    "PathRejection",
    "PathSearchConfig",
    "PathSearchDiagnostics",
    "PathSearchEngine",
    "PathStatus",
    "RejectionReason",
    "SharedSegment",
    "TransportLegContract",
    "remove_dominated_paths",
    "serialize_candidate_paths",
]
