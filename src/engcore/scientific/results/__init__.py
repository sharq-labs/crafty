"""Scientific results: value + unit + model + solver + validation + provenance."""

from .applicability import ApplicabilityReport, ApplicabilityState
from .data_reference import ScientificDataReference
from .provenance import ExecutionBinding, ProvenanceRecord
from .result import ScientificResult
from .uncertainty import Uncertainty, UncertaintyKind
from .validation import (
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
    unverified_report,
)
from .variable_binding import (
    VARIABLE_BULK_LINKAGE_SCHEMA,
    VariableBulkLinkage,
    unlinked_references,
)

__all__ = [
    "ApplicabilityReport",
    "ApplicabilityState",
    "ExecutionBinding",
    "ProvenanceRecord",
    "ScientificDataReference",
    "ScientificResult",
    "Uncertainty",
    "UncertaintyKind",
    "VARIABLE_BULK_LINKAGE_SCHEMA",
    "VariableBulkLinkage",
    "unlinked_references",
    "ValidationCheck",
    "ValidationLevel",
    "ValidationOutcome",
    "ValidationReport",
    "unverified_report",
]
