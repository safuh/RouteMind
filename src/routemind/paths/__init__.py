"""Feasible multimodal shipment path discovery and consolidation analysis."""

from .consolidation import (
    ConsolidationEngine,
    ConsolidationEvaluation,
    ConsolidationOpportunity,
    ConsolidationRejection,
    ConsolidationRejectionReason,
    SharedSegment,
)
from .contracts import CandidatePathContract, TransportLegContract, serialize_candidate_path, serialize_candidate_paths
from .diagnostics import PathRejection, PathSearchDiagnostics, RejectionReason
from .dominance import remove_dominated_paths
from .models import CandidatePath, PathStatus
from .search import PathSearchConfig, PathSearchEngine

__all__ = [
    "CandidatePath",
    "CandidatePathContract",
    "ConsolidationEngine",
    "ConsolidationEvaluation",
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
    "serialize_candidate_path",
    "serialize_candidate_paths",
]
