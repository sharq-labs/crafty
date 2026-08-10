"""D4 - local compatibility and recombination experiment contracts.

D4 deliberately keeps compatibility rules, child materialization semantics, and
interaction equations in this experiment-owned module. The only Core objects it
uses are the frozen DesignCandidate, DesignEvaluation, DesignMemoryEntry, and
ScientificTwin contracts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.objectives import ObjectiveDefinition, ObjectiveDirection
from ..scientific.ir.problem import ModelReference
from ..scientific.ir.values import (
    BooleanValue,
    CategoricalValue,
    IntegerValue,
    ScientificValue,
    decode_value,
    encode_value,
)
from ..scientific.ir.variables import ScientificVariable, VariableKind, VariableRole
from ..scientific.results.provenance import ProvenanceRecord
from ..scientific.results.result import ScientificResult
from ..scientific.serialization import require_schema, schema_string
from ..scientific.solvers.protocol import ConvergenceState, SolverIdentity
from ..scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
    TwinReference,
)
from ..scientific.units.quantity import Quantity
from .candidate import DesignCandidate, DesignCandidateReference
from .evaluation import (
    RESULT_BINDING_METADATA_KEY,
    DesignEvaluation,
    DesignEvaluationReference,
    ResultBinding,
    SelectionEligibility,
)
from .generation import assignment_digest
from .memory import DesignMemoryEntry, DesignMemoryScope
from .space import DesignSpace


COMPATIBILITY_CONTEXT_ID = "d4-synthetic-compat-v0.1"
SLOT_SCHEMA_ID = "d4-synthetic-slots-v0.1"
MATERIALIZATION_SEMANTICS_ID = "d4-synthetic-materialization-v0.1"
RECOMBINATION_OPERATOR = "recombine:d4-synthetic-v0.1"
CHILD_GENERATION = 1

D4_SOURCE_RECORD_SCHEMA = schema_string("d4_selected_source_record")
D4_COMPATIBILITY_RESULT_SCHEMA = schema_string("d4_compatibility_result")
D4_DERIVATION_RECORD_SCHEMA = schema_string("d4_derivation_record")
D4_MATERIALIZATION_SCHEMA = schema_string("d4_materialization")

SLOTS = (
    "component_a",
    "component_b",
    "adapter",
    "control_level",
    "guard_enabled",
)
A_VALUES = ("A_base", "A_peak", "A_stable")
B_VALUES = ("B_base", "B_peak", "B_filter")
ADAPTER_VALUES = ("direct", "buffered", "isolated")

TARGET_THRESHOLDS = {
    "yield_score": 70.0,
    "loss_score": 25.0,
    "stability_score": 50.0,
}

FORBIDDEN_CHILD_STATUS_KEYS = frozenset(
    {
        "adequacy",
        "archive_membership",
        "evidence",
        "feasibility",
        "model_adequacy",
        "pareto",
        "pareto_member",
        "safety",
        "scientific_validity",
        "selection",
        "selection_eligibility",
        "status",
        "target",
        "target_pass",
        "uq",
        "validation",
    }
)


class CompatibilityState(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    INVALID = "INVALID"


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _identity_sort_key(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _value_plain(value: ScientificValue) -> Any:
    if isinstance(value, (CategoricalValue, IntegerValue, BooleanValue)):
        return value.value
    if isinstance(value, Quantity):
        return value.magnitude
    raise InvalidScientificProblem("D4 encountered unsupported ScientificValue")


def _cat(value: str, vocabulary: Sequence[str]) -> CategoricalValue:
    return CategoricalValue(value=value, vocabulary=tuple(vocabulary))


def _int(value: int) -> IntegerValue:
    return IntegerValue(value=value)


def _bool(value: bool) -> BooleanValue:
    return BooleanValue(value=value)


@dataclass(frozen=True)
class D4SelectedSourceRecord:
    slot_name: str
    selected_value: ScientificValue
    parent_candidate: DesignCandidateReference
    parent_twin: TwinReference
    parent_evaluation: DesignEvaluationReference
    d3_entry_identity: str
    d3_entry_digest: str

    def __post_init__(self) -> None:
        slot_name = str(self.slot_name).strip()
        if not slot_name:
            raise InvalidScientificProblem("D4 source record requires slot_name")
        if slot_name not in SLOTS:
            raise InvalidScientificProblem("D4 source record names an unknown slot")
        if not isinstance(self.parent_candidate, DesignCandidateReference):
            raise InvalidScientificProblem("D4 source record requires parent candidate")
        if not isinstance(self.parent_twin, TwinReference):
            raise InvalidScientificProblem("D4 source record requires parent Twin")
        if not isinstance(self.parent_evaluation, DesignEvaluationReference):
            raise InvalidScientificProblem("D4 source record requires parent evaluation")
        for label, value in (
            ("D3 entry identity", self.d3_entry_identity),
            ("D3 entry digest", self.d3_entry_digest),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(ch not in "0123456789abcdef" for ch in value)
            ):
                raise InvalidScientificProblem(f"{label} must be a 64-char hex digest")
        object.__setattr__(self, "slot_name", slot_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D4_SOURCE_RECORD_SCHEMA,
            "slot_name": self.slot_name,
            "selected_value": encode_value(self.selected_value),
            "parent_candidate": self.parent_candidate.to_dict(),
            "parent_twin": self.parent_twin.to_dict(),
            "parent_evaluation": self.parent_evaluation.to_dict(),
            "d3_entry_identity": self.d3_entry_identity,
            "d3_entry_digest": self.d3_entry_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D4SelectedSourceRecord":
        require_schema(payload, D4_SOURCE_RECORD_SCHEMA)
        return cls(
            slot_name=payload["slot_name"],
            selected_value=decode_value(payload["selected_value"]),
            parent_candidate=DesignCandidateReference.from_dict(
                payload["parent_candidate"]
            ),
            parent_twin=TwinReference.from_dict(payload["parent_twin"]),
            parent_evaluation=DesignEvaluationReference.from_dict(
                payload["parent_evaluation"]
            ),
            d3_entry_identity=payload["d3_entry_identity"],
            d3_entry_digest=payload["d3_entry_digest"],
        )


@dataclass(frozen=True)
class D4CompatibilityResult:
    state: CompatibilityState
    reason: str
    failed_rule_ids: tuple[str, ...] = ()
    compatibility_context_id: str = COMPATIBILITY_CONTEXT_ID
    slot_schema_id: str = SLOT_SCHEMA_ID
    materialization_semantics_id: str = MATERIALIZATION_SEMANTICS_ID

    def __post_init__(self) -> None:
        state = CompatibilityState(self.state)
        reason = str(self.reason).strip()
        if not reason:
            raise InvalidScientificProblem("D4 compatibility result requires reason")
        failed = tuple(str(item).strip() for item in self.failed_rule_ids)
        if any(not item for item in failed):
            raise InvalidScientificProblem("D4 failed rule ids must be non-empty")
        if state is CompatibilityState.COMPATIBLE and failed:
            raise InvalidScientificProblem("COMPATIBLE cannot carry failed rules")
        if state is not CompatibilityState.COMPATIBLE and not failed:
            raise InvalidScientificProblem("non-compatible result needs failed rules")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "failed_rule_ids", tuple(sorted(set(failed))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D4_COMPATIBILITY_RESULT_SCHEMA,
            "state": self.state.value,
            "reason": self.reason,
            "failed_rule_ids": list(self.failed_rule_ids),
            "compatibility_context_id": self.compatibility_context_id,
            "slot_schema_id": self.slot_schema_id,
            "materialization_semantics_id": self.materialization_semantics_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D4CompatibilityResult":
        require_schema(payload, D4_COMPATIBILITY_RESULT_SCHEMA)
        return cls(
            state=CompatibilityState(payload["state"]),
            reason=payload["reason"],
            failed_rule_ids=tuple(payload.get("failed_rule_ids", ())),
            compatibility_context_id=payload.get(
                "compatibility_context_id", COMPATIBILITY_CONTEXT_ID
            ),
            slot_schema_id=payload.get("slot_schema_id", SLOT_SCHEMA_ID),
            materialization_semantics_id=payload.get(
                "materialization_semantics_id", MATERIALIZATION_SEMANTICS_ID
            ),
        )


@dataclass(frozen=True)
class D4DerivationRecord:
    child_candidate: DesignCandidateReference
    child_twin: TwinReference
    recombination_event_identity: str
    compatibility: D4CompatibilityResult
    selected_sources: tuple[D4SelectedSourceRecord, ...]
    parent_candidates: tuple[DesignCandidateReference, ...]
    parent_twins: tuple[TwinReference, ...]
    d3_sources: tuple[dict[str, str], ...]
    parent_evaluations: tuple[DesignEvaluationReference, ...]
    child_assignments: Mapping[str, ScientificValue]
    child_assignment_digest: str
    materialization_semantics_id: str = MATERIALIZATION_SEMANTICS_ID

    def __post_init__(self) -> None:
        if not isinstance(self.child_candidate, DesignCandidateReference):
            raise InvalidScientificProblem("D4 derivation requires child candidate")
        if not isinstance(self.child_twin, TwinReference):
            raise InvalidScientificProblem("D4 derivation requires child Twin")
        if not isinstance(self.compatibility, D4CompatibilityResult):
            raise InvalidScientificProblem("D4 derivation requires compatibility result")
        if self.compatibility.state is not CompatibilityState.COMPATIBLE:
            raise InvalidScientificProblem("D4 derivation requires compatible inputs")
        sources = tuple(
            sorted(
                self.selected_sources,
                key=lambda item: _identity_sort_key(item.to_dict()),
            )
        )
        parents = tuple(
            sorted(self.parent_candidates, key=lambda item: item.candidate_id)
        )
        twins = tuple(
            sorted(self.parent_twins, key=lambda item: (item.twin_id, item.version))
        )
        evaluations = tuple(
            sorted(self.parent_evaluations, key=lambda item: item.evaluation_id)
        )
        assignments = dict(self.child_assignments)
        digest = assignment_digest(assignments)
        if digest != self.child_assignment_digest:
            raise InvalidScientificProblem("D4 child assignment digest mismatch")
        if self.child_candidate.candidate_id != child_candidate_id(
            self.recombination_event_identity
        ):
            raise InvalidScientificProblem("D4 child candidate id does not match event")
        object.__setattr__(self, "selected_sources", sources)
        object.__setattr__(self, "parent_candidates", parents)
        object.__setattr__(self, "parent_twins", twins)
        object.__setattr__(self, "parent_evaluations", evaluations)
        object.__setattr__(
            self,
            "d3_sources",
            tuple(
                sorted(
                    (dict(item) for item in self.d3_sources),
                    key=lambda item: (item["identity"], item["entry_digest"]),
                )
            ),
        )
        object.__setattr__(self, "child_assignments", assignments)

    @property
    def identity(self) -> str:
        return self.recombination_event_identity

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D4_DERIVATION_RECORD_SCHEMA,
            "child_candidate": self.child_candidate.to_dict(),
            "child_twin": self.child_twin.to_dict(),
            "recombination_event_identity": self.recombination_event_identity,
            "compatibility": self.compatibility.to_dict(),
            "selected_sources": [item.to_dict() for item in self.selected_sources],
            "parent_candidates": [item.to_dict() for item in self.parent_candidates],
            "parent_twins": [item.to_dict() for item in self.parent_twins],
            "d3_sources": [dict(sorted(item.items())) for item in self.d3_sources],
            "parent_evaluations": [item.to_dict() for item in self.parent_evaluations],
            "materialization_semantics_id": self.materialization_semantics_id,
            "child_assignment_digest": self.child_assignment_digest,
            "child_assignments": {
                name: encode_value(value)
                for name, value in sorted(self.child_assignments.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D4DerivationRecord":
        require_schema(payload, D4_DERIVATION_RECORD_SCHEMA)
        return cls(
            child_candidate=DesignCandidateReference.from_dict(
                payload["child_candidate"]
            ),
            child_twin=TwinReference.from_dict(payload["child_twin"]),
            recombination_event_identity=payload["recombination_event_identity"],
            compatibility=D4CompatibilityResult.from_dict(payload["compatibility"]),
            selected_sources=tuple(
                D4SelectedSourceRecord.from_dict(item)
                for item in payload.get("selected_sources", ())
            ),
            parent_candidates=tuple(
                DesignCandidateReference.from_dict(item)
                for item in payload.get("parent_candidates", ())
            ),
            parent_twins=tuple(
                TwinReference.from_dict(item) for item in payload.get("parent_twins", ())
            ),
            d3_sources=tuple(dict(item) for item in payload.get("d3_sources", ())),
            parent_evaluations=tuple(
                DesignEvaluationReference.from_dict(item)
                for item in payload.get("parent_evaluations", ())
            ),
            child_assignments={
                name: decode_value(value)
                for name, value in payload.get("child_assignments", {}).items()
            },
            child_assignment_digest=payload["child_assignment_digest"],
            materialization_semantics_id=payload.get(
                "materialization_semantics_id", MATERIALIZATION_SEMANTICS_ID
            ),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), indent=indent
        )


@dataclass(frozen=True)
class D4Materialization:
    compatibility: D4CompatibilityResult
    recombination_event_identity: str
    child_candidate: DesignCandidate | None = None
    child_twin: ScientificTwin | None = None
    derivation: D4DerivationRecord | None = None
    child_evaluation: DesignEvaluation | None = None
    target_pass: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D4_MATERIALIZATION_SCHEMA,
            "compatibility": self.compatibility.to_dict(),
            "recombination_event_identity": self.recombination_event_identity,
            "child_candidate": self.child_candidate.to_dict()
            if self.child_candidate
            else None,
            "child_twin": self.child_twin.to_dict() if self.child_twin else None,
            "derivation": self.derivation.to_dict() if self.derivation else None,
            "child_evaluation": self.child_evaluation.to_dict()
            if self.child_evaluation
            else None,
            "target_pass": self.target_pass,
        }


def design_space() -> DesignSpace:
    return DesignSpace(
        space_id="d4-domain-neutral-synthetic",
        version="0.1",
        variables=(
            ScientificVariable(
                name="component_a",
                unit="dimensionless",
                kind=VariableKind.CATEGORICAL,
                role=VariableRole.DESIGN,
                categories=A_VALUES,
            ),
            ScientificVariable(
                name="component_b",
                unit="dimensionless",
                kind=VariableKind.CATEGORICAL,
                role=VariableRole.DESIGN,
                categories=B_VALUES,
            ),
            ScientificVariable(
                name="adapter",
                unit="dimensionless",
                kind=VariableKind.CATEGORICAL,
                role=VariableRole.DESIGN,
                categories=ADAPTER_VALUES,
            ),
            ScientificVariable(
                name="control_level",
                unit="dimensionless",
                kind=VariableKind.INTEGER,
                role=VariableRole.DESIGN,
                lower=Quantity(0, "dimensionless"),
                upper=Quantity(2, "dimensionless"),
            ),
            ScientificVariable(
                name="guard_enabled",
                unit="dimensionless",
                kind=VariableKind.BOOLEAN,
                role=VariableRole.DESIGN,
            ),
        ),
    )


YIELD = ObjectiveDefinition(
    name="yield_score",
    metric="yield_score",
    direction=ObjectiveDirection.MAXIMIZE,
    unit="dimensionless",
)
LOSS = ObjectiveDefinition(
    name="loss_score",
    metric="loss_score",
    direction=ObjectiveDirection.MINIMIZE,
    unit="dimensionless",
)
STABILITY = ObjectiveDefinition(
    name="stability_score",
    metric="stability_score",
    direction=ObjectiveDirection.MAXIMIZE,
    unit="dimensionless",
)
OBJECTIVES = (YIELD, LOSS, STABILITY)

A_YIELD = {"A_base": 20, "A_peak": 50, "A_stable": 25}
B_YIELD = {"B_base": 12, "B_peak": 35, "B_filter": 10}
ADAPTER_YIELD = {"direct": 3, "buffered": -2, "isolated": -5}
A_LOSS = {"A_base": 5, "A_peak": 20, "A_stable": 8}
B_LOSS = {"B_base": 4, "B_peak": 15, "B_filter": -10}
ADAPTER_LOSS = {"direct": 0, "buffered": 4, "isolated": 8}
A_STABILITY = {"A_base": 10, "A_peak": -10, "A_stable": 25}
B_STABILITY = {"B_base": 8, "B_peak": -15, "B_filter": 20}
ADAPTER_STABILITY = {"direct": -2, "buffered": 5, "isolated": 12}
INTERACTIONS = {
    ("A_peak", "B_filter"): (-25, 18, -30),
    ("A_stable", "B_filter"): (12, -4, 10),
    ("A_stable", "B_peak"): (18, 10, -8),
}


def typed_assignments(
    component_a: str,
    component_b: str,
    adapter: str,
    control_level: int,
    guard_enabled: bool,
) -> dict[str, ScientificValue]:
    return {
        "component_a": _cat(component_a, A_VALUES),
        "component_b": _cat(component_b, B_VALUES),
        "adapter": _cat(adapter, ADAPTER_VALUES),
        "control_level": _int(control_level),
        "guard_enabled": _bool(guard_enabled),
    }


def synthetic_objective_values(
    assignments: Mapping[str, ScientificValue],
) -> dict[str, Quantity]:
    a = assignments["component_a"].value
    b = assignments["component_b"].value
    adapter = assignments["adapter"].value
    level = assignments["control_level"].value
    guard = 1 if assignments["guard_enabled"].value else 0
    interaction_yield, interaction_loss, interaction_stability = INTERACTIONS.get(
        (a, b), (0, 0, 0)
    )
    return {
        "yield_score": Quantity(
            A_YIELD[a]
            + B_YIELD[b]
            + ADAPTER_YIELD[adapter]
            + 2 * level
            - 3 * guard
            + interaction_yield,
            "dimensionless",
        ),
        "loss_score": Quantity(
            A_LOSS[a]
            + B_LOSS[b]
            + ADAPTER_LOSS[adapter]
            + level
            + 5 * guard
            + interaction_loss,
            "dimensionless",
        ),
        "stability_score": Quantity(
            A_STABILITY[a]
            + B_STABILITY[b]
            + ADAPTER_STABILITY[adapter]
            + 3 * level
            + 10 * guard
            + interaction_stability,
            "dimensionless",
        ),
    }


def target_assessment(values: Mapping[str, Quantity]) -> bool:
    return (
        values["yield_score"].magnitude >= TARGET_THRESHOLDS["yield_score"]
        and values["loss_score"].magnitude <= TARGET_THRESHOLDS["loss_score"]
        and values["stability_score"].magnitude
        >= TARGET_THRESHOLDS["stability_score"]
    )


def _new_twin(
    *,
    twin_id: str,
    kind: TwinKind,
    assignments: Mapping[str, ScientificValue],
    parent: TwinReference | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ScientificTwin:
    return ScientificTwin(
        twin_id=twin_id,
        version="1",
        kind=kind,
        models=(ModelReference("d4.synthetic.analytic", "0.1"),),
        declarations=tuple(
            TwinDatum(name=name, value=assignments[name], role=TwinDatumRole.PARAMETER)
            for name in sorted(assignments)
        ),
        parent=parent,
        metadata=dict(metadata or {}),
    )


def _make_evaluation(
    candidate: DesignCandidate,
    *,
    suffix: str,
    eligible_reason: str,
) -> DesignEvaluation:
    binding = ResultBinding(
        candidate=candidate.reference,
        twin=candidate.twin,
        design_space=candidate.design_space,
    )
    result = ScientificResult(
        result_id=f"d4-result:{suffix}:{candidate.candidate_id}",
        problem_id="d4-synthetic-objectives-v0.1",
        values=synthetic_objective_values(candidate.assignments),
        provenance=ProvenanceRecord(
            run_id=f"d4-run:{suffix}:{candidate.candidate_id}",
            models=(("d4.synthetic.analytic", "0.1"),),
            solvers=(("d4.closed-form.synthetic", "0.1"),),
            metadata={RESULT_BINDING_METADATA_KEY: binding.to_dict()},
        ),
        solver=SolverIdentity("d4.closed-form.synthetic", "0.1"),
        convergence=ConvergenceState.NOT_APPLICABLE,
    )
    return DesignEvaluation(
        evaluation_id=f"d4-eval:{suffix}:{candidate.candidate_id}",
        candidate=candidate.reference,
        twin=candidate.twin,
        design_space=candidate.design_space,
        result=result,
        eligibility=SelectionEligibility.ELIGIBLE,
        eligibility_reasons=(eligible_reason,),
    )


def build_parent_candidates_and_memory() -> tuple[
    DesignSpace,
    tuple[DesignCandidate, ...],
    tuple[ScientificTwin, ...],
    tuple[DesignEvaluation, ...],
    tuple[DesignMemoryEntry, ...],
]:
    space = design_space()
    parent_assignments = {
        "d4-parent-a": typed_assignments("A_peak", "B_base", "buffered", 2, False),
        "d4-parent-b": typed_assignments("A_base", "B_peak", "direct", 0, False),
        "d4-parent-c": typed_assignments("A_stable", "B_base", "direct", 1, True),
        "d4-parent-d": typed_assignments("A_base", "B_filter", "buffered", 2, True),
    }
    twins = tuple(
        _new_twin(
            twin_id=f"d4-twin:{candidate_id}",
            kind=TwinKind.CANDIDATE,
            assignments=assignments,
        )
        for candidate_id, assignments in parent_assignments.items()
    )
    twin_by_parent = {
        twin.twin_id.removeprefix("d4-twin:"): twin.reference for twin in twins
    }
    candidates = tuple(
        DesignCandidate(
            candidate_id=candidate_id,
            design_space=space.reference,
            twin=twin_by_parent[candidate_id],
            assignments=assignments,
            generation=0,
            parents=(),
            operator="declared:d4-preregistered-parent",
        ).validate_against(space)
        for candidate_id, assignments in parent_assignments.items()
    )
    evaluations = tuple(
        _make_evaluation(
            candidate,
            suffix="parent",
            eligible_reason="preregistered D4 parent synthetic evaluation",
        )
        for candidate in candidates
    )
    scope = DesignMemoryScope(
        design_space=space.reference,
        objectives=OBJECTIVES,
        context_reference="d4-preregistered-parent-observations-v0.1",
    )
    entries = tuple(
        DesignMemoryEntry.from_evaluation(
            scope=scope, candidate=candidate, evaluation=evaluation
        )
        for candidate, evaluation in zip(candidates, evaluations)
    )
    return space, candidates, twins, evaluations, entries


def _fail(
    state: CompatibilityState,
    reason: str,
    rule: str,
    *,
    compatibility_context_id: str,
    slot_schema_id: str,
    materialization_semantics_id: str,
) -> D4CompatibilityResult:
    return D4CompatibilityResult(
        state=state,
        reason=reason,
        failed_rule_ids=(rule,),
        compatibility_context_id=compatibility_context_id,
        slot_schema_id=slot_schema_id,
        materialization_semantics_id=materialization_semantics_id,
    )


def assess_compatibility(
    *,
    selected_sources: Sequence[D4SelectedSourceRecord],
    child_assignments: Mapping[str, ScientificValue],
    parent_candidates: Sequence[DesignCandidate],
    parent_evaluations: Sequence[DesignEvaluation],
    d3_entries: Sequence[DesignMemoryEntry],
    compatibility_context_id: str = COMPATIBILITY_CONTEXT_ID,
    slot_schema_id: str = SLOT_SCHEMA_ID,
    materialization_semantics_id: str = MATERIALIZATION_SEMANTICS_ID,
) -> D4CompatibilityResult:
    if compatibility_context_id != COMPATIBILITY_CONTEXT_ID:
        return _fail(
            CompatibilityState.INVALID,
            "altered compatibility context id is not attributable to D4 V0.1",
            "context-identity",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    if slot_schema_id != SLOT_SCHEMA_ID:
        return _fail(
            CompatibilityState.INVALID,
            "altered slot schema id is not attributable to D4 V0.1",
            "slot-schema-identity",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    if materialization_semantics_id != MATERIALIZATION_SEMANTICS_ID:
        return _fail(
            CompatibilityState.INVALID,
            "altered materialization semantics id is not attributable to D4 V0.1",
            "materialization-semantics-identity",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    sources = tuple(selected_sources)
    if not sources:
        return _fail(
            CompatibilityState.INVALID,
            "no selected source records were declared",
            "source-records-present",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    slots = [source.slot_name for source in sources]
    if len(slots) != len(set(slots)):
        return _fail(
            CompatibilityState.INVALID,
            "duplicate selected source slots are not attributable",
            "source-slot-unique",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    if set(child_assignments) != set(SLOTS):
        return _fail(
            CompatibilityState.INVALID,
            "child assignment does not contain exactly the five D4 slots",
            "complete-child-assignment",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    try:
        design_space().validate_assignments(child_assignments)
    except Exception:
        return _fail(
            CompatibilityState.INVALID,
            "child assignment violates typed D4 slot/value semantics",
            "typed-child-assignment",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )

    candidates_by_id = {candidate.candidate_id: candidate for candidate in parent_candidates}
    evaluations_by_id = {
        evaluation.evaluation_id: evaluation for evaluation in parent_evaluations
    }
    d3_by_identity = {entry.identity: entry for entry in d3_entries}
    if len(candidates_by_id) != len(tuple(parent_candidates)):
        return _fail(
            CompatibilityState.INVALID,
            "parent candidate identities are not unique",
            "parent-identity-unique",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    for source in sources:
        parent = candidates_by_id.get(source.parent_candidate.candidate_id)
        if parent is None:
            return _fail(
                CompatibilityState.INVALID,
                "selected source references a nonexistent parent candidate",
                "parent-exists",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if parent.reference.candidate_id != source.parent_candidate.candidate_id:
            return _fail(
                CompatibilityState.INVALID,
                "selected parent reference disagrees with candidate payload",
                "parent-reference-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if parent.twin.key != source.parent_twin.key:
            return _fail(
                CompatibilityState.INVALID,
                "selected source Twin does not match attributable parent candidate",
                "parent-twin-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        evaluation = evaluations_by_id.get(source.parent_evaluation.evaluation_id)
        if evaluation is None:
            return _fail(
                CompatibilityState.INVALID,
                "selected source references a nonexistent parent evaluation",
                "parent-evaluation-exists",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if evaluation.candidate.candidate_id != parent.candidate_id:
            return _fail(
                CompatibilityState.INVALID,
                "selected source evaluation is bound to a different parent candidate",
                "parent-evaluation-candidate-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if evaluation.twin.key != parent.twin.key:
            return _fail(
                CompatibilityState.INVALID,
                "selected source evaluation is bound to a different parent Twin",
                "parent-evaluation-twin-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        entry = d3_by_identity.get(source.d3_entry_identity)
        if entry is None or entry.entry_digest != source.d3_entry_digest:
            return _fail(
                CompatibilityState.INVALID,
                "selected source D3 memory entry is absent or digest-mismatched",
                "d3-entry-attribution",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if entry.candidate.candidate_id != parent.candidate_id:
            return _fail(
                CompatibilityState.INVALID,
                "D3 memory entry is bound to a different candidate",
                "d3-entry-candidate-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if entry.evaluation.evaluation_id != evaluation.evaluation_id:
            return _fail(
                CompatibilityState.INVALID,
                "D3 memory entry is bound to a different evaluation",
                "d3-entry-evaluation-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if source.slot_name not in parent.assignments:
            return _fail(
                CompatibilityState.INVALID,
                "selected source slot is absent from parent candidate",
                "source-slot-present-in-parent",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if encode_value(parent.assignments[source.slot_name]) != encode_value(
            source.selected_value
        ):
            return _fail(
                CompatibilityState.INVALID,
                "selected source value does not equal parent candidate assignment",
                "source-value-parent-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if encode_value(entry.assignments[source.slot_name]) != encode_value(
            source.selected_value
        ):
            return _fail(
                CompatibilityState.INVALID,
                "selected source value does not equal attributable D3 assignment",
                "source-value-d3-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )
        if encode_value(child_assignments[source.slot_name]) != encode_value(
            source.selected_value
        ):
            return _fail(
                CompatibilityState.INVALID,
                "child materialization declaration differs from selected source",
                "child-source-assignment-match",
                compatibility_context_id=compatibility_context_id,
                slot_schema_id=slot_schema_id,
                materialization_semantics_id=materialization_semantics_id,
            )

    component_a = child_assignments["component_a"].value
    component_b = child_assignments["component_b"].value
    adapter = child_assignments["adapter"].value
    if (component_a, component_b) == ("A_peak", "B_peak"):
        return _fail(
            CompatibilityState.INCOMPATIBLE,
            "A_peak plus B_peak is a preregistered incompatible pair",
            "pair-matrix",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    adapter_requirements = {
        ("A_peak", "B_filter"): ("buffered",),
        ("A_stable", "B_peak"): ("direct",),
        ("A_stable", "B_filter"): ("buffered", "isolated"),
    }
    allowed = adapter_requirements.get((component_a, component_b), ADAPTER_VALUES)
    if adapter not in allowed:
        return _fail(
            CompatibilityState.INCOMPATIBLE,
            "adapter does not satisfy preregistered pair requirement",
            "adapter-requirement",
            compatibility_context_id=compatibility_context_id,
            slot_schema_id=slot_schema_id,
            materialization_semantics_id=materialization_semantics_id,
        )
    return D4CompatibilityResult(
        state=CompatibilityState.COMPATIBLE,
        reason="all D4 structural, attribution, pair, adapter and type checks passed",
        failed_rule_ids=(),
        compatibility_context_id=compatibility_context_id,
        slot_schema_id=slot_schema_id,
        materialization_semantics_id=materialization_semantics_id,
    )


def recombination_event_payload(
    *,
    selected_sources: Sequence[D4SelectedSourceRecord],
    child_assignments: Mapping[str, ScientificValue],
    compatibility: D4CompatibilityResult,
    child_generation: int = CHILD_GENERATION,
) -> dict[str, Any]:
    sources = tuple(selected_sources)
    parents = sorted(
        {source.parent_candidate.candidate_id: source.parent_candidate for source in sources}.values(),
        key=lambda item: item.candidate_id,
    )
    parent_twins = sorted(
        {source.parent_twin.key: source.parent_twin for source in sources}.values(),
        key=lambda item: (item.twin_id, item.version),
    )
    d3_sources = sorted(
        {
            (
                source.d3_entry_identity,
                source.d3_entry_digest,
            )
            for source in sources
        }
    )
    return {
        "schema": "d4_recombination_event/1",
        "compatibility_context_id": compatibility.compatibility_context_id,
        "slot_schema_id": compatibility.slot_schema_id,
        "materialization_semantics_id": compatibility.materialization_semantics_id,
        "parent_candidate_references": [item.to_dict() for item in parents],
        "parent_twin_references": [item.to_dict() for item in parent_twins],
        "d3_source_provenance": [
            {"identity": identity, "entry_digest": digest}
            for identity, digest in d3_sources
        ],
        "selected_source_records": sorted(
            [source.to_dict() for source in sources], key=_identity_sort_key
        ),
        "child_assignment": {
            name: encode_value(value) for name, value in sorted(child_assignments.items())
        },
        "compatibility_result": compatibility.to_dict(),
        "child_generation": child_generation,
        "operator": RECOMBINATION_OPERATOR,
    }


def recombination_event_digest(
    *,
    selected_sources: Sequence[D4SelectedSourceRecord],
    child_assignments: Mapping[str, ScientificValue],
    compatibility: D4CompatibilityResult,
    child_generation: int = CHILD_GENERATION,
) -> str:
    return _digest(
        recombination_event_payload(
            selected_sources=selected_sources,
            child_assignments=child_assignments,
            compatibility=compatibility,
            child_generation=child_generation,
        )
    )


def recombination_event_identity(event_digest: str) -> str:
    return f"d4-event:sha256:{event_digest}"


def child_candidate_id(event_identity_or_digest: str) -> str:
    digest = event_identity_or_digest.removeprefix("d4-event:sha256:")
    return f"d4-child:sha256:{digest}"


def child_twin_id(event_identity_or_digest: str) -> str:
    digest = event_identity_or_digest.removeprefix("d4-event:sha256:")
    return f"d4-derived-twin:sha256:{digest}"


def _ensure_no_status_inflation(payload: Mapping[str, Any], *, context: str) -> None:
    keys = {str(key).lower() for key in payload}
    forbidden = keys & FORBIDDEN_CHILD_STATUS_KEYS
    if forbidden:
        raise InvalidScientificProblem(
            f"{context} attempts to carry forbidden child scientific/status claims: "
            f"{sorted(forbidden)}"
        )


def materialize_recombination(
    *,
    selected_sources: Sequence[D4SelectedSourceRecord],
    child_assignments: Mapping[str, ScientificValue],
    parent_candidates: Sequence[DesignCandidate],
    parent_twins: Sequence[ScientificTwin],
    parent_evaluations: Sequence[DesignEvaluation],
    d3_entries: Sequence[DesignMemoryEntry],
    supplied_child_id: str | None = None,
    materialized_assignments: Mapping[str, ScientificValue] | None = None,
    attempted_parent_result_attachment: Sequence[ScientificResult] = (),
    attempted_status_inheritance: Mapping[str, Any] | None = None,
    compatibility_context_id: str = COMPATIBILITY_CONTEXT_ID,
) -> D4Materialization:
    compatibility = assess_compatibility(
        selected_sources=selected_sources,
        child_assignments=child_assignments,
        parent_candidates=parent_candidates,
        parent_evaluations=parent_evaluations,
        d3_entries=d3_entries,
        compatibility_context_id=compatibility_context_id,
    )
    event_digest = recombination_event_digest(
        selected_sources=selected_sources,
        child_assignments=child_assignments,
        compatibility=compatibility,
    )
    event_identity = recombination_event_identity(event_digest)
    if compatibility.state is not CompatibilityState.COMPATIBLE:
        return D4Materialization(
            compatibility=compatibility,
            recombination_event_identity=event_identity,
        )
    expected_child_id = child_candidate_id(event_identity)
    if supplied_child_id is not None and supplied_child_id != expected_child_id:
        raise InvalidScientificProblem("D4 supplied child id differs from event digest")
    if materialized_assignments is not None and {
        name: encode_value(value) for name, value in materialized_assignments.items()
    } != {name: encode_value(value) for name, value in child_assignments.items()}:
        raise InvalidScientificProblem(
            "D4 materialized child assignments differ from declared recombination"
        )
    if tuple(attempted_parent_result_attachment):
        raise InvalidScientificProblem(
            "D4 child cannot attach parent ScientificResult as child evidence"
        )
    if attempted_status_inheritance:
        _ensure_no_status_inflation(attempted_status_inheritance, context="D4 child")

    parent_refs = tuple(
        sorted(
            {
                source.parent_candidate.candidate_id: source.parent_candidate
                for source in selected_sources
            }.values(),
            key=lambda item: item.candidate_id,
        )
    )
    parent_twin_refs = tuple(
        sorted(
            {source.parent_twin.key: source.parent_twin for source in selected_sources}.values(),
            key=lambda item: (item.twin_id, item.version),
        )
    )
    twin_by_key = {twin.reference.key: twin for twin in parent_twins}
    if any(ref.key not in twin_by_key for ref in parent_twin_refs):
        raise InvalidScientificProblem("D4 parent Twin source absent at materialization")
    if expected_child_id in {parent.candidate_id for parent in parent_refs}:
        raise InvalidScientificProblem("D4 child id collides with a parent candidate")
    child_twin_ref = TwinReference(child_twin_id(event_identity), "1")
    if child_twin_ref.key in {ref.key for ref in parent_twin_refs}:
        raise InvalidScientificProblem("D4 child Twin reference collides with parent Twin")

    d3_sources = tuple(
        {"identity": source.d3_entry_identity, "entry_digest": source.d3_entry_digest}
        for source in selected_sources
    )
    child = DesignCandidate(
        candidate_id=expected_child_id,
        design_space=design_space().reference,
        twin=child_twin_ref,
        assignments=dict(child_assignments),
        generation=CHILD_GENERATION,
        parents=parent_refs,
        operator=RECOMBINATION_OPERATOR,
        metadata={"d4_derivation_event": event_identity},
    ).validate_against(design_space())
    child_twin = _new_twin(
        twin_id=child_twin_ref.twin_id,
        kind=TwinKind.DERIVED,
        assignments=child_assignments,
        parent=parent_twin_refs[0],
        metadata={
            "d4_derivation_event": event_identity,
            "authoritative_multi_parent_lineage": "D4DerivationRecord",
        },
    )
    derivation = D4DerivationRecord(
        child_candidate=child.reference,
        child_twin=child_twin.reference,
        recombination_event_identity=event_identity,
        compatibility=compatibility,
        selected_sources=tuple(selected_sources),
        parent_candidates=parent_refs,
        parent_twins=parent_twin_refs,
        d3_sources=d3_sources,
        parent_evaluations=tuple(source.parent_evaluation for source in selected_sources),
        child_assignments=child_assignments,
        child_assignment_digest=assignment_digest(child_assignments),
    )
    child_evaluation = _make_evaluation(
        child,
        suffix="child",
        eligible_reason="new D4 synthetic child evaluation under frozen equations",
    )
    validate_child_scientific_independence(
        derivation=derivation,
        child_candidate=child,
        child_twin=child_twin,
        child_evaluation=child_evaluation,
        parent_evaluations=parent_evaluations,
    )
    return D4Materialization(
        compatibility=compatibility,
        recombination_event_identity=event_identity,
        child_candidate=child,
        child_twin=child_twin,
        derivation=derivation,
        child_evaluation=child_evaluation,
        target_pass=target_assessment(child_evaluation.result.values),
    )


def validate_child_scientific_independence(
    *,
    derivation: D4DerivationRecord,
    child_candidate: DesignCandidate,
    child_twin: ScientificTwin,
    child_evaluation: DesignEvaluation,
    parent_evaluations: Sequence[DesignEvaluation],
) -> None:
    if child_candidate.reference.candidate_id != derivation.child_candidate.candidate_id:
        raise InvalidScientificProblem("D4 child candidate is not derivation child")
    if child_twin.reference.key != derivation.child_twin.key:
        raise InvalidScientificProblem("D4 child Twin is not derivation child Twin")
    if child_twin.kind is not TwinKind.DERIVED:
        raise InvalidScientificProblem("D4 child Twin must be TwinKind.DERIVED")
    if child_twin.evidence_refs or child_twin.calibration_evidence_refs:
        raise InvalidScientificProblem("D4 child Twin cannot inherit parent evidence")
    if child_evaluation.candidate.candidate_id != child_candidate.candidate_id:
        raise InvalidScientificProblem("D4 child evaluation does not bind child candidate")
    if child_evaluation.twin.key != child_twin.reference.key:
        raise InvalidScientificProblem("D4 child evaluation does not bind child Twin")
    if child_evaluation.result_binding.candidate.candidate_id != child_candidate.candidate_id:
        raise InvalidScientificProblem("D4 child result binding names wrong candidate")
    if child_evaluation.result_binding.twin.key != child_twin.reference.key:
        raise InvalidScientificProblem("D4 child result binding names wrong Twin")
    parent_candidate_ids = {item.candidate.candidate_id for item in parent_evaluations}
    parent_twin_keys = {item.twin.key for item in parent_evaluations}
    parent_result_ids = {item.result.result_id for item in parent_evaluations}
    parent_evaluation_ids = {item.evaluation_id for item in parent_evaluations}
    if child_candidate.candidate_id in parent_candidate_ids:
        raise InvalidScientificProblem("D4 child candidate reused a parent identity")
    if child_twin.reference.key in parent_twin_keys:
        raise InvalidScientificProblem("D4 child Twin reused a parent Twin identity")
    if child_evaluation.result.result_id in parent_result_ids:
        raise InvalidScientificProblem("D4 child reused a parent ScientificResult")
    child_result_payload = json.dumps(
        child_evaluation.result.to_dict(), sort_keys=True, separators=(",", ":")
    )
    for forbidden in parent_result_ids | parent_evaluation_ids:
        if forbidden in child_result_payload:
            raise InvalidScientificProblem(
                "D4 child result contains parent scientific evidence identity"
            )
    _ensure_no_status_inflation(child_candidate.metadata, context="D4 child candidate")
    allowed_twin_metadata = {
        "d4_derivation_event",
        "authoritative_multi_parent_lineage",
    }
    extra_twin_metadata = set(child_twin.metadata) - allowed_twin_metadata
    if extra_twin_metadata:
        _ensure_no_status_inflation(
            {key: child_twin.metadata[key] for key in extra_twin_metadata},
            context="D4 child Twin",
        )


def source_record(
    *,
    slot_name: str,
    parent_id: str,
    candidates: Sequence[DesignCandidate],
    evaluations: Sequence[DesignEvaluation],
    d3_entries: Sequence[DesignMemoryEntry],
) -> D4SelectedSourceRecord:
    candidate = {item.candidate_id: item for item in candidates}[parent_id]
    evaluation = {item.candidate.candidate_id: item for item in evaluations}[parent_id]
    entry = {item.candidate.candidate_id: item for item in d3_entries}[parent_id]
    return D4SelectedSourceRecord(
        slot_name=slot_name,
        selected_value=candidate.assignments[slot_name],
        parent_candidate=candidate.reference,
        parent_twin=candidate.twin,
        parent_evaluation=evaluation.reference,
        d3_entry_identity=entry.identity,
        d3_entry_digest=entry.entry_digest,
    )


def preregistered_cases(
    *,
    candidates: Sequence[DesignCandidate],
    evaluations: Sequence[DesignEvaluation],
    d3_entries: Sequence[DesignMemoryEntry],
) -> dict[str, tuple[tuple[D4SelectedSourceRecord, ...], dict[str, ScientificValue]]]:
    def src(parent_id: str, *slots: str) -> tuple[D4SelectedSourceRecord, ...]:
        return tuple(
            source_record(
                slot_name=slot,
                parent_id=parent_id,
                candidates=candidates,
                evaluations=evaluations,
                d3_entries=d3_entries,
            )
            for slot in slots
        )

    return {
        "A": (
            src("d4-parent-a", "component_a")
            + src("d4-parent-b", "component_b")
            + src("d4-parent-a", "adapter", "control_level", "guard_enabled"),
            typed_assignments("A_peak", "B_peak", "buffered", 2, False),
        ),
        "B": (
            src("d4-parent-a", "component_a")
            + src(
                "d4-parent-d",
                "component_b",
                "adapter",
                "control_level",
                "guard_enabled",
            ),
            typed_assignments("A_peak", "B_filter", "buffered", 2, True),
        ),
        "C": (
            src("d4-parent-c", "component_a", "guard_enabled")
            + src("d4-parent-d", "component_b", "adapter", "control_level"),
            typed_assignments("A_stable", "B_filter", "buffered", 2, True),
        ),
        "D": (
            src("d4-parent-c", "component_a", "guard_enabled", "control_level")
            + src("d4-parent-b", "component_b", "adapter"),
            typed_assignments("A_stable", "B_peak", "direct", 1, True),
        ),
    }


def run_preregistered_case(case_name: str) -> D4Materialization:
    space, candidates, twins, evaluations, entries = build_parent_candidates_and_memory()
    cases = preregistered_cases(
        candidates=candidates, evaluations=evaluations, d3_entries=entries
    )
    sources, assignments = cases[case_name]
    return materialize_recombination(
        selected_sources=sources,
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )


def objective_plain(values: Mapping[str, Quantity]) -> dict[str, float]:
    return {name: values[name].magnitude for name in sorted(values)}


def compare_child_to_parents(
    *,
    child: DesignEvaluation,
    parents: Sequence[DesignEvaluation],
) -> dict[str, Any]:
    child_values = child.result.values
    parent_values = {item.candidate.candidate_id: item.result.values for item in parents}
    comparisons: dict[str, Any] = {}
    for parent_id, values in parent_values.items():
        comparisons[parent_id] = {
            "yield_score_delta": child_values["yield_score"].magnitude
            - values["yield_score"].magnitude,
            "loss_score_delta": child_values["loss_score"].magnitude
            - values["loss_score"].magnitude,
            "stability_score_delta": child_values["stability_score"].magnitude
            - values["stability_score"].magnitude,
        }
    improved_objectives = []
    if all(
        child_values["yield_score"].magnitude > values["yield_score"].magnitude
        for values in parent_values.values()
    ):
        improved_objectives.append("yield_score")
    if all(
        child_values["loss_score"].magnitude < values["loss_score"].magnitude
        for values in parent_values.values()
    ):
        improved_objectives.append("loss_score")
    if all(
        child_values["stability_score"].magnitude
        > values["stability_score"].magnitude
        for values in parent_values.values()
    ):
        improved_objectives.append("stability_score")
    underperformed = False
    for values in parent_values.values():
        underperformed = underperformed or (
            child_values["yield_score"].magnitude < values["yield_score"].magnitude
            or child_values["loss_score"].magnitude > values["loss_score"].magnitude
            or child_values["stability_score"].magnitude
            < values["stability_score"].magnitude
        )
    return {
        "against_parents": comparisons,
        "improved_objectives_relative_to_all_relevant_parents": improved_objectives,
        "underperformed_at_least_one_relevant_parent": underperformed,
    }


def selected_parent_ids(sources: Sequence[D4SelectedSourceRecord]) -> tuple[str, ...]:
    return tuple(sorted({source.parent_candidate.candidate_id for source in sources}))
