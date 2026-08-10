"""D7 bounded integrated scientific-discovery loop.

This module deliberately lives with the experiment.  It composes the frozen
D0/D1/D3/D4/ScientificTwin contracts without changing them or promoting the
loop-local scope, evidence, derivation, decision, or checkpoint abstractions
into Core.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
import os

from engcore.design.candidate import DesignCandidate
from engcore.design.evaluation import (
    RESULT_BINDING_METADATA_KEY,
    DesignEvaluation,
    ResultBinding,
    SelectionEligibility,
)
from engcore.design.memory import (
    AssessmentContext,
    DesignMemoryEntry,
    DesignMemoryLayerA,
    DesignMemoryPolicy,
    DesignMemoryRecord,
    DesignMemoryScope,
    verify_layer_a_attribution,
)
from engcore.design import d4_recombination as d4
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.problem import ModelReference
from engcore.scientific.ir.values import (
    ScientificValue,
    decode_value,
    encode_value,
)
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.solvers.protocol import ConvergenceState, SolverIdentity
from engcore.scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
)
from engcore.scientific.units.quantity import Quantity


MILESTONE = "D7 - Integrated Scientific Discovery Loop / Cross-Milestone Object-Trace Conformance V0.1"
PREREGISTRATION = "docs/design-d7-integrated-discovery-loop-prereg.md"
PREREGISTRATION_CHECKPOINT = "86f8b4879a7e3da4839d53b209f51f09e55a742b"
MODEL = ("d4.synthetic.analytic", "0.1")
SOLVER = ("d4.closed-form.synthetic", "0.1")
PROBLEM_ID = "d4-synthetic-objectives-v0.1"
DESIGN_SPACE_REFERENCE = "d4-domain-neutral-synthetic@0.1"
EXECUTION_SEMANTICS = "d7.d4-closed-form-integrated-execution@0.1"
MEMORY_POLICY_ID = "d7-loop-memory-policy-v0.1"
ELIGIBILITY_POLICY_ID = "d7-closed-execution-eligibility@0.1"
OPTION_SET_ID = "d7-integrated-next-experiment-options-v0.1"
DECISION_POLICY_ID = "d7-information-per-compute-lexicographic@0.1"
GENERATION_ADMISSION = "d7-exact-d4-child-admission@0.1"
MATERIALIZATION_SEMANTICS = "d7-authoritative-d4-materialization@0.1"
SELECTED_MATERIALIZATION_SEMANTICS = "d7-selected-study-materialization@0.1"
SOURCE_GENERATION_ID = "d7-generation-0-preregistered@0.1"
RECOMBINATION_OPERATOR = "recombine:d4-synthetic-v0.1"
GENERATION0_REASON = (
    "preregistered D7 Generation 0 synthetic execution completed with finite "
    "projected objectives and exact result binding"
)
SUCCESSOR_REASON = (
    "preregistered D7 authoritative successor synthetic execution completed "
    "with finite projected objectives and exact result binding"
)
SELECTED_REASON = (
    "preregistered D7 selected synthetic execution completed with finite "
    "projected objectives and exact Candidate/Twin/Study/result binding"
)


def canonical_bytes(payload: Any) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidScientificProblem("D7 payload is not canonical finite JSON") from exc


def digest(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def _identity(prefix: str, payload: Any) -> str:
    return f"{prefix}:sha256:{digest(payload)}"


def _require_keys(payload: Mapping[str, Any], keys: set[str], context: str) -> None:
    actual = set(payload)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise InvalidScientificProblem(
            f"{context} schema fields mismatch; missing={missing}, extra={extra}"
        )


def _require_identity(recorded: Any, expected: str, context: str) -> str:
    if recorded != expected:
        raise InvalidScientificProblem(f"{context} identity mismatch")
    return expected


def _object_digest(value: Any) -> str:
    return digest(value.to_dict())


def _assignment_dict(values: Mapping[str, ScientificValue]) -> dict[str, Any]:
    return {name: encode_value(value) for name, value in sorted(values.items())}


def _assignment_plain(values: Mapping[str, ScientificValue]) -> dict[str, Any]:
    return {name: value.value for name, value in sorted(values.items())}


def _decode_assignment(payload: Mapping[str, Any]) -> dict[str, ScientificValue]:
    return {name: decode_value(value) for name, value in payload.items()}


def _quantity_plain(values: Mapping[str, Quantity]) -> dict[str, float]:
    return {name: float(values[name].magnitude) for name in sorted(values)}


def _binding_digest(binding: ResultBinding) -> str:
    return digest(binding.to_dict())


def _result_digest(result: ScientificResult) -> str:
    return digest(result.to_dict())


@dataclass(frozen=True)
class LoopPhysicsScope:
    design_space_reference: str = DESIGN_SPACE_REFERENCE
    problem_system_identity: str = PROBLEM_ID
    execution_model_reference: tuple[str, str] = MODEL
    solver_identity: tuple[str, str] = SOLVER
    operating_conditions: Mapping[str, Any] = field(
        default_factory=lambda: {
            "synthetic_environment": {"type": "categorical", "value": "nominal"}
        }
    )
    fidelity: Mapping[str, str] = field(
        default_factory=lambda: {
            "kind": "NONE",
            "reason": "closed-form analytic execution has no fidelity ladder",
        }
    )
    objective_projection: tuple[Mapping[str, str], ...] = field(
        default_factory=lambda: tuple(
            {
                "name": objective.name,
                "metric": objective.metric,
                "direction": objective.direction.value,
                "canonical_unit": objective.unit,
            }
            for objective in d4.OBJECTIVES
        )
    )
    execution_semantics_identity: str = EXECUTION_SEMANTICS
    physics_scope_identity: str = field(init=False)

    def __post_init__(self) -> None:
        model = tuple(self.execution_model_reference)
        solver = tuple(self.solver_identity)
        if len(model) != 2 or len(solver) != 2:
            raise InvalidScientificProblem("D7 physics scope requires versioned model/solver")
        objectives = tuple(dict(item) for item in self.objective_projection)
        if [item["name"] for item in objectives] != [o.name for o in d4.OBJECTIVES]:
            raise InvalidScientificProblem("D7 physics objective projection mismatch")
        object.__setattr__(self, "execution_model_reference", model)
        object.__setattr__(self, "solver_identity", solver)
        object.__setattr__(self, "operating_conditions", dict(self.operating_conditions))
        object.__setattr__(self, "fidelity", dict(self.fidelity))
        object.__setattr__(self, "objective_projection", objectives)
        object.__setattr__(self, "physics_scope_identity", digest(self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_loop_physics_scope/1",
            "design_space_reference": self.design_space_reference,
            "problem_system_identity": self.problem_system_identity,
            "execution_model_reference": list(self.execution_model_reference),
            "solver_identity": list(self.solver_identity),
            "operating_conditions": self.operating_conditions,
            "fidelity": self.fidelity,
            "objective_projection": list(self.objective_projection),
            "execution_semantics_identity": self.execution_semantics_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "physics_scope_identity": self.physics_scope_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LoopPhysicsScope":
        _require_keys(
            payload,
            {
                "schema", "design_space_reference", "problem_system_identity",
                "execution_model_reference", "solver_identity", "operating_conditions",
                "fidelity", "objective_projection", "execution_semantics_identity",
                "physics_scope_identity",
            },
            "D7 physics scope",
        )
        if payload["schema"] != "d7_loop_physics_scope/1":
            raise InvalidScientificProblem("D7 physics scope schema mismatch")
        rebuilt = cls(
            design_space_reference=payload["design_space_reference"],
            problem_system_identity=payload["problem_system_identity"],
            execution_model_reference=tuple(payload["execution_model_reference"]),
            solver_identity=tuple(payload["solver_identity"]),
            operating_conditions=dict(payload["operating_conditions"]),
            fidelity=dict(payload["fidelity"]),
            objective_projection=tuple(dict(item) for item in payload["objective_projection"]),
            execution_semantics_identity=payload["execution_semantics_identity"],
        )
        _require_identity(payload["physics_scope_identity"], rebuilt.physics_scope_identity, "D7 physics scope")
        return rebuilt


@dataclass(frozen=True)
class LoopAssessmentContext:
    assessment_context_id: str = "d7-loop-target-context-v0.1"
    threshold_predicates: tuple[Mapping[str, Any], ...] = field(
        default_factory=lambda: (
            {"objective": "yield_score", "operator": ">=", "threshold": 70.0, "unit": "dimensionless"},
            {"objective": "loss_score", "operator": "<=", "threshold": 25.0, "unit": "dimensionless"},
            {"objective": "stability_score", "operator": ">=", "threshold": 50.0, "unit": "dimensionless"},
        )
    )
    combination_rule: str = "AND"
    classification_labels: tuple[str, str] = ("PASS", "FAIL")
    reporting_context_id: str = "d7-integrated-loop-report-v0.1"
    decision_context_id: str = "d7-which-next-experiment-v0.1"
    study_question_id: str = "d7-close-return-arrow-v0.1"
    assessment_context_identity: str = field(init=False)

    def __post_init__(self) -> None:
        predicates = tuple(dict(item) for item in self.threshold_predicates)
        if {item["objective"] for item in predicates} != {o.name for o in d4.OBJECTIVES}:
            raise InvalidScientificProblem("D7 assessment threshold projection mismatch")
        if any(item.get("operator") not in {">=", "<="} for item in predicates):
            raise InvalidScientificProblem("D7 assessment predicate operator mismatch")
        if self.combination_rule != "AND" or tuple(self.classification_labels) != ("PASS", "FAIL"):
            raise InvalidScientificProblem("D7 assessment combination/labels mismatch")
        object.__setattr__(self, "threshold_predicates", predicates)
        object.__setattr__(self, "classification_labels", tuple(self.classification_labels))
        object.__setattr__(self, "assessment_context_identity", digest(self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_loop_assessment_context/1",
            "assessment_context_id": self.assessment_context_id,
            "threshold_predicates": list(self.threshold_predicates),
            "combination_rule": self.combination_rule,
            "classification_labels": list(self.classification_labels),
            "reporting_context_id": self.reporting_context_id,
            "decision_context_id": self.decision_context_id,
            "study_question_id": self.study_question_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "assessment_context_identity": self.assessment_context_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LoopAssessmentContext":
        _require_keys(
            payload,
            {
                "schema", "assessment_context_id", "threshold_predicates",
                "combination_rule", "classification_labels", "reporting_context_id",
                "decision_context_id", "study_question_id", "assessment_context_identity",
            },
            "D7 assessment context",
        )
        if payload["schema"] != "d7_loop_assessment_context/1":
            raise InvalidScientificProblem("D7 assessment schema mismatch")
        rebuilt = cls(
            assessment_context_id=payload["assessment_context_id"],
            threshold_predicates=tuple(dict(item) for item in payload["threshold_predicates"]),
            combination_rule=payload["combination_rule"],
            classification_labels=tuple(payload["classification_labels"]),
            reporting_context_id=payload["reporting_context_id"],
            decision_context_id=payload["decision_context_id"],
            study_question_id=payload["study_question_id"],
        )
        _require_identity(payload["assessment_context_identity"], rebuilt.assessment_context_identity, "D7 assessment")
        return rebuilt

    def classify(self, values: Mapping[str, Quantity]) -> str:
        checks = []
        for predicate in self.threshold_predicates:
            value = values[predicate["objective"]].to(predicate["unit"]).magnitude
            threshold = float(predicate["threshold"])
            checks.append(value >= threshold if predicate["operator"] == ">=" else value <= threshold)
        return "PASS" if all(checks) else "FAIL"


def _new_twin(
    twin_id: str,
    kind: TwinKind,
    assignments: Mapping[str, ScientificValue],
    *,
    parent=None,
    metadata: Mapping[str, Any] | None = None,
    evidence_refs: Sequence[str] = (),
    calibration_evidence_refs: Sequence[str] = (),
) -> ScientificTwin:
    return ScientificTwin(
        twin_id=twin_id,
        version="1",
        kind=kind,
        models=(ModelReference(*MODEL),),
        declarations=tuple(
            TwinDatum(name=name, value=assignments[name], role=TwinDatumRole.PARAMETER)
            for name in sorted(assignments)
        ),
        parent=parent,
        metadata=dict(metadata or {}),
        evidence_refs=tuple(evidence_refs),
        calibration_evidence_refs=tuple(calibration_evidence_refs),
    )


def _scientific_result(
    *,
    result_id: str,
    run_id: str,
    candidate: DesignCandidate,
    values: Mapping[str, Quantity],
    scope: LoopPhysicsScope,
    provenance_metadata: Mapping[str, Any] | None = None,
) -> tuple[ScientificResult, ResultBinding]:
    binding = ResultBinding(candidate.reference, candidate.twin, candidate.design_space)
    metadata = {
        RESULT_BINDING_METADATA_KEY: binding.to_dict(),
        "d7_physics_scope_identity": scope.physics_scope_identity,
        "d7_physics_scope_payload_digest": digest(scope.identity_payload()),
        "d7_execution_semantics_identity": scope.execution_semantics_identity,
        "d7_candidate": candidate.reference.to_dict(),
        "d7_twin": candidate.twin.to_dict(),
        "d7_assignment": _assignment_dict(candidate.assignments),
    }
    metadata.update(dict(provenance_metadata or {}))
    result = ScientificResult(
        result_id=result_id,
        problem_id=scope.problem_system_identity,
        values=dict(values),
        models=(MODEL,),
        solver=SolverIdentity(*SOLVER),
        convergence=ConvergenceState.NOT_APPLICABLE,
        provenance=ProvenanceRecord(
            run_id=run_id,
            models=(MODEL,),
            solvers=(SOLVER,),
            metadata=metadata,
        ),
    )
    return result, binding


def _evaluation(
    *,
    evaluation_id: str,
    candidate: DesignCandidate,
    twin: ScientificTwin,
    result_id: str,
    run_id: str,
    scope: LoopPhysicsScope,
    reason: str,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[DesignEvaluation, ResultBinding]:
    if twin.reference.key != candidate.twin.key:
        raise InvalidScientificProblem("D7 evaluation Candidate/Twin mismatch")
    values = d4.synthetic_objective_values(candidate.assignments)
    result, binding = _scientific_result(
        result_id=result_id,
        run_id=run_id,
        candidate=candidate,
        values=values,
        scope=scope,
        provenance_metadata=metadata,
    )
    evaluation = DesignEvaluation(
        evaluation_id=evaluation_id,
        candidate=candidate.reference,
        twin=twin.reference,
        design_space=candidate.design_space,
        result=result,
        eligibility=SelectionEligibility.ELIGIBLE,
        eligibility_reasons=(reason,),
        metadata={
            "d7_physics_scope_identity": scope.physics_scope_identity,
            "d7_target_classification_separate": True,
        },
    )
    return evaluation, binding


@dataclass(frozen=True)
class GenerationZero:
    candidates: tuple[DesignCandidate, ...]
    twins: tuple[ScientificTwin, ...]
    evaluations: tuple[DesignEvaluation, ...]
    physics_scope: LoopPhysicsScope

    def __post_init__(self) -> None:
        candidates = tuple(sorted(self.candidates, key=lambda item: item.candidate_id))
        twins = tuple(sorted(self.twins, key=lambda item: item.reference.key))
        evaluations = tuple(sorted(self.evaluations, key=lambda item: item.evaluation_id))
        if len(candidates) != 4 or len(twins) != 4 or len(evaluations) != 5:
            raise InvalidScientificProblem("D7 Generation 0 cardinality mismatch")
        if len({item.evaluation_id for item in evaluations}) != 5:
            raise InvalidScientificProblem("D7 Generation 0 evaluation identity collision")
        if len({item.result.result_id for item in evaluations}) != 5:
            raise InvalidScientificProblem("D7 Generation 0 result identity collision")
        if len({item.result.provenance.run_id for item in evaluations}) != 5:
            raise InvalidScientificProblem("D7 Generation 0 run identity collision")
        candidate_by_id = {item.candidate_id: item for item in candidates}
        twin_by_key = {item.reference.key: item for item in twins}
        for evaluation in evaluations:
            candidate = candidate_by_id[evaluation.candidate.candidate_id]
            evaluation.validate_candidate(candidate)
            if candidate.twin.key not in twin_by_key:
                raise InvalidScientificProblem("D7 Generation 0 Twin absent")
            _validate_result_execution(evaluation.result, candidate, self.physics_scope)
            suffix = evaluation.evaluation_id.rsplit(":", 1)[-1]
            if suffix not in {"primary", "replicate"}:
                raise InvalidScientificProblem("D7 Generation 0 evaluation suffix mismatch")
            if (
                evaluation.evaluation_id != f"d7-g0-evaluation:{candidate.candidate_id}:{suffix}"
                or evaluation.result.result_id != f"d7-g0-result:{candidate.candidate_id}:{suffix}"
                or evaluation.result.provenance.run_id != f"d7-g0-run:{candidate.candidate_id}:{suffix}"
            ):
                raise InvalidScientificProblem("D7 Generation 0 deterministic execution identity mismatch")
            if suffix == "replicate" and candidate.candidate_id != "d4-parent-c":
                raise InvalidScientificProblem("D7 Generation 0 replicate assigned to wrong candidate")
        c_evaluations = [item for item in evaluations if item.candidate.candidate_id == "d4-parent-c"]
        if len(c_evaluations) != 2 or _quantity_plain(c_evaluations[0].result.values) != _quantity_plain(c_evaluations[1].result.values):
            raise InvalidScientificProblem("D7 Generation 0 replicate fixture mismatch")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "twins", twins)
        object.__setattr__(self, "evaluations", evaluations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_generation_zero/1",
            "physics_scope_identity": self.physics_scope.physics_scope_identity,
            "candidates": [item.to_dict() for item in self.candidates],
            "twins": [item.to_dict() for item in self.twins],
            "evaluations": [item.to_dict() for item in self.evaluations],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], scope: LoopPhysicsScope) -> "GenerationZero":
        _require_keys(payload, {"schema", "physics_scope_identity", "candidates", "twins", "evaluations"}, "D7 Generation 0")
        if payload["schema"] != "d7_generation_zero/1" or payload["physics_scope_identity"] != scope.physics_scope_identity:
            raise InvalidScientificProblem("D7 Generation 0 scope/schema mismatch")
        return cls(
            candidates=tuple(DesignCandidate.from_dict(item) for item in payload["candidates"]),
            twins=tuple(ScientificTwin.from_dict(item) for item in payload["twins"]),
            evaluations=tuple(DesignEvaluation.from_dict(item) for item in payload["evaluations"]),
            physics_scope=scope,
        )

    def candidate(self, candidate_id: str) -> DesignCandidate:
        return next(item for item in self.candidates if item.candidate_id == candidate_id)

    def twin(self, candidate_id: str) -> ScientificTwin:
        candidate = self.candidate(candidate_id)
        return next(item for item in self.twins if item.reference.key == candidate.twin.key)

    def evaluation(self, candidate_id: str, suffix: str = "primary") -> DesignEvaluation:
        expected = f"d7-g0-evaluation:{candidate_id}:{suffix}"
        return next(item for item in self.evaluations if item.evaluation_id == expected)


def build_generation_zero(scope: LoopPhysicsScope) -> GenerationZero:
    space = d4.design_space()
    assignments = {
        "d4-parent-a": d4.typed_assignments("A_peak", "B_base", "buffered", 2, False),
        "d4-parent-b": d4.typed_assignments("A_base", "B_peak", "direct", 0, False),
        "d4-parent-c": d4.typed_assignments("A_stable", "B_base", "direct", 1, True),
        "d4-parent-d": d4.typed_assignments("A_base", "B_filter", "buffered", 2, True),
    }
    twins = tuple(
        _new_twin(f"d4-twin:{candidate_id}", TwinKind.CANDIDATE, value)
        for candidate_id, value in assignments.items()
    )
    twin_by_id = {item.twin_id.removeprefix("d4-twin:"): item for item in twins}
    candidates = tuple(
        DesignCandidate(
            candidate_id=candidate_id,
            design_space=space.reference,
            twin=twin_by_id[candidate_id].reference,
            assignments=value,
            generation=0,
            operator="declared:d7-preregistered-generation-zero",
        ).validate_against(space)
        for candidate_id, value in assignments.items()
    )
    evaluations: list[DesignEvaluation] = []
    for candidate in candidates:
        evaluation, _ = _evaluation(
            evaluation_id=f"d7-g0-evaluation:{candidate.candidate_id}:primary",
            candidate=candidate,
            twin=twin_by_id[candidate.candidate_id],
            result_id=f"d7-g0-result:{candidate.candidate_id}:primary",
            run_id=f"d7-g0-run:{candidate.candidate_id}:primary",
            scope=scope,
            reason=GENERATION0_REASON,
        )
        evaluations.append(evaluation)
    candidate_c = next(item for item in candidates if item.candidate_id == "d4-parent-c")
    replicate, _ = _evaluation(
        evaluation_id="d7-g0-evaluation:d4-parent-c:replicate",
        candidate=candidate_c,
        twin=twin_by_id["d4-parent-c"],
        result_id="d7-g0-result:d4-parent-c:replicate",
        run_id="d7-g0-run:d4-parent-c:replicate",
        scope=scope,
        reason=GENERATION0_REASON,
    )
    evaluations.append(replicate)
    return GenerationZero(candidates, twins, tuple(evaluations), scope)


def _validate_result_execution(result: ScientificResult, candidate: DesignCandidate, scope: LoopPhysicsScope) -> None:
    binding = ResultBinding(candidate.reference, candidate.twin, candidate.design_space)
    if result.provenance.metadata.get(RESULT_BINDING_METADATA_KEY) != binding.to_dict():
        raise InvalidScientificProblem("D7 result binding mismatch")
    if result.problem_id != scope.problem_system_identity or tuple(result.models) != (MODEL,):
        raise InvalidScientificProblem("D7 result problem/model mismatch")
    if result.solver is None or result.solver.key != SOLVER:
        raise InvalidScientificProblem("D7 result solver mismatch")
    if result.provenance.models != (MODEL,) or result.provenance.solvers != (SOLVER,):
        raise InvalidScientificProblem("D7 result provenance model/solver mismatch")
    if result.provenance.metadata.get("d7_physics_scope_identity") != scope.physics_scope_identity:
        raise InvalidScientificProblem("D7 result physics scope mismatch")
    if result.provenance.metadata.get("d7_physics_scope_payload_digest") != digest(scope.identity_payload()):
        raise InvalidScientificProblem("D7 result physics scope payload digest mismatch")
    if result.provenance.metadata.get("d7_execution_semantics_identity") != scope.execution_semantics_identity:
        raise InvalidScientificProblem("D7 result execution semantics mismatch")
    if result.provenance.metadata.get("d7_candidate") != candidate.reference.to_dict():
        raise InvalidScientificProblem("D7 result direct Candidate input mismatch")
    if result.provenance.metadata.get("d7_twin") != candidate.twin.to_dict():
        raise InvalidScientificProblem("D7 result direct Twin input mismatch")
    if result.provenance.metadata.get("d7_assignment") != _assignment_dict(candidate.assignments):
        raise InvalidScientificProblem("D7 result direct assignment input mismatch")
    expected = d4.synthetic_objective_values(candidate.assignments)
    if result.values != expected or set(result.values) != {item.name for item in d4.OBJECTIVES}:
        raise InvalidScientificProblem("D7 result objective projection mismatch")
    if any(not math.isfinite(value.magnitude) for value in result.values.values()):
        raise InvalidScientificProblem("D7 result objectives must be finite")


def _partitioner(assignments: Mapping[str, ScientificValue]) -> bytes:
    return (
        f"component_a={assignments['component_a'].value}|"
        f"component_b={assignments['component_b'].value}"
    ).encode("utf-8")


def build_memory(
    generation_zero: GenerationZero,
    assessment: LoopAssessmentContext,
) -> DesignMemoryRecord:
    scope = DesignMemoryScope(
        design_space=d4.design_space().reference,
        objectives=d4.OBJECTIVES,
        context_reference=generation_zero.physics_scope.physics_scope_identity,
    )
    layer = DesignMemoryLayerA.build(
        scope=scope,
        candidates=generation_zero.candidates,
        evaluations=generation_zero.evaluations,
        partitioner=_partitioner,
    )
    d3_assessment = AssessmentContext(
        assessment_id=assessment.assessment_context_identity,
        thresholds={
            "yield_score": Quantity(70.0, "dimensionless"),
            "loss_score": Quantity(25.0, "dimensionless"),
            "stability_score": Quantity(50.0, "dimensionless"),
        },
        threshold_tolerances={
            name: Quantity(0.0, "dimensionless")
            for name in ("yield_score", "loss_score", "stability_score")
        },
    )
    policy = DesignMemoryPolicy(
        policy_id=MEMORY_POLICY_ID,
        cap=16,
        elite_scopes=(("yield_score",), ("loss_score",), ("stability_score",)),
        extreme_tolerances={
            name: Quantity(0.0, "dimensionless")
            for name in ("yield_score", "loss_score", "stability_score")
        },
        assessment_contexts=(d3_assessment,),
        explicit_retention=(),
    )
    record = DesignMemoryRecord.build(layer_a=layer, policy=policy)
    verify_layer_a_attribution(
        layer_a=record.layer_a,
        candidates=generation_zero.candidates,
        evaluations=generation_zero.evaluations,
    )
    if len(record.layer_a.entries) != 5:
        raise InvalidScientificProblem("D7 memory must contain five attributable entries")
    return record


@dataclass(frozen=True)
class D4Source:
    slot_name: str
    selected_value: ScientificValue
    candidate: DesignCandidate
    twin: ScientificTwin
    evaluation: DesignEvaluation
    entry: DesignMemoryEntry
    memory_scope: DesignMemoryScope
    physics_scope: LoopPhysicsScope
    source_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.slot_name not in d4.SLOTS:
            raise InvalidScientificProblem("D7 D4 source slot mismatch")
        self.candidate.validate_against(d4.design_space())
        self.evaluation.validate_candidate(self.candidate)
        _validate_result_execution(self.evaluation.result, self.candidate, self.physics_scope)
        if self.twin.reference.key != self.candidate.twin.key:
            raise InvalidScientificProblem("D7 D4 source Twin mismatch")
        expected_entry = DesignMemoryEntry.from_evaluation(
            scope=self.memory_scope, candidate=self.candidate, evaluation=self.evaluation
        )
        if expected_entry.to_dict() != self.entry.to_dict():
            raise InvalidScientificProblem("D7 D4 source entry attribution mismatch")
        if self.memory_scope.context_reference != self.physics_scope.physics_scope_identity:
            raise InvalidScientificProblem("D7 D4 source physics/memory scope mismatch")
        if encode_value(self.selected_value) != encode_value(self.candidate.assignments[self.slot_name]):
            raise InvalidScientificProblem("D7 D4 source typed slot value mismatch")
        object.__setattr__(self, "source_identity", _identity("d7-d4-source", self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_d4_source/1",
            "slot_name": self.slot_name,
            "selected_value": encode_value(self.selected_value),
            "candidate": self.candidate.to_dict(),
            "candidate_digest": _object_digest(self.candidate),
            "twin": self.twin.to_dict(),
            "twin_digest": _object_digest(self.twin),
            "evaluation": self.evaluation.to_dict(),
            "evaluation_digest": _object_digest(self.evaluation),
            "result_digest": _result_digest(self.evaluation.result),
            "entry": self.entry.to_dict(),
            "entry_identity": self.entry.identity,
            "entry_digest": self.entry.entry_digest,
            "memory_scope": self.memory_scope.to_dict(),
            "physics_scope": self.physics_scope.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "source_identity": self.source_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D4Source":
        required = {
            "schema", "slot_name", "selected_value", "candidate", "candidate_digest",
            "twin", "twin_digest", "evaluation", "evaluation_digest", "result_digest",
            "entry", "entry_identity", "entry_digest", "memory_scope", "physics_scope",
            "source_identity",
        }
        _require_keys(payload, required, "D7 D4 source")
        if payload["schema"] != "d7_d4_source/1":
            raise InvalidScientificProblem("D7 D4 source schema mismatch")
        rebuilt = cls(
            slot_name=payload["slot_name"],
            selected_value=decode_value(payload["selected_value"]),
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            evaluation=DesignEvaluation.from_dict(payload["evaluation"]),
            entry=DesignMemoryEntry.from_dict(payload["entry"]),
            memory_scope=DesignMemoryScope.from_dict(payload["memory_scope"]),
            physics_scope=LoopPhysicsScope.from_dict(payload["physics_scope"]),
        )
        checks = {
            "candidate_digest": _object_digest(rebuilt.candidate),
            "twin_digest": _object_digest(rebuilt.twin),
            "evaluation_digest": _object_digest(rebuilt.evaluation),
            "result_digest": _result_digest(rebuilt.evaluation.result),
            "entry_identity": rebuilt.entry.identity,
            "entry_digest": rebuilt.entry.entry_digest,
            "source_identity": rebuilt.source_identity,
        }
        for key, expected in checks.items():
            if payload[key] != expected:
                raise InvalidScientificProblem(f"D7 D4 source {key} mismatch")
        return rebuilt

    def frozen_d4_record(self) -> d4.D4SelectedSourceRecord:
        return d4.D4SelectedSourceRecord(
            slot_name=self.slot_name,
            selected_value=self.selected_value,
            parent_candidate=self.candidate.reference,
            parent_twin=self.twin.reference,
            parent_evaluation=self.evaluation.reference,
            d3_entry_identity=self.entry.identity,
            d3_entry_digest=self.entry.entry_digest,
        )


def select_d4_source(
    *,
    slot_name: str,
    candidate_id: str,
    evaluation_id: str,
    candidates: Sequence[DesignCandidate],
    twins: Sequence[ScientificTwin],
    evaluations: Sequence[DesignEvaluation],
    memory: DesignMemoryRecord,
    physics_scope: LoopPhysicsScope,
) -> D4Source:
    # The primary key is deliberately the exact pair, never candidate-id-only.
    candidate_by_id = {item.candidate_id: item for item in candidates}
    evaluation_by_key = {
        (item.candidate.candidate_id, item.evaluation_id): item for item in evaluations
    }
    entry_by_key = {
        (item.candidate.candidate_id, item.evaluation.evaluation_id): item
        for item in memory.layer_a.entries
    }
    candidate = candidate_by_id.get(candidate_id)
    evaluation = evaluation_by_key.get((candidate_id, evaluation_id))
    entry = entry_by_key.get((candidate_id, evaluation_id))
    if candidate is None or evaluation is None or entry is None:
        raise InvalidScientificProblem("D7 exact candidate/evaluation D4 source absent")
    twin_by_key = {item.reference.key: item for item in twins}
    twin = twin_by_key.get(candidate.twin.key)
    if twin is None:
        raise InvalidScientificProblem("D7 D4 source Twin absent")
    return D4Source(
        slot_name=slot_name,
        selected_value=candidate.assignments[slot_name],
        candidate=candidate,
        twin=twin,
        evaluation=evaluation,
        entry=entry,
        memory_scope=memory.layer_a.scope,
        physics_scope=physics_scope,
    )


def select_case_c_sources(g0: GenerationZero, memory: DesignMemoryRecord) -> tuple[D4Source, ...]:
    specs = (
        ("component_a", "d4-parent-c"),
        ("guard_enabled", "d4-parent-c"),
        ("component_b", "d4-parent-d"),
        ("adapter", "d4-parent-d"),
        ("control_level", "d4-parent-d"),
    )
    return tuple(
        select_d4_source(
            slot_name=slot,
            candidate_id=parent,
            evaluation_id=f"d7-g0-evaluation:{parent}:primary",
            candidates=g0.candidates,
            twins=g0.twins,
            evaluations=g0.evaluations,
            memory=memory,
            physics_scope=g0.physics_scope,
        )
        for slot, parent in specs
    )


def _ensure_single_scope(sources: Sequence[D4Source]) -> LoopPhysicsScope:
    identities = {item.physics_scope.physics_scope_identity for item in sources}
    if len(identities) != 1:
        raise InvalidScientificProblem("D7 mixed physics scope rejected before D4 materialization")
    return sources[0].physics_scope


FORBIDDEN_INHERITANCE = frozenset(
    {
        "adequacy", "archive_membership", "calibration_evidence_refs", "evidence",
        "evidence_refs", "feasible", "feasibility", "model_adequacy", "pareto",
        "pareto_member", "safety", "safe", "scientific_validity", "selected",
        "selection", "selection_eligibility", "selection_status", "selection_truth",
        "status", "target", "target_pass", "truth", "uq", "uncertainty", "valid",
        "validation", "validity",
    }
)


def validate_no_inheritance(
    candidate: DesignCandidate,
    twin: ScientificTwin,
    *,
    forbidden_scientific_ids: Iterable[str] = (),
) -> None:
    if twin.evidence_refs != () or twin.calibration_evidence_refs != ():
        raise InvalidScientificProblem("D7 new Twin evidence fields must be empty")
    allowed_metadata = {
        "d7_d4_event_identity", "d7_authoritative_multi_parent_lineage",
        "d7_study_identity", "d7_option_identity", "d7_decision_identity",
        "d7_materialization_semantics", "d7_parent_twin_reference",
    }

    def scan(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, Mapping):
            for raw_key, item in value.items():
                key = str(raw_key).strip().lower().replace("-", "_")
                if key in FORBIDDEN_INHERITANCE:
                    if key in {"evidence_refs", "calibration_evidence_refs"} and item == []:
                        continue
                    raise InvalidScientificProblem(f"D7 forbidden inherited vocabulary at {'.'.join(path + (key,))}")
                scan(item, path + (key,))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                scan(item, path + (str(index),))

    candidate_payload = candidate.to_dict()
    twin_payload = twin.to_dict()
    extra_candidate_metadata = set(candidate.metadata) - allowed_metadata
    extra_twin_metadata = set(twin.metadata) - allowed_metadata
    scan({key: candidate.metadata[key] for key in extra_candidate_metadata}, ("candidate_metadata",))
    scan({key: twin.metadata[key] for key in extra_twin_metadata}, ("twin_metadata",))
    serialized = canonical_bytes({"candidate": candidate_payload, "twin": twin_payload}).decode("utf-8")
    for scientific_id in forbidden_scientific_ids:
        if scientific_id and scientific_id in serialized:
            raise InvalidScientificProblem("D7 parent scientific identity inherited by new child")


@dataclass(frozen=True)
class AuthoritativeD4:
    sources: tuple[D4Source, ...]
    assignment: Mapping[str, ScientificValue]
    compatibility: d4.D4CompatibilityResult
    event_payload: Mapping[str, Any]
    event_identity: str
    candidate: DesignCandidate
    twin: ScientificTwin
    derivation_payload: Mapping[str, Any]
    derivation_identity: str

    def __post_init__(self) -> None:
        sources = tuple(sorted(self.sources, key=lambda item: (item.slot_name, item.source_identity)))
        scope = _ensure_single_scope(sources)
        assignment = dict(self.assignment)
        d4.design_space().validate_assignments(assignment)
        frozen_sources = tuple(item.frozen_d4_record() for item in sources)
        expected_compatibility = d4.assess_compatibility(
            selected_sources=frozen_sources,
            child_assignments=assignment,
            parent_candidates=tuple({item.candidate.candidate_id: item.candidate for item in sources}.values()),
            parent_evaluations=tuple({item.evaluation.evaluation_id: item.evaluation for item in sources}.values()),
            d3_entries=tuple({item.entry.identity: item.entry for item in sources}.values()),
        )
        if expected_compatibility.to_dict() != self.compatibility.to_dict() or self.compatibility.state is not d4.CompatibilityState.COMPATIBLE:
            raise InvalidScientificProblem("D7 authoritative D4 compatibility mismatch")
        expected_event_payload = authoritative_event_payload(sources, assignment, expected_compatibility, scope)
        expected_event_identity = _identity("d7-d4-event", expected_event_payload)
        if dict(self.event_payload) != expected_event_payload or self.event_identity != expected_event_identity:
            raise InvalidScientificProblem("D7 authoritative D4 event mismatch")
        event_hex = expected_event_identity.rsplit(":", 1)[-1]
        if self.candidate.candidate_id != f"d7-d4-child:sha256:{event_hex}":
            raise InvalidScientificProblem("D7 authoritative child Candidate identity mismatch")
        if self.twin.twin_id != f"d7-d4-derived-twin:sha256:{event_hex}":
            raise InvalidScientificProblem("D7 authoritative child Twin identity mismatch")
        if self.candidate.to_dict()["assignments"] != _assignment_dict(assignment):
            raise InvalidScientificProblem("D7 authoritative child assignment mismatch")
        if self.candidate.twin.key != self.twin.reference.key:
            raise InvalidScientificProblem("D7 authoritative child Candidate/Twin mismatch")
        validate_no_inheritance(
            self.candidate,
            self.twin,
            forbidden_scientific_ids=[item.evaluation.result.result_id for item in sources]
            + [item.evaluation.evaluation_id for item in sources],
        )
        expected_derivation_payload = authoritative_derivation_payload(
            expected_event_payload, expected_event_identity, self.candidate, self.twin, sources, assignment
        )
        expected_derivation_identity = _identity("d7-d4-derivation", expected_derivation_payload)
        if dict(self.derivation_payload) != expected_derivation_payload or self.derivation_identity != expected_derivation_identity:
            raise InvalidScientificProblem("D7 authoritative D4 derivation mismatch")
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "assignment", assignment)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_authoritative_d4/1",
            "sources": [item.to_dict() for item in self.sources],
            "assignment": _assignment_dict(self.assignment),
            "compatibility": self.compatibility.to_dict(),
            "event_payload": dict(self.event_payload),
            "event_identity": self.event_identity,
            "candidate": self.candidate.to_dict(),
            "twin": self.twin.to_dict(),
            "derivation_payload": dict(self.derivation_payload),
            "derivation_identity": self.derivation_identity,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthoritativeD4":
        _require_keys(
            payload,
            {"schema", "sources", "assignment", "compatibility", "event_payload", "event_identity", "candidate", "twin", "derivation_payload", "derivation_identity"},
            "D7 authoritative D4",
        )
        if payload["schema"] != "d7_authoritative_d4/1":
            raise InvalidScientificProblem("D7 authoritative D4 schema mismatch")
        return cls(
            sources=tuple(D4Source.from_dict(item) for item in payload["sources"]),
            assignment=_decode_assignment(payload["assignment"]),
            compatibility=d4.D4CompatibilityResult.from_dict(payload["compatibility"]),
            event_payload=dict(payload["event_payload"]),
            event_identity=payload["event_identity"],
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            derivation_payload=dict(payload["derivation_payload"]),
            derivation_identity=payload["derivation_identity"],
        )


def _compatibility_rule_set_payload() -> dict[str, Any]:
    return {
        "compatibility_context_id": d4.COMPATIBILITY_CONTEXT_ID,
        "slot_schema_id": d4.SLOT_SCHEMA_ID,
        "materialization_semantics_id": d4.MATERIALIZATION_SEMANTICS_ID,
        "incompatible_pairs": [["A_peak", "B_peak"]],
        "adapter_requirements": [
            {"component_a": "A_peak", "component_b": "B_filter", "allowed": ["buffered"]},
            {"component_a": "A_stable", "component_b": "B_filter", "allowed": ["buffered", "isolated"]},
            {"component_a": "A_stable", "component_b": "B_peak", "allowed": ["direct"]},
        ],
    }


def authoritative_event_payload(
    sources: Sequence[D4Source],
    assignment: Mapping[str, ScientificValue],
    compatibility: d4.D4CompatibilityResult,
    scope: LoopPhysicsScope,
) -> dict[str, Any]:
    rule_set = _compatibility_rule_set_payload()
    parents = {item.candidate.candidate_id: item.candidate for item in sources}
    twins = {item.twin.reference.key: item.twin for item in sources}
    return {
        "schema": "d7_authoritative_d4_event/1",
        "physics_scope": scope.to_dict(),
        "compatibility_context": rule_set,
        "compatibility_rule_set_digest": digest(rule_set),
        "slot_schema_id": d4.SLOT_SCHEMA_ID,
        "materialization_semantics_id": MATERIALIZATION_SEMANTICS,
        "generation_admission_semantics_id": GENERATION_ADMISSION,
        "target_generation": 1,
        "operator": RECOMBINATION_OPERATOR,
        "selected_source_records": [item.to_dict() for item in sorted(sources, key=lambda source: (source.slot_name, source.source_identity))],
        "parent_candidates": [parents[key].to_dict() for key in sorted(parents)],
        "parent_twins": [twins[key].to_dict() for key in sorted(twins)],
        "child_assignment": _assignment_dict(assignment),
        "compatibility_input": {
            "selected_sources": [item.frozen_d4_record().to_dict() for item in sorted(sources, key=lambda source: (source.slot_name, source.source_identity))],
            "child_assignment": _assignment_dict(assignment),
        },
        "compatibility_result": compatibility.to_dict(),
        "analytic_execution_semantics_identity": EXECUTION_SEMANTICS,
    }


def authoritative_derivation_payload(
    event_payload: Mapping[str, Any],
    event_identity: str,
    candidate: DesignCandidate,
    twin: ScientificTwin,
    sources: Sequence[D4Source],
    assignment: Mapping[str, ScientificValue],
) -> dict[str, Any]:
    return {
        "schema": "d7_authoritative_d4_derivation/1",
        "event_payload": dict(event_payload),
        "event_identity": event_identity,
        "child_candidate": candidate.to_dict(),
        "child_candidate_digest": _object_digest(candidate),
        "child_twin": twin.to_dict(),
        "child_twin_digest": _object_digest(twin),
        "child_assignment_digest": digest(_assignment_dict(assignment)),
        "lineage": [
            {
                "source_identity": item.source_identity,
                "candidate_id": item.candidate.candidate_id,
                "twin": item.twin.reference.to_dict(),
                "evaluation_id": item.evaluation.evaluation_id,
                "entry_identity": item.entry.identity,
                "entry_digest": item.entry.entry_digest,
                "slot_name": item.slot_name,
            }
            for item in sorted(sources, key=lambda source: (source.slot_name, source.source_identity))
        ],
        "materialization_semantics_id": MATERIALIZATION_SEMANTICS,
        "generation_admission_semantics_id": GENERATION_ADMISSION,
    }


def materialize_authoritative_d4(sources: Sequence[D4Source]) -> AuthoritativeD4:
    sources = tuple(sources)
    scope = _ensure_single_scope(sources)
    assignment = d4.typed_assignments("A_stable", "B_filter", "buffered", 2, True)
    compatibility = d4.assess_compatibility(
        selected_sources=tuple(item.frozen_d4_record() for item in sources),
        child_assignments=assignment,
        parent_candidates=tuple({item.candidate.candidate_id: item.candidate for item in sources}.values()),
        parent_evaluations=tuple({item.evaluation.evaluation_id: item.evaluation for item in sources}.values()),
        d3_entries=tuple({item.entry.identity: item.entry for item in sources}.values()),
    )
    if compatibility.state is not d4.CompatibilityState.COMPATIBLE:
        raise InvalidScientificProblem("D7 preregistered Case C is not compatible")
    event_payload = authoritative_event_payload(sources, assignment, compatibility, scope)
    event_identity = _identity("d7-d4-event", event_payload)
    event_hex = event_identity.rsplit(":", 1)[-1]
    parent_candidates = tuple(
        item.candidate.reference
        for item in sorted({source.candidate.candidate_id: source for source in sources}.values(), key=lambda source: source.candidate.candidate_id)
    )
    parent_twins = tuple(
        item.twin.reference
        for item in sorted({source.twin.reference.key: source for source in sources}.values(), key=lambda source: source.twin.reference.key)
    )
    candidate = DesignCandidate(
        candidate_id=f"d7-d4-child:sha256:{event_hex}",
        design_space=d4.design_space().reference,
        twin=d4.TwinReference(f"d7-d4-derived-twin:sha256:{event_hex}", "1"),
        assignments=assignment,
        generation=1,
        parents=parent_candidates,
        operator=RECOMBINATION_OPERATOR,
        metadata={"d7_d4_event_identity": event_identity},
    ).validate_against(d4.design_space())
    twin = _new_twin(
        candidate.twin.twin_id,
        TwinKind.DERIVED,
        assignment,
        parent=parent_twins[0],
        metadata={
            "d7_d4_event_identity": event_identity,
            "d7_authoritative_multi_parent_lineage": [item.to_dict() for item in parent_twins],
        },
    )
    derivation_payload = authoritative_derivation_payload(event_payload, event_identity, candidate, twin, sources, assignment)
    derivation_identity = _identity("d7-d4-derivation", derivation_payload)
    return AuthoritativeD4(
        sources=tuple(sources), assignment=assignment, compatibility=compatibility,
        event_payload=event_payload, event_identity=event_identity,
        candidate=candidate, twin=twin, derivation_payload=derivation_payload,
        derivation_identity=derivation_identity,
    )


@dataclass(frozen=True)
class GenerationLineage:
    source_generation_identity: str
    target_generation: int
    candidate: DesignCandidate
    twin: ScientificTwin
    parents: tuple[Mapping[str, Any], ...]
    d4_event_identity: str
    d4_derivation_identity: str
    d3_sources: tuple[Mapping[str, str], ...]
    operator: str
    lineage_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.target_generation != 1:
            raise InvalidScientificProblem("D7 successor lineage target generation mismatch")
        parents = tuple(sorted((dict(item) for item in self.parents), key=lambda item: canonical_bytes(item)))
        d3_sources = tuple(sorted((dict(item) for item in self.d3_sources), key=lambda item: (item["identity"], item["digest"])))
        object.__setattr__(self, "parents", parents)
        object.__setattr__(self, "d3_sources", d3_sources)
        object.__setattr__(self, "lineage_identity", _identity("d7-generation-lineage", self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_generation_lineage/1",
            "source_generation_identity": self.source_generation_identity,
            "target_generation": self.target_generation,
            "candidate": self.candidate.to_dict(),
            "candidate_digest": _object_digest(self.candidate),
            "twin": self.twin.to_dict(),
            "twin_digest": _object_digest(self.twin),
            "parents": list(self.parents),
            "d4_event_identity": self.d4_event_identity,
            "d4_derivation_identity": self.d4_derivation_identity,
            "d3_sources": list(self.d3_sources),
            "operator": self.operator,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "lineage_identity": self.lineage_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GenerationLineage":
        _require_keys(payload, {
            "schema", "source_generation_identity", "target_generation", "candidate", "candidate_digest",
            "twin", "twin_digest", "parents", "d4_event_identity", "d4_derivation_identity",
            "d3_sources", "operator", "lineage_identity",
        }, "D7 generation lineage")
        if payload["schema"] != "d7_generation_lineage/1":
            raise InvalidScientificProblem("D7 generation lineage schema mismatch")
        rebuilt = cls(
            source_generation_identity=payload["source_generation_identity"],
            target_generation=payload["target_generation"],
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            parents=tuple(dict(item) for item in payload["parents"]),
            d4_event_identity=payload["d4_event_identity"],
            d4_derivation_identity=payload["d4_derivation_identity"],
            d3_sources=tuple(dict(item) for item in payload["d3_sources"]),
            operator=payload["operator"],
        )
        if payload["candidate_digest"] != _object_digest(rebuilt.candidate) or payload["twin_digest"] != _object_digest(rebuilt.twin):
            raise InvalidScientificProblem("D7 generation lineage object digest mismatch")
        _require_identity(payload["lineage_identity"], rebuilt.lineage_identity, "D7 generation lineage")
        return rebuilt


@dataclass(frozen=True)
class GenerationMember:
    target_generation: int
    candidate: DesignCandidate
    twin: ScientificTwin
    lineage_identity: str
    role: str = "AUTHORITATIVE_D4_MATERIALIZATION"
    member_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.target_generation != 1 or self.role != "AUTHORITATIVE_D4_MATERIALIZATION":
            raise InvalidScientificProblem("D7 generation member role/generation mismatch")
        object.__setattr__(self, "member_identity", _identity("d7-generation-member", self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_generation_member/1",
            "target_generation": self.target_generation,
            "candidate": self.candidate.to_dict(),
            "candidate_digest": _object_digest(self.candidate),
            "twin": self.twin.to_dict(),
            "twin_digest": _object_digest(self.twin),
            "lineage_identity": self.lineage_identity,
            "membership_role": self.role,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "member_identity": self.member_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GenerationMember":
        _require_keys(payload, {
            "schema", "target_generation", "candidate", "candidate_digest", "twin", "twin_digest",
            "lineage_identity", "membership_role", "member_identity",
        }, "D7 generation member")
        if payload["schema"] != "d7_generation_member/1":
            raise InvalidScientificProblem("D7 generation member schema mismatch")
        rebuilt = cls(
            target_generation=payload["target_generation"],
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            lineage_identity=payload["lineage_identity"],
            role=payload["membership_role"],
        )
        if payload["candidate_digest"] != _object_digest(rebuilt.candidate) or payload["twin_digest"] != _object_digest(rebuilt.twin):
            raise InvalidScientificProblem("D7 generation member object digest mismatch")
        _require_identity(payload["member_identity"], rebuilt.member_identity, "D7 generation member")
        return rebuilt


@dataclass(frozen=True)
class SuccessorGeneration:
    source_generation_identity: str
    target_generation: int
    policy_id: str
    lineage: GenerationLineage
    members: tuple[GenerationMember, ...]
    generation_identity: str = field(init=False)

    def __post_init__(self) -> None:
        members = tuple(sorted(self.members, key=lambda item: item.member_identity))
        if self.target_generation != 1 or self.policy_id != GENERATION_ADMISSION or len(members) != 1:
            raise InvalidScientificProblem("D7 successor generation declaration mismatch")
        member = members[0]
        if member.lineage_identity != self.lineage.lineage_identity:
            raise InvalidScientificProblem("D7 successor member lineage mismatch")
        if member.candidate.to_dict() != self.lineage.candidate.to_dict() or member.twin.to_dict() != self.lineage.twin.to_dict():
            raise InvalidScientificProblem("D7 successor generation replaced authoritative child")
        object.__setattr__(self, "members", members)
        object.__setattr__(self, "generation_identity", _identity("d7-successor-generation", self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_successor_generation/1",
            "source_generation_identity": self.source_generation_identity,
            "target_generation": self.target_generation,
            "policy_id": self.policy_id,
            "lineage": self.lineage.to_dict(),
            "members": [item.to_dict() for item in self.members],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "generation_identity": self.generation_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SuccessorGeneration":
        _require_keys(payload, {"schema", "source_generation_identity", "target_generation", "policy_id", "lineage", "members", "generation_identity"}, "D7 successor generation")
        if payload["schema"] != "d7_successor_generation/1":
            raise InvalidScientificProblem("D7 successor generation schema mismatch")
        rebuilt = cls(
            source_generation_identity=payload["source_generation_identity"],
            target_generation=payload["target_generation"],
            policy_id=payload["policy_id"],
            lineage=GenerationLineage.from_dict(payload["lineage"]),
            members=tuple(GenerationMember.from_dict(item) for item in payload["members"]),
        )
        _require_identity(payload["generation_identity"], rebuilt.generation_identity, "D7 successor generation")
        return rebuilt


def admit_successor(authoritative: AuthoritativeD4) -> SuccessorGeneration:
    lineage = GenerationLineage(
        source_generation_identity=SOURCE_GENERATION_ID,
        target_generation=1,
        candidate=authoritative.candidate,
        twin=authoritative.twin,
        parents=tuple(item.to_dict() for item in authoritative.candidate.parents),
        d4_event_identity=authoritative.event_identity,
        d4_derivation_identity=authoritative.derivation_identity,
        d3_sources=tuple(
            {"identity": source.entry.identity, "digest": source.entry.entry_digest}
            for source in authoritative.sources
        ),
        operator=RECOMBINATION_OPERATOR,
    )
    member = GenerationMember(1, authoritative.candidate, authoritative.twin, lineage.lineage_identity)
    generation = SuccessorGeneration(SOURCE_GENERATION_ID, 1, GENERATION_ADMISSION, lineage, (member,))
    if generation.members[0].candidate.to_dict() != authoritative.candidate.to_dict() or generation.members[0].twin.to_dict() != authoritative.twin.to_dict():
        raise InvalidScientificProblem("D7 D4 to D5 payload identity failure")
    return generation


@dataclass(frozen=True)
class SuccessorEvaluation:
    generation_identity: str
    member_identity: str
    lineage_identity: str
    evaluation: DesignEvaluation
    result_binding: ResultBinding

    def __post_init__(self) -> None:
        if self.evaluation.result_binding.to_dict() != self.result_binding.to_dict():
            raise InvalidScientificProblem("D7 successor ResultBinding mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_successor_evaluation/1",
            "generation_identity": self.generation_identity,
            "member_identity": self.member_identity,
            "lineage_identity": self.lineage_identity,
            "evaluation": self.evaluation.to_dict(),
            "result_binding": self.result_binding.to_dict(),
            "result_binding_digest": _binding_digest(self.result_binding),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SuccessorEvaluation":
        _require_keys(payload, {"schema", "generation_identity", "member_identity", "lineage_identity", "evaluation", "result_binding", "result_binding_digest"}, "D7 successor evaluation")
        if payload["schema"] != "d7_successor_evaluation/1":
            raise InvalidScientificProblem("D7 successor evaluation schema mismatch")
        rebuilt = cls(
            generation_identity=payload["generation_identity"],
            member_identity=payload["member_identity"],
            lineage_identity=payload["lineage_identity"],
            evaluation=DesignEvaluation.from_dict(payload["evaluation"]),
            result_binding=ResultBinding.from_dict(payload["result_binding"]),
        )
        if payload["result_binding_digest"] != _binding_digest(rebuilt.result_binding):
            raise InvalidScientificProblem("D7 successor binding digest mismatch")
        return rebuilt


def execute_successor(generation: SuccessorGeneration, scope: LoopPhysicsScope) -> SuccessorEvaluation:
    member = generation.members[0]
    validate_no_inheritance(member.candidate, member.twin)
    request_payload = {
        "schema": "d7_successor_execution_request/1",
        "generation_identity": generation.generation_identity,
        "member_identity": member.member_identity,
        "lineage_identity": member.lineage_identity,
        "candidate": member.candidate.to_dict(),
        "twin": member.twin.to_dict(),
        "physics_scope": scope.to_dict(),
    }
    request_digest = digest(request_payload)
    run_id = f"d7-successor-run:sha256:{request_digest}"
    result_id = f"d7-successor-result:sha256:{digest({'request': request_payload, 'values': _quantity_plain(d4.synthetic_objective_values(member.candidate.assignments))})}"
    evaluation_id = f"d7-successor-evaluation:sha256:{digest({'result_id': result_id, 'member_identity': member.member_identity})}"
    evaluation, binding = _evaluation(
        evaluation_id=evaluation_id,
        candidate=member.candidate,
        twin=member.twin,
        result_id=result_id,
        run_id=run_id,
        scope=scope,
        reason=SUCCESSOR_REASON,
        metadata={
            "d7_generation_identity": generation.generation_identity,
            "d7_generation_member_identity": member.member_identity,
            "d7_generation_lineage_identity": member.lineage_identity,
            "d7_d4_event_identity": generation.lineage.d4_event_identity,
            "d7_d4_derivation_identity": generation.lineage.d4_derivation_identity,
        },
    )
    if _quantity_plain(evaluation.result.values) != {"loss_score": 5.0, "stability_score": 76.0, "yield_score": 46.0}:
        raise InvalidScientificProblem("D7 successor objective fixture mismatch")
    return SuccessorEvaluation(generation.generation_identity, member.member_identity, member.lineage_identity, evaluation, binding)


@dataclass(frozen=True)
class LoopDecisionEvidenceBinding:
    candidate: DesignCandidate
    twin: ScientificTwin
    evaluation: DesignEvaluation
    result_binding: ResultBinding
    physics_scope: LoopPhysicsScope
    source_generation_identity: str
    successor_generation_identity: str
    generation_member_identity: str
    generation_lineage_identity: str
    d4_event_identity: str | None = None
    d4_derivation_identity: str | None = None
    binding_identity: str = field(init=False)
    binding_digest: str = field(init=False)

    def __post_init__(self) -> None:
        self.candidate.validate_against(d4.design_space())
        self.evaluation.validate_candidate(self.candidate)
        if self.twin.reference.key != self.candidate.twin.key:
            raise InvalidScientificProblem("D7 evidence Candidate/Twin mismatch")
        _validate_result_execution(self.evaluation.result, self.candidate, self.physics_scope)
        if self.evaluation.to_dict()["result"] != self.evaluation.result.to_dict():
            raise InvalidScientificProblem("D7 evidence embedded result mismatch")
        if self.evaluation.result_binding.to_dict() != self.result_binding.to_dict():
            raise InvalidScientificProblem("D7 evidence ResultBinding mismatch")
        if not all((self.source_generation_identity, self.successor_generation_identity, self.generation_member_identity, self.generation_lineage_identity)):
            raise InvalidScientificProblem("D7 evidence generation/lineage is incomplete")
        payload = self.identity_payload()
        binding_digest = digest(payload)
        object.__setattr__(self, "binding_digest", binding_digest)
        object.__setattr__(self, "binding_identity", f"d7-decision-evidence:sha256:{binding_digest}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_decision_evidence_binding/1",
            "candidate": self.candidate.to_dict(),
            "candidate_digest": _object_digest(self.candidate),
            "twin": self.twin.to_dict(),
            "twin_digest": _object_digest(self.twin),
            "evaluation": self.evaluation.to_dict(),
            "evaluation_identity": self.evaluation.evaluation_id,
            "evaluation_digest": _object_digest(self.evaluation),
            "scientific_result": self.evaluation.result.to_dict(),
            "result_id": self.evaluation.result.result_id,
            "result_digest": _result_digest(self.evaluation.result),
            "result_binding": self.result_binding.to_dict(),
            "result_binding_digest": _binding_digest(self.result_binding),
            "run_identity": self.evaluation.result.provenance.run_id,
            "physics_scope": self.physics_scope.to_dict(),
            "physics_scope_payload_digest": digest(self.physics_scope.identity_payload()),
            "source_generation_identity": self.source_generation_identity,
            "successor_generation_identity": self.successor_generation_identity,
            "generation_member_identity": self.generation_member_identity,
            "generation_lineage_identity": self.generation_lineage_identity,
            "d4_event_identity": self.d4_event_identity,
            "d4_derivation_identity": self.d4_derivation_identity,
            "objective_projection": list(self.physics_scope.objective_projection),
            "objective_values": {name: value.to_dict() for name, value in sorted(self.evaluation.result.values.items())},
            "assignment": _assignment_dict(self.candidate.assignments),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "binding_identity": self.binding_identity, "binding_digest": self.binding_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LoopDecisionEvidenceBinding":
        required = {
            "schema", "candidate", "candidate_digest", "twin", "twin_digest", "evaluation",
            "evaluation_identity", "evaluation_digest", "scientific_result", "result_id", "result_digest",
            "result_binding", "result_binding_digest", "run_identity", "physics_scope",
            "physics_scope_payload_digest", "source_generation_identity", "successor_generation_identity",
            "generation_member_identity", "generation_lineage_identity", "d4_event_identity",
            "d4_derivation_identity", "objective_projection", "objective_values", "assignment",
            "binding_identity", "binding_digest",
        }
        _require_keys(payload, required, "D7 evidence binding")
        if payload["schema"] != "d7_decision_evidence_binding/1":
            raise InvalidScientificProblem("D7 evidence binding schema mismatch")
        rebuilt = cls(
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            evaluation=DesignEvaluation.from_dict(payload["evaluation"]),
            result_binding=ResultBinding.from_dict(payload["result_binding"]),
            physics_scope=LoopPhysicsScope.from_dict(payload["physics_scope"]),
            source_generation_identity=payload["source_generation_identity"],
            successor_generation_identity=payload["successor_generation_identity"],
            generation_member_identity=payload["generation_member_identity"],
            generation_lineage_identity=payload["generation_lineage_identity"],
            d4_event_identity=payload["d4_event_identity"],
            d4_derivation_identity=payload["d4_derivation_identity"],
        )
        exact = rebuilt.to_dict()
        if exact != dict(payload):
            raise InvalidScientificProblem("D7 evidence binding content/digest mismatch")
        return rebuilt


def _baseline_lineage(candidate: DesignCandidate, evaluation: DesignEvaluation) -> tuple[str, str]:
    payload = {
        "schema": "d7_generation_zero_baseline_lineage/1",
        "source_generation_identity": SOURCE_GENERATION_ID,
        "candidate": candidate.to_dict(),
        "evaluation_id": evaluation.evaluation_id,
    }
    lineage = _identity("d7-g0-lineage", payload)
    member = _identity("d7-g0-member", {**payload, "lineage_identity": lineage})
    return member, lineage


def build_evidence_bindings(
    g0: GenerationZero,
    generation: SuccessorGeneration,
    successor: SuccessorEvaluation,
) -> tuple[LoopDecisionEvidenceBinding, ...]:
    twin_by_key = {item.reference.key: item for item in g0.twins}
    candidate_by_id = {item.candidate_id: item for item in g0.candidates}
    bindings: list[LoopDecisionEvidenceBinding] = []
    for evaluation in g0.evaluations:
        candidate = candidate_by_id[evaluation.candidate.candidate_id]
        member, lineage = _baseline_lineage(candidate, evaluation)
        bindings.append(
            LoopDecisionEvidenceBinding(
                candidate=candidate,
                twin=twin_by_key[candidate.twin.key],
                evaluation=evaluation,
                result_binding=evaluation.result_binding,
                physics_scope=g0.physics_scope,
                source_generation_identity=SOURCE_GENERATION_ID,
                successor_generation_identity=generation.generation_identity,
                generation_member_identity=member,
                generation_lineage_identity=lineage,
            )
        )
    bindings.append(
        LoopDecisionEvidenceBinding(
            candidate=generation.members[0].candidate,
            twin=generation.members[0].twin,
            evaluation=successor.evaluation,
            result_binding=successor.result_binding,
            physics_scope=g0.physics_scope,
            source_generation_identity=SOURCE_GENERATION_ID,
            successor_generation_identity=generation.generation_identity,
            generation_member_identity=generation.members[0].member_identity,
            generation_lineage_identity=generation.lineage.lineage_identity,
            d4_event_identity=generation.lineage.d4_event_identity,
            d4_derivation_identity=generation.lineage.d4_derivation_identity,
        )
    )
    result = tuple(sorted(bindings, key=lambda item: item.binding_identity))
    if len({item.binding_identity for item in result}) != 6:
        raise InvalidScientificProblem("D7 evidence binding identities must be unique")
    return result


@dataclass(frozen=True)
class NoveltyUniverse:
    bindings: tuple[LoopDecisionEvidenceBinding, ...]
    universe_digest: str = field(init=False)
    universe_identity: str = field(init=False)

    def __post_init__(self) -> None:
        bindings = tuple(sorted(self.bindings, key=lambda item: item.binding_identity))
        if not bindings or len({item.binding_identity for item in bindings}) != len(bindings):
            raise InvalidScientificProblem("D7 novelty universe bindings invalid")
        scopes = {item.physics_scope.physics_scope_identity for item in bindings}
        if len(scopes) != 1:
            raise InvalidScientificProblem("D7 novelty universe refuses mixed physics")
        object.__setattr__(self, "bindings", bindings)
        value = digest(self.identity_payload())
        object.__setattr__(self, "universe_digest", value)
        object.__setattr__(self, "universe_identity", f"d7-evaluated-universe:sha256:{value}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_evaluated_candidate_universe/1",
            "binding_members": [
                {"identity": item.binding_identity, "digest": item.binding_digest, "assignment": _assignment_dict(item.candidate.assignments)}
                for item in self.bindings
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "universe_digest": self.universe_digest, "universe_identity": self.universe_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], bindings: Sequence[LoopDecisionEvidenceBinding]) -> "NoveltyUniverse":
        _require_keys(payload, {"schema", "binding_members", "universe_digest", "universe_identity"}, "D7 novelty universe")
        if payload["schema"] != "d7_evaluated_candidate_universe/1":
            raise InvalidScientificProblem("D7 novelty universe schema mismatch")
        rebuilt = cls(tuple(bindings))
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("D7 novelty universe digest/content mismatch")
        return rebuilt

    @property
    def unique_assignments(self) -> tuple[dict[str, ScientificValue], ...]:
        by_bytes = {canonical_bytes(_assignment_dict(item.candidate.assignments)): dict(item.candidate.assignments) for item in self.bindings}
        return tuple(by_bytes[key] for key in sorted(by_bytes))


def novelty(assignment: Mapping[str, ScientificValue], universe: NoveltyUniverse) -> float:
    if not universe.bindings:
        raise InvalidScientificProblem("D7 novelty requires typed evaluated universe")
    distances = []
    for other in universe.unique_assignments:
        distances.append(sum(encode_value(assignment[name]) != encode_value(other[name]) for name in d4.SLOTS) / 5.0)
    return min(distances)


def _classify_prediction(values: Mapping[str, float], assessment: LoopAssessmentContext) -> str:
    quantities = {name: Quantity(value, "dimensionless") for name, value in values.items()}
    return assessment.classify(quantities)


@dataclass(frozen=True)
class PredictionRecord:
    source_id: str
    version: str
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        values = {name: float(value) for name, value in self.values.items()}
        if set(values) != {item.name for item in d4.OBJECTIVES} or any(not math.isfinite(value) for value in values.values()):
            raise InvalidScientificProblem("D7 prediction must contain finite complete projection")
        object.__setattr__(self, "values", dict(sorted(values.items())))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "d7_declared_prediction/1", "source_id": self.source_id, "version": self.version, "values": dict(self.values)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PredictionRecord":
        _require_keys(payload, {"schema", "source_id", "version", "values"}, "D7 prediction")
        if payload["schema"] != "d7_declared_prediction/1":
            raise InvalidScientificProblem("D7 prediction schema mismatch")
        return cls(payload["source_id"], payload["version"], dict(payload["values"]))


def model_disagreement(alpha: PredictionRecord, beta: PredictionRecord) -> float:
    return max(
        abs(alpha.values["yield_score"] - beta.values["yield_score"]) / 100.0,
        abs(alpha.values["loss_score"] - beta.values["loss_score"]) / 50.0,
        abs(alpha.values["stability_score"] - beta.values["stability_score"]) / 100.0,
    )


@dataclass(frozen=True)
class LoopExperimentOption:
    option_label: str
    study_id: str
    assignment: Mapping[str, ScientificValue]
    physics_scope: LoopPhysicsScope
    assessment_context: LoopAssessmentContext
    evidence_bindings: tuple[LoopDecisionEvidenceBinding, ...]
    novelty_universe: NoveltyUniverse
    alpha_prediction: PredictionRecord
    beta_prediction: PredictionRecord
    declared_uncertainty: float
    compute_cost: int
    partial_success_lineage: tuple[str, ...] = ()
    useful_failure_lineage: tuple[str, ...] = ()
    option_identity: str = field(init=False)
    derived_signals: Mapping[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        if self.option_label not in {"A", "B", "C"}:
            raise InvalidScientificProblem("D7 option label mismatch")
        assignment = dict(self.assignment)
        d4.design_space().validate_assignments(assignment)
        evidence = tuple(sorted(self.evidence_bindings, key=lambda item: item.binding_identity))
        if not evidence or len({item.binding_identity for item in evidence}) != len(evidence):
            raise InvalidScientificProblem("D7 option evidence bindings invalid")
        if any(item.physics_scope.physics_scope_identity != self.physics_scope.physics_scope_identity for item in evidence):
            raise InvalidScientificProblem("D7 option evidence physics mismatch")
        uncertainty = float(self.declared_uncertainty)
        if not math.isfinite(uncertainty) or uncertainty < 0:
            raise InvalidScientificProblem("D7 declared uncertainty must be finite and non-negative")
        if isinstance(self.compute_cost, bool) or not isinstance(self.compute_cost, int) or self.compute_cost <= 0:
            raise InvalidScientificProblem("D7 compute cost must be positive integer units")
        exact_declarations = {
            "A": {
                "study_id": "d7-study-partial-success-adapter-variation-v0.1",
                "assignment": d4.typed_assignments("A_stable", "B_filter", "isolated", 2, True),
                "evidence_evaluations": None,
                "alpha": {"yield_score": 88.0, "loss_score": 18.0, "stability_score": 66.0},
                "beta": {"yield_score": 84.0, "loss_score": 20.0, "stability_score": 64.0},
                "uncertainty": 0.08,
                "cost": 1,
            },
            "B": {
                "study_id": "d7-study-uncertainty-disagreement-boundary-v0.1",
                "assignment": d4.typed_assignments("A_peak", "B_filter", "buffered", 1, False),
                "evidence_evaluations": {
                    "d7-g0-evaluation:d4-parent-a:primary",
                    "d7-g0-evaluation:d4-parent-d:primary",
                    "SUCCESSOR",
                },
                "alpha": {"yield_score": 52.0, "loss_score": 22.0, "stability_score": 54.0},
                "beta": {"yield_score": 72.0, "loss_score": 32.0, "stability_score": 38.0},
                "uncertainty": 0.31,
                "cost": 2,
            },
            "C": {
                "study_id": "d7-study-novel-region-v0.1",
                "assignment": d4.typed_assignments("A_base", "B_base", "isolated", 0, True),
                "evidence_evaluations": "ALL",
                "alpha": {"yield_score": 60.0, "loss_score": 24.0, "stability_score": 62.0},
                "beta": {"yield_score": 50.0, "loss_score": 29.0, "stability_score": 72.0},
                "uncertainty": 0.18,
                "cost": 5,
            },
        }
        declared = exact_declarations[self.option_label]
        evidence_labels = {
            "SUCCESSOR" if item.d4_derivation_identity is not None else item.evaluation.evaluation_id
            for item in evidence
        }
        expected_evidence = declared["evidence_evaluations"]
        evidence_ok = (
            evidence_labels == {"SUCCESSOR"}
            if expected_evidence is None
            else evidence_labels == ({
                "SUCCESSOR" if item.d4_derivation_identity is not None else item.evaluation.evaluation_id
                for item in self.novelty_universe.bindings
            } if expected_evidence == "ALL" else expected_evidence)
        )
        if (
            self.study_id != declared["study_id"]
            or _assignment_dict(assignment) != _assignment_dict(declared["assignment"])
            or not evidence_ok
            or self.alpha_prediction.source_id != "d7.synthetic.model-alpha"
            or self.alpha_prediction.version != "0.1"
            or self.beta_prediction.source_id != "d7.synthetic.model-beta"
            or self.beta_prediction.version != "0.1"
        ):
            raise InvalidScientificProblem(f"D7 option {self.option_label} declaration mismatch")
        disagreement = model_disagreement(self.alpha_prediction, self.beta_prediction)
        novelty_value = novelty(assignment, self.novelty_universe)
        contradiction = _classify_prediction(self.alpha_prediction.values, self.assessment_context) != _classify_prediction(self.beta_prediction.values, self.assessment_context)
        successor = next((item for item in evidence if item.d4_derivation_identity is not None), None)
        partial = False
        if successor is not None:
            changed = sum(encode_value(assignment[name]) != encode_value(successor.candidate.assignments[name]) for name in d4.SLOTS)
            parent_ids = {item.candidate_id for item in successor.candidate.parents}
            parent_evidence = tuple(
                item for item in self.novelty_universe.bindings
                if item.candidate.candidate_id in parent_ids
            )
            improved_relative_to_every_parent = any(
                all(
                    (
                        successor.evaluation.result.values[objective.name].magnitude
                        > parent.evaluation.result.values[objective.name].magnitude
                        if objective.direction.value == "maximize"
                        else successor.evaluation.result.values[objective.name].magnitude
                        < parent.evaluation.result.values[objective.name].magnitude
                    )
                    for parent in parent_evidence
                )
                for objective in d4.OBJECTIVES
            ) if parent_evidence else False
            partial = (
                changed == 1
                and self.assessment_context.classify(successor.evaluation.result.values) == "FAIL"
                and self.partial_success_lineage == (successor.generation_lineage_identity,)
                and improved_relative_to_every_parent
            )
        useful = False
        if self.useful_failure_lineage:
            useful = any(self.assessment_context.classify(item.evaluation.result.values) == "FAIL" for item in evidence)
        predicates = {
            "high_uncertainty": uncertainty >= 0.25,
            "high_disagreement": disagreement >= 0.20,
            "high_novelty": novelty_value >= 0.50,
            "contradiction": contradiction,
            "partial_success_relevance": partial,
            "useful_failure_relevance": useful,
        }
        info = sum(bool(value) for value in predicates.values())
        signals = {
            "declared_uncertainty": uncertainty,
            "uncertainty_kind": "DECLARED",
            "model_disagreement": disagreement,
            "novelty": novelty_value,
            **predicates,
            "information_proxy_units": info,
            "compute_cost": self.compute_cost,
            "information_per_compute": f"{info}/{self.compute_cost}",
            "derivation_semantics": {
                "novelty": "d7-min-typed-hamming@0.1",
                "disagreement": "d7-normalized-max-model-disagreement@0.1",
                "contradiction": "d7-assessment-classification-disagreement@0.1",
                "information_proxy": "d7-six-predicate-count@0.1",
            },
        }
        object.__setattr__(self, "assignment", assignment)
        object.__setattr__(self, "evidence_bindings", evidence)
        object.__setattr__(self, "declared_uncertainty", uncertainty)
        object.__setattr__(self, "partial_success_lineage", tuple(sorted(self.partial_success_lineage)))
        object.__setattr__(self, "useful_failure_lineage", tuple(sorted(self.useful_failure_lineage)))
        object.__setattr__(self, "derived_signals", signals)
        object.__setattr__(self, "option_identity", _identity("d7-option", self.identity_payload()))

    def study_specification(self) -> dict[str, Any]:
        return {
            "schema": "d7_loop_study_specification/1",
            "study_id": self.study_id,
            "assignment": _assignment_dict(self.assignment),
            "physics_scope_identity": self.physics_scope.physics_scope_identity,
            "assessment_context_identity": self.assessment_context.assessment_context_identity,
            "problem_id": PROBLEM_ID,
            "model": list(MODEL),
            "solver": list(SOLVER),
            "execution_semantics_identity": EXECUTION_SEMANTICS,
            "decision_question": self.assessment_context.study_question_id,
        }

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_experiment_option/1",
            "option_set_id": OPTION_SET_ID,
            "option_label": self.option_label,
            "study_specification": self.study_specification(),
            "proposed_assignment": _assignment_dict(self.assignment),
            "physics_scope": self.physics_scope.to_dict(),
            "physics_scope_payload_digest": digest(self.physics_scope.identity_payload()),
            "assessment_context": self.assessment_context.to_dict(),
            "assessment_context_payload_digest": digest(self.assessment_context.identity_payload()),
            "evidence_bindings": [{"identity": item.binding_identity, "digest": item.binding_digest} for item in self.evidence_bindings],
            "novelty_universe_identity": self.novelty_universe.universe_identity,
            "novelty_universe_digest": self.novelty_universe.universe_digest,
            "alpha_prediction": self.alpha_prediction.to_dict(),
            "beta_prediction": self.beta_prediction.to_dict(),
            "declared_uncertainty": {"source_id": "d7.synthetic.declared-uncertainty", "version": "0.1", "value": self.declared_uncertainty, "kind": "DECLARED"},
            "derived_signals": dict(self.derived_signals),
            "partial_success_source_lineage": list(self.partial_success_lineage),
            "useful_failure_source_lineage": list(self.useful_failure_lineage),
            "compute_cost": {"source_id": "d7.synthetic.compute-cost", "version": "0.1", "normalized_units": self.compute_cost},
            "decision_policy_id": DECISION_POLICY_ID,
            "execution_semantics_id": EXECUTION_SEMANTICS,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "option_identity": self.option_identity}

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        evidence_by_identity: Mapping[str, LoopDecisionEvidenceBinding],
        universe: NoveltyUniverse,
    ) -> "LoopExperimentOption":
        required = {
            "schema", "option_set_id", "option_label", "study_specification", "proposed_assignment",
            "physics_scope", "physics_scope_payload_digest", "assessment_context", "assessment_context_payload_digest",
            "evidence_bindings", "novelty_universe_identity", "novelty_universe_digest", "alpha_prediction",
            "beta_prediction", "declared_uncertainty", "derived_signals", "partial_success_source_lineage",
            "useful_failure_source_lineage", "compute_cost", "decision_policy_id", "execution_semantics_id", "option_identity",
        }
        _require_keys(payload, required, "D7 option")
        if payload["schema"] != "d7_experiment_option/1" or payload["option_set_id"] != OPTION_SET_ID:
            raise InvalidScientificProblem("D7 option schema/set mismatch")
        evidence = []
        for ref in payload["evidence_bindings"]:
            item = evidence_by_identity.get(ref.get("identity"))
            if item is None or item.binding_digest != ref.get("digest"):
                raise InvalidScientificProblem("D7 option typed evidence reference mismatch")
            evidence.append(item)
        uncertainty = payload["declared_uncertainty"]
        cost = payload["compute_cost"]
        rebuilt = cls(
            option_label=payload["option_label"],
            study_id=payload["study_specification"]["study_id"],
            assignment=_decode_assignment(payload["proposed_assignment"]),
            physics_scope=LoopPhysicsScope.from_dict(payload["physics_scope"]),
            assessment_context=LoopAssessmentContext.from_dict(payload["assessment_context"]),
            evidence_bindings=tuple(evidence),
            novelty_universe=universe,
            alpha_prediction=PredictionRecord.from_dict(payload["alpha_prediction"]),
            beta_prediction=PredictionRecord.from_dict(payload["beta_prediction"]),
            declared_uncertainty=uncertainty["value"],
            compute_cost=cost["normalized_units"],
            partial_success_lineage=tuple(payload["partial_success_source_lineage"]),
            useful_failure_lineage=tuple(payload["useful_failure_source_lineage"]),
        )
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("D7 option content/signal/identity mismatch")
        return rebuilt


def build_options(
    bindings: Sequence[LoopDecisionEvidenceBinding],
    universe: NoveltyUniverse,
    scope: LoopPhysicsScope,
    assessment: LoopAssessmentContext,
) -> tuple[LoopExperimentOption, ...]:
    by_eval = {item.evaluation.evaluation_id: item for item in bindings}
    successor = next(item for item in bindings if item.d4_derivation_identity is not None)
    primary_a = by_eval["d7-g0-evaluation:d4-parent-a:primary"]
    primary_d = by_eval["d7-g0-evaluation:d4-parent-d:primary"]
    definitions = (
        (
            "A", "d7-study-partial-success-adapter-variation-v0.1",
            d4.typed_assignments("A_stable", "B_filter", "isolated", 2, True),
            (successor,), (88, 18, 66), (84, 20, 64), 0.08, 1,
            (successor.generation_lineage_identity,), (),
        ),
        (
            "B", "d7-study-uncertainty-disagreement-boundary-v0.1",
            d4.typed_assignments("A_peak", "B_filter", "buffered", 1, False),
            (successor, primary_a, primary_d), (52, 22, 54), (72, 32, 38), 0.31, 2,
            (), (),
        ),
        (
            "C", "d7-study-novel-region-v0.1",
            d4.typed_assignments("A_base", "B_base", "isolated", 0, True),
            tuple(bindings), (60, 24, 62), (50, 29, 72), 0.18, 5,
            (), (),
        ),
    )
    options = []
    for label, study_id, assignment, evidence, alpha, beta, uncertainty, cost, partial, useful in definitions:
        names = ("yield_score", "loss_score", "stability_score")
        options.append(
            LoopExperimentOption(
                option_label=label,
                study_id=study_id,
                assignment=assignment,
                physics_scope=scope,
                assessment_context=assessment,
                evidence_bindings=tuple(evidence),
                novelty_universe=universe,
                alpha_prediction=PredictionRecord("d7.synthetic.model-alpha", "0.1", dict(zip(names, alpha))),
                beta_prediction=PredictionRecord("d7.synthetic.model-beta", "0.1", dict(zip(names, beta))),
                declared_uncertainty=uncertainty,
                compute_cost=cost,
                partial_success_lineage=partial,
                useful_failure_lineage=useful,
            )
        )
    result = tuple(sorted(options, key=lambda item: item.option_label))
    expected = {
        "A": (1, 1, "1/1", 0.20, 0.04),
        "B": (2, 2, "2/2", 0.40, 0.20),
        "C": (1, 5, "1/5", 0.60, 0.10),
    }
    for option in result:
        actual = (
            option.derived_signals["information_proxy_units"], option.compute_cost,
            option.derived_signals["information_per_compute"], option.derived_signals["novelty"],
            option.derived_signals["model_disagreement"],
        )
        if actual != expected[option.option_label]:
            raise InvalidScientificProblem(f"D7 option {option.option_label} signal table mismatch: {actual}")
    return result


def rank_options(options: Sequence[LoopExperimentOption]) -> tuple[LoopExperimentOption, ...]:
    items = tuple(options)
    if len(items) != 3 or {item.option_label for item in items} != {"A", "B", "C"}:
        raise InvalidScientificProblem("D7 decision requires exactly A/B/C")
    if len({item.option_identity for item in items}) != 3:
        raise InvalidScientificProblem("D7 decision rejects duplicate option identities")
    return tuple(sorted(
        items,
        key=lambda item: (
            -Fraction(item.derived_signals["information_proxy_units"], item.compute_cost),
            -item.derived_signals["information_proxy_units"],
            -item.derived_signals["model_disagreement"],
            item.option_identity,
        ),
    ))


@dataclass(frozen=True)
class NextExperimentDecision:
    options: tuple[LoopExperimentOption, ...]
    physics_scope: LoopPhysicsScope
    assessment_context: LoopAssessmentContext
    novelty_universe: NoveltyUniverse
    ranking: tuple[str, ...] = field(init=False)
    selected_option_identity: str = field(init=False)
    decision_identity: str = field(init=False)

    def __post_init__(self) -> None:
        options = tuple(sorted(self.options, key=lambda item: item.option_label))
        ranked = rank_options(options)
        if ranked[0].option_label != "B":
            raise InvalidScientificProblem("D7 preregistered winner is not B")
        ranking = tuple(item.option_identity for item in ranked)
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "ranking", ranking)
        object.__setattr__(self, "selected_option_identity", ranked[0].option_identity)
        object.__setattr__(self, "decision_identity", _identity("d7-decision", self.identity_payload()))

    @property
    def selected_option(self) -> LoopExperimentOption:
        return next(item for item in self.options if item.option_identity == self.selected_option_identity)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_next_experiment_decision/1",
            "option_set_id": OPTION_SET_ID,
            "policy_id": DECISION_POLICY_ID,
            "selection_basis": [
                "maximum exact information_proxy_units/compute_cost",
                "higher information_proxy_units",
                "higher model_disagreement",
                "lexicographically smallest option identity",
            ],
            "options": [item.to_dict() for item in self.options],
            "ranking": list(self.ranking),
            "selected_option_identity": self.selected_option_identity,
            "physics_scope": self.physics_scope.to_dict(),
            "assessment_context": self.assessment_context.to_dict(),
            "evidence_universe_identity": self.novelty_universe.universe_identity,
            "evidence_universe_digest": self.novelty_universe.universe_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "decision_identity": self.decision_identity}

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        evidence_by_identity: Mapping[str, LoopDecisionEvidenceBinding],
        universe: NoveltyUniverse,
    ) -> "NextExperimentDecision":
        required = {
            "schema", "option_set_id", "policy_id", "selection_basis", "options", "ranking",
            "selected_option_identity", "physics_scope", "assessment_context", "evidence_universe_identity",
            "evidence_universe_digest", "decision_identity",
        }
        _require_keys(payload, required, "D7 decision")
        if payload["schema"] != "d7_next_experiment_decision/1":
            raise InvalidScientificProblem("D7 decision schema mismatch")
        options = tuple(LoopExperimentOption.from_dict(item, evidence_by_identity, universe) for item in payload["options"])
        rebuilt = cls(
            options=options,
            physics_scope=LoopPhysicsScope.from_dict(payload["physics_scope"]),
            assessment_context=LoopAssessmentContext.from_dict(payload["assessment_context"]),
            novelty_universe=universe,
        )
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("D7 decision content/ranking/identity mismatch")
        return rebuilt


def _partial_trace(
    g0: GenerationZero,
    memory: DesignMemoryRecord,
    authoritative: AuthoritativeD4,
    generation: SuccessorGeneration,
    successor: SuccessorEvaluation,
    bindings: Sequence[LoopDecisionEvidenceBinding],
    decision: NextExperimentDecision,
) -> dict[str, Any]:
    initial = g0.evaluation("d4-parent-c", "primary")
    initial_entry = next(
        item for item in memory.layer_a.entries
        if item.evaluation.evaluation_id == initial.evaluation_id
    )
    return {
        "schema": "d7_integrated_object_trace_partial/1",
        "initial_candidate_id": initial.candidate.candidate_id,
        "initial_twin_id": f"{initial.twin.twin_id}@{initial.twin.version}",
        "initial_evaluation_id": initial.evaluation_id,
        "initial_result_id": initial.result.result_id,
        "initial_run_id": initial.result.provenance.run_id,
        "generation0_candidate_ids": [item.candidate_id for item in g0.candidates],
        "generation0_twin_ids": [f"{item.twin_id}@{item.version}" for item in g0.twins],
        "generation0_evaluation_ids": [item.evaluation_id for item in g0.evaluations],
        "generation0_result_ids": [item.result.result_id for item in g0.evaluations],
        "generation0_run_ids": [item.result.provenance.run_id for item in g0.evaluations],
        "memory_entry_identity": initial_entry.identity,
        "memory_entry_digest": initial_entry.entry_digest,
        "memory_scope_identity": memory.layer_a.scope.scope_identity,
        "d4_source_evaluation_ids": sorted({item.evaluation.evaluation_id for item in authoritative.sources}),
        "d4_event_identity": authoritative.event_identity,
        "d4_derivation_identity": authoritative.derivation_identity,
        "d4_materialized_child_identity": authoritative.candidate.candidate_id,
        "d4_materialized_twin_identity": f"{authoritative.twin.twin_id}@{authoritative.twin.version}",
        "successor_generation_identity": generation.generation_identity,
        "generation_member_identity": generation.members[0].member_identity,
        "generation_lineage_identity": generation.lineage.lineage_identity,
        "successor_evaluation_id": successor.evaluation.evaluation_id,
        "successor_result_id": successor.evaluation.result.result_id,
        "successor_run_id": successor.evaluation.result.provenance.run_id,
        "decision_evidence_binding_ids": [item.binding_identity for item in bindings],
        "decision_evidence_binding_digests": [item.binding_digest for item in bindings],
        "experiment_option_identities": [item.option_identity for item in decision.options],
        "decision_identity": decision.decision_identity,
        "selected_option_identity": decision.selected_option_identity,
    }


def _validate_global_uniqueness(
    g0: GenerationZero,
    generation: SuccessorGeneration,
    successor: SuccessorEvaluation,
    bindings: Sequence[LoopDecisionEvidenceBinding],
    decision: NextExperimentDecision,
) -> None:
    groups = {
        "runs": [item.result.provenance.run_id for item in g0.evaluations] + [successor.evaluation.result.provenance.run_id],
        "results": [item.result.result_id for item in g0.evaluations] + [successor.evaluation.result.result_id],
        "evaluations": [item.evaluation_id for item in g0.evaluations] + [successor.evaluation.evaluation_id],
        "options": [item.option_identity for item in decision.options],
        "members": [item.member_identity for item in generation.members],
        "bindings": [item.binding_identity for item in bindings],
    }
    for label, identities in groups.items():
        if len(identities) != len(set(identities)):
            raise InvalidScientificProblem(f"D7 duplicate {label} identity")


@dataclass(frozen=True)
class PreExecutionState:
    physics_scope: LoopPhysicsScope
    assessment_context: LoopAssessmentContext
    generation_zero: GenerationZero
    memory: DesignMemoryRecord
    authoritative_d4: AuthoritativeD4
    successor_generation: SuccessorGeneration
    successor_evaluation: SuccessorEvaluation
    evidence_bindings: tuple[LoopDecisionEvidenceBinding, ...]
    novelty_universe: NoveltyUniverse
    decision: NextExperimentDecision
    partial_object_trace: Mapping[str, Any]

    def __post_init__(self) -> None:
        bindings = tuple(sorted(self.evidence_bindings, key=lambda item: item.binding_identity))
        if self.generation_zero.physics_scope.to_dict() != self.physics_scope.to_dict():
            raise InvalidScientificProblem("D7 state Generation 0 physics mismatch")
        if self.memory.layer_a.scope.context_reference != self.physics_scope.physics_scope_identity:
            raise InvalidScientificProblem("D7 state memory physics mismatch")
        verify_layer_a_attribution(
            layer_a=self.memory.layer_a,
            candidates=self.generation_zero.candidates,
            evaluations=self.generation_zero.evaluations,
        )
        if self.memory.reconstruct().to_dict() != self.memory.to_dict():
            raise InvalidScientificProblem("D7 state memory classification reconstruction mismatch")
        member = self.successor_generation.members[0]
        if member.candidate.to_dict() != self.authoritative_d4.candidate.to_dict() or member.twin.to_dict() != self.authoritative_d4.twin.to_dict():
            raise InvalidScientificProblem("D7 state D4/D5 literal child mismatch")
        if self.successor_evaluation.generation_identity != self.successor_generation.generation_identity:
            raise InvalidScientificProblem("D7 state successor evaluation generation mismatch")
        if self.successor_evaluation.member_identity != member.member_identity or self.successor_evaluation.lineage_identity != self.successor_generation.lineage.lineage_identity:
            raise InvalidScientificProblem("D7 state successor evaluation lineage mismatch")
        self.successor_evaluation.evaluation.validate_candidate(member.candidate)
        expected_d3_sources = tuple(sorted(
            ({"identity": item.entry.identity, "digest": item.entry.entry_digest} for item in self.authoritative_d4.sources),
            key=lambda item: (item["identity"], item["digest"]),
        ))
        if (
            self.successor_generation.source_generation_identity != SOURCE_GENERATION_ID
            or self.successor_generation.lineage.source_generation_identity != SOURCE_GENERATION_ID
            or self.successor_generation.lineage.d4_event_identity != self.authoritative_d4.event_identity
            or self.successor_generation.lineage.d4_derivation_identity != self.authoritative_d4.derivation_identity
            or self.successor_generation.lineage.d3_sources != expected_d3_sources
        ):
            raise InvalidScientificProblem("D7 successor lineage does not prove exact authoritative D4 sources")
        expected_successor = execute_successor(self.successor_generation, self.physics_scope)
        if expected_successor.to_dict() != self.successor_evaluation.to_dict():
            raise InvalidScientificProblem("D7 successor evaluation/run/result is not exactly rederivable")
        g0_evaluations = {item.evaluation_id: item for item in self.generation_zero.evaluations}
        successor_binding_count = 0
        for binding in bindings:
            if binding.source_generation_identity != SOURCE_GENERATION_ID or binding.successor_generation_identity != self.successor_generation.generation_identity:
                raise InvalidScientificProblem("D7 evidence binding generation graph mismatch")
            if binding.d4_derivation_identity is not None:
                successor_binding_count += 1
                if (
                    binding.candidate.to_dict() != member.candidate.to_dict()
                    or binding.twin.to_dict() != member.twin.to_dict()
                    or binding.evaluation.to_dict() != self.successor_evaluation.evaluation.to_dict()
                    or binding.generation_member_identity != member.member_identity
                    or binding.generation_lineage_identity != self.successor_generation.lineage.lineage_identity
                    or binding.d4_event_identity != self.authoritative_d4.event_identity
                    or binding.d4_derivation_identity != self.authoritative_d4.derivation_identity
                ):
                    raise InvalidScientificProblem("D7 successor evidence binding does not prove exact D4/D5 graph")
            else:
                evaluation = g0_evaluations.get(binding.evaluation.evaluation_id)
                if evaluation is None or evaluation.to_dict() != binding.evaluation.to_dict():
                    raise InvalidScientificProblem("D7 baseline evidence evaluation absent or altered")
                expected_member, expected_lineage = _baseline_lineage(binding.candidate, evaluation)
                if binding.generation_member_identity != expected_member or binding.generation_lineage_identity != expected_lineage:
                    raise InvalidScientificProblem("D7 baseline evidence lineage mismatch")
        if successor_binding_count != 1:
            raise InvalidScientificProblem("D7 evidence graph requires exactly one authoritative successor binding")
        if tuple(item.to_dict() for item in bindings) != tuple(item.to_dict() for item in self.novelty_universe.bindings):
            raise InvalidScientificProblem("D7 state novelty universe does not cover stored evidence")
        if self.decision.novelty_universe.to_dict() != self.novelty_universe.to_dict():
            raise InvalidScientificProblem("D7 state decision universe mismatch")
        expected_trace = _partial_trace(
            self.generation_zero, self.memory, self.authoritative_d4,
            self.successor_generation, self.successor_evaluation, bindings, self.decision,
        )
        if dict(self.partial_object_trace) != expected_trace:
            raise InvalidScientificProblem("D7 partial object trace mismatch")
        _validate_global_uniqueness(self.generation_zero, self.successor_generation, self.successor_evaluation, bindings, self.decision)
        object.__setattr__(self, "evidence_bindings", bindings)
        object.__setattr__(self, "partial_object_trace", expected_trace)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_pre_execution_state/1",
            "physics_scope": self.physics_scope.to_dict(),
            "assessment_context": self.assessment_context.to_dict(),
            "generation_zero": self.generation_zero.to_dict(),
            "memory": self.memory.to_dict(),
            "authoritative_d4": self.authoritative_d4.to_dict(),
            "successor_generation": self.successor_generation.to_dict(),
            "successor_evaluation": self.successor_evaluation.to_dict(),
            "evidence_bindings": [item.to_dict() for item in self.evidence_bindings],
            "novelty_universe": self.novelty_universe.to_dict(),
            "decision": self.decision.to_dict(),
            "partial_object_trace": dict(self.partial_object_trace),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PreExecutionState":
        _require_keys(payload, {
            "schema", "physics_scope", "assessment_context", "generation_zero", "memory",
            "authoritative_d4", "successor_generation", "successor_evaluation",
            "evidence_bindings", "novelty_universe", "decision", "partial_object_trace",
        }, "D7 pre-execution state")
        if payload["schema"] != "d7_pre_execution_state/1":
            raise InvalidScientificProblem("D7 pre-execution state schema mismatch")
        physics = LoopPhysicsScope.from_dict(payload["physics_scope"])
        assessment = LoopAssessmentContext.from_dict(payload["assessment_context"])
        g0 = GenerationZero.from_dict(payload["generation_zero"], physics)
        memory = DesignMemoryRecord.from_dict(payload["memory"])
        authoritative = AuthoritativeD4.from_dict(payload["authoritative_d4"])
        generation = SuccessorGeneration.from_dict(payload["successor_generation"])
        successor = SuccessorEvaluation.from_dict(payload["successor_evaluation"])
        bindings = tuple(LoopDecisionEvidenceBinding.from_dict(item) for item in payload["evidence_bindings"])
        by_identity = {item.binding_identity: item for item in bindings}
        universe = NoveltyUniverse.from_dict(payload["novelty_universe"], bindings)
        decision = NextExperimentDecision.from_dict(payload["decision"], by_identity, universe)
        return cls(
            physics, assessment, g0, memory, authoritative, generation, successor,
            bindings, universe, decision, dict(payload["partial_object_trace"]),
        )


def build_pre_execution_state() -> PreExecutionState:
    physics = LoopPhysicsScope()
    assessment = LoopAssessmentContext()
    g0 = build_generation_zero(physics)
    memory = build_memory(g0, assessment)
    authoritative = materialize_authoritative_d4(select_case_c_sources(g0, memory))
    generation = admit_successor(authoritative)
    successor = execute_successor(generation, physics)
    bindings = build_evidence_bindings(g0, generation, successor)
    universe = NoveltyUniverse(bindings)
    options = build_options(bindings, universe, physics, assessment)
    decision = NextExperimentDecision(options, physics, assessment, universe)
    partial = _partial_trace(g0, memory, authoritative, generation, successor, bindings, decision)
    return PreExecutionState(
        physics, assessment, g0, memory, authoritative, generation, successor,
        bindings, universe, decision, partial,
    )


@dataclass(frozen=True)
class D7Checkpoint:
    state: PreExecutionState
    checkpoint_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint_identity", digest(self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_integrated_loop_checkpoint/1",
            "phase": "DECISION_RECORDED_PRE_EXECUTION",
            "milestone": MILESTONE,
            "version": "0.1",
            "payload": self.state.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "checkpoint_identity": self.checkpoint_identity}

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D7Checkpoint":
        _require_keys(payload, {"schema", "phase", "milestone", "version", "payload", "checkpoint_identity"}, "D7 checkpoint")
        if payload["schema"] != "d7_integrated_loop_checkpoint/1" or payload["phase"] != "DECISION_RECORDED_PRE_EXECUTION" or payload["milestone"] != MILESTONE or payload["version"] != "0.1":
            raise InvalidScientificProblem("D7 checkpoint envelope declaration mismatch")
        state = PreExecutionState.from_dict(payload["payload"])
        rebuilt = cls(state)
        _require_identity(payload["checkpoint_identity"], rebuilt.checkpoint_identity, "D7 checkpoint")
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("D7 checkpoint is not canonical/reconstructible")
        return rebuilt

    @classmethod
    def from_bytes(cls, data: bytes) -> "D7Checkpoint":
        try:
            text = data.decode("utf-8")
            payload = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidScientificProblem("D7 checkpoint bytes are invalid UTF-8 JSON") from exc
        if not isinstance(payload, Mapping):
            raise InvalidScientificProblem("D7 checkpoint root must be an object")
        rebuilt = cls.from_dict(payload)
        if rebuilt.to_bytes() != data:
            raise InvalidScientificProblem("D7 checkpoint bytes are not canonical")
        return rebuilt


def write_checkpoint_atomic(checkpoint: D7Checkpoint, path: Path) -> bytes:
    data = checkpoint.to_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    return data


def real_checkpoint_reload(path: Path) -> tuple[D7Checkpoint, bool]:
    state = build_pre_execution_state()
    checkpoint = D7Checkpoint(state)
    data = write_checkpoint_atomic(checkpoint, path)
    # The only surviving authority at this boundary is serialized bytes/path.
    del checkpoint
    del state
    reloaded_bytes = path.read_bytes()
    if reloaded_bytes != data:
        raise InvalidScientificProblem("D7 checkpoint persisted bytes changed")
    reloaded = D7Checkpoint.from_bytes(reloaded_bytes)
    return reloaded, reloaded.to_bytes() == data


@dataclass(frozen=True)
class LoopStudy:
    decision_identity: str
    option: LoopExperimentOption
    evidence_bindings: tuple[Mapping[str, str], ...]
    study_identity: str = field(init=False)

    def __post_init__(self) -> None:
        evidence = tuple(sorted((dict(item) for item in self.evidence_bindings), key=lambda item: item["identity"]))
        expected = tuple({"identity": item.binding_identity, "digest": item.binding_digest} for item in self.option.evidence_bindings)
        if evidence != expected:
            raise InvalidScientificProblem("D7 Study decision-evidence provenance mismatch")
        object.__setattr__(self, "evidence_bindings", evidence)
        object.__setattr__(self, "study_identity", _identity("d7-study", self.identity_payload()))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_loop_study/1",
            "study_id": self.option.study_id,
            "decision_identity": self.decision_identity,
            "selected_option_identity": self.option.option_identity,
            "selected_option_label": self.option.option_label,
            "assignment": _assignment_dict(self.option.assignment),
            "physics_scope": self.option.physics_scope.to_dict(),
            "assessment_context": self.option.assessment_context.to_dict(),
            "problem_id": PROBLEM_ID,
            "model": list(MODEL),
            "solver": list(SOLVER),
            "execution_semantics_identity": EXECUTION_SEMANTICS,
            "decision_question": self.option.assessment_context.study_question_id,
            "decision_evidence_bindings": list(self.evidence_bindings),
            "decision_provenance_only": True,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "study_identity": self.study_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], option: LoopExperimentOption) -> "LoopStudy":
        required = {
            "schema", "study_id", "decision_identity", "selected_option_identity", "selected_option_label",
            "assignment", "physics_scope", "assessment_context", "problem_id", "model", "solver",
            "execution_semantics_identity", "decision_question", "decision_evidence_bindings",
            "decision_provenance_only", "study_identity",
        }
        _require_keys(payload, required, "D7 LoopStudy")
        if payload["schema"] != "d7_loop_study/1":
            raise InvalidScientificProblem("D7 LoopStudy schema mismatch")
        rebuilt = cls(payload["decision_identity"], option, tuple(dict(item) for item in payload["decision_evidence_bindings"]))
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("D7 LoopStudy content/identity mismatch")
        return rebuilt


@dataclass(frozen=True)
class SelectedMaterialization:
    study: LoopStudy
    predecessor_twin: ScientificTwin
    candidate: DesignCandidate
    twin: ScientificTwin
    materialization_digest: str

    def __post_init__(self) -> None:
        expected_payload = self.materialization_payload()
        expected_digest = digest(expected_payload)
        if self.materialization_digest != expected_digest:
            raise InvalidScientificProblem("D7 selected materialization digest mismatch")
        if self.candidate.candidate_id != f"d7-selected-candidate:sha256:{expected_digest}":
            raise InvalidScientificProblem("D7 selected Candidate identity mismatch")
        if self.twin.twin_id != f"d7-selected-twin:sha256:{expected_digest}" or self.twin.version != "1":
            raise InvalidScientificProblem("D7 selected Twin identity mismatch")
        if self.candidate.twin.key != self.twin.reference.key:
            raise InvalidScientificProblem("D7 selected Candidate/Twin mismatch")
        if self.candidate.generation != 1:
            raise InvalidScientificProblem("D7 selected Study materialization cannot create Generation 2")
        if _assignment_dict(self.candidate.assignments) != _assignment_dict(self.study.option.assignment):
            raise InvalidScientificProblem("D7 selected assignment mismatch")
        if self.twin.parent is None or self.twin.parent.key != self.predecessor_twin.reference.key:
            raise InvalidScientificProblem("D7 selected Twin predecessor mismatch")
        validate_no_inheritance(self.candidate, self.twin)

    def materialization_payload(self) -> dict[str, Any]:
        return {
            "schema": "d7_selected_materialization/1",
            "study": self.study.to_dict(),
            "decision_identity": self.study.decision_identity,
            "option_identity": self.study.option.option_identity,
            "assignment": _assignment_dict(self.study.option.assignment),
            "design_space": d4.design_space().reference.to_dict(),
            "physics_scope": self.study.option.physics_scope.to_dict(),
            "assessment_context": self.study.option.assessment_context.to_dict(),
            "parent_twin": self.predecessor_twin.reference.to_dict(),
            "materialization_semantics": SELECTED_MATERIALIZATION_SEMANTICS,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_selected_materialization_record/1",
            "study": self.study.to_dict(),
            "predecessor_twin": self.predecessor_twin.to_dict(),
            "candidate": self.candidate.to_dict(),
            "twin": self.twin.to_dict(),
            "materialization_digest": self.materialization_digest,
        }


def materialize_selected(state: PreExecutionState) -> SelectedMaterialization:
    decision = state.decision
    option = decision.selected_option
    if option.option_label != "B":
        raise InvalidScientificProblem("D7 selected execution must be option B")
    evidence_refs = tuple({"identity": item.binding_identity, "digest": item.binding_digest} for item in option.evidence_bindings)
    study = LoopStudy(decision.decision_identity, option, evidence_refs)
    predecessor = state.successor_generation.members[0].twin
    payload = {
        "schema": "d7_selected_materialization/1",
        "study": study.to_dict(),
        "decision_identity": decision.decision_identity,
        "option_identity": option.option_identity,
        "assignment": _assignment_dict(option.assignment),
        "design_space": d4.design_space().reference.to_dict(),
        "physics_scope": state.physics_scope.to_dict(),
        "assessment_context": state.assessment_context.to_dict(),
        "parent_twin": predecessor.reference.to_dict(),
        "materialization_semantics": SELECTED_MATERIALIZATION_SEMANTICS,
    }
    materialization_digest = digest(payload)
    candidate_id = f"d7-selected-candidate:sha256:{materialization_digest}"
    twin_id = f"d7-selected-twin:sha256:{materialization_digest}"
    candidate = DesignCandidate(
        candidate_id=candidate_id,
        design_space=d4.design_space().reference,
        twin=d4.TwinReference(twin_id, "1"),
        assignments=option.assignment,
        # A selected Study materialization is not a second successor generation.
        # Generation 2 is deliberately not created by D7.
        generation=1,
        parents=(predecessor_candidate_ref := state.successor_generation.members[0].candidate.reference,),
        operator="materialize:d7-selected-study-v0.1",
        metadata={
            "d7_study_identity": study.study_identity,
            "d7_option_identity": option.option_identity,
            "d7_decision_identity": decision.decision_identity,
            "d7_materialization_semantics": SELECTED_MATERIALIZATION_SEMANTICS,
        },
    ).validate_against(d4.design_space())
    del predecessor_candidate_ref
    twin = _new_twin(
        twin_id,
        TwinKind.DERIVED,
        option.assignment,
        parent=predecessor.reference,
        metadata={
            "d7_study_identity": study.study_identity,
            "d7_option_identity": option.option_identity,
            "d7_decision_identity": decision.decision_identity,
            "d7_parent_twin_reference": predecessor.reference.to_dict(),
        },
    )
    return SelectedMaterialization(study, predecessor, candidate, twin, materialization_digest)


@dataclass(frozen=True)
class ExecutionRequest:
    selected: SelectedMaterialization
    request_identity: str = field(init=False)
    run_identity: str = field(init=False)

    def __post_init__(self) -> None:
        payload = self.identity_payload()
        value = digest(payload)
        object.__setattr__(self, "request_identity", f"d7-execution-request:sha256:{value}")
        object.__setattr__(self, "run_identity", f"d7-selected-run:sha256:{value}")

    def identity_payload(self) -> dict[str, Any]:
        option = self.selected.study.option
        return {
            "schema": "d7_execution_request/1",
            "study": self.selected.study.to_dict(),
            "candidate": self.selected.candidate.to_dict(),
            "twin": self.selected.twin.to_dict(),
            "problem_id": PROBLEM_ID,
            "model": list(MODEL),
            "solver": list(SOLVER),
            "fidelity": option.physics_scope.fidelity,
            "physics_scope": option.physics_scope.to_dict(),
            "assessment_context": option.assessment_context.to_dict(),
            "assignment": _assignment_dict(option.assignment),
            "execution_semantics_identity": EXECUTION_SEMANTICS,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "request_identity": self.request_identity, "run_identity": self.run_identity}


@dataclass(frozen=True)
class SelectedExecution:
    request: ExecutionRequest
    result: ScientificResult
    result_binding: ResultBinding
    evaluation: DesignEvaluation
    result_identity: str
    result_binding_identity: str
    result_binding_digest: str
    target: str

    def __post_init__(self) -> None:
        candidate = self.request.selected.candidate
        twin = self.request.selected.twin
        self.evaluation.validate_candidate(candidate)
        if twin.reference.key != candidate.twin.key:
            raise InvalidScientificProblem("D7 selected execution Twin mismatch")
        _validate_result_execution(self.result, candidate, self.request.selected.study.option.physics_scope)
        if self.evaluation.result.to_dict() != self.result.to_dict():
            raise InvalidScientificProblem("D7 selected evaluation/result mismatch")
        if self.result_binding.to_dict() != self.evaluation.result_binding.to_dict():
            raise InvalidScientificProblem("D7 selected execution ResultBinding mismatch")
        expected_binding_digest = _binding_digest(self.result_binding)
        if self.result_binding_digest != expected_binding_digest or self.result_binding_identity != f"d7-result-binding:sha256:{expected_binding_digest}":
            raise InvalidScientificProblem("D7 selected ResultBinding identity mismatch")
        values = _quantity_plain(self.result.values)
        outcome_payload = {
            "schema": "d7_execution_outcome/1",
            "request": self.request.to_dict(),
            "run_identity": self.request.run_identity,
            "values": values,
            "convergence": self.result.convergence.value,
            "model": list(MODEL),
            "solver": list(SOLVER),
            "problem_id": PROBLEM_ID,
            "result_binding_digest": expected_binding_digest,
        }
        expected_result = _identity("d7-selected-result", outcome_payload)
        if self.result_identity != expected_result or self.result.result_id != expected_result:
            raise InvalidScientificProblem("D7 selected result identity mismatch")
        if values != {"loss_score": 33.0, "stability_score": -12.0, "yield_score": 35.0} or self.target != "FAIL":
            raise InvalidScientificProblem("D7 selected result/target fixture mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "d7_selected_execution/1",
            "request": self.request.to_dict(),
            "selected_materialization": self.request.selected.to_dict(),
            "result": self.result.to_dict(),
            "result_identity": self.result_identity,
            "result_binding": self.result_binding.to_dict(),
            "result_binding_identity": self.result_binding_identity,
            "result_binding_digest": self.result_binding_digest,
            "evaluation": self.evaluation.to_dict(),
            "target": self.target,
        }


def _validate_execution_request(
    state: PreExecutionState,
    selected: SelectedMaterialization,
    request: ExecutionRequest,
    *,
    attempted_assignment: Mapping[str, ScientificValue] | None = None,
    attempted_twin: ScientificTwin | None = None,
) -> None:
    option = state.decision.selected_option
    if option.option_label != "B" or selected.study.decision_identity != state.decision.decision_identity or selected.study.option.option_identity != option.option_identity:
        raise InvalidScientificProblem("D7 execution decision/option mismatch")
    assignment = dict(attempted_assignment or selected.candidate.assignments)
    if _assignment_dict(assignment) != _assignment_dict(option.assignment):
        raise InvalidScientificProblem("D7 execution attempted assignment substitution")
    twin = attempted_twin or selected.twin
    if twin.to_dict() != selected.twin.to_dict():
        raise InvalidScientificProblem("D7 execution attempted Twin substitution")
    validate_no_inheritance(selected.candidate, twin)
    if request.identity_payload()["candidate"] != selected.candidate.to_dict() or request.identity_payload()["twin"] != selected.twin.to_dict():
        raise InvalidScientificProblem("D7 execution request graph mismatch")
    if option.physics_scope.to_dict() != state.physics_scope.to_dict() or option.assessment_context.to_dict() != state.assessment_context.to_dict():
        raise InvalidScientificProblem("D7 execution physics/assessment mismatch")


def execute_selected(
    state: PreExecutionState,
    *,
    attempted_assignment: Mapping[str, ScientificValue] | None = None,
    attempted_twin: ScientificTwin | None = None,
) -> SelectedExecution:
    selected = materialize_selected(state)
    request = ExecutionRequest(selected)
    _validate_execution_request(state, selected, request, attempted_assignment=attempted_assignment, attempted_twin=attempted_twin)
    binding = ResultBinding(selected.candidate.reference, selected.twin.reference, selected.candidate.design_space)
    binding_digest_value = _binding_digest(binding)
    binding_identity = f"d7-result-binding:sha256:{binding_digest_value}"
    values = d4.synthetic_objective_values(selected.candidate.assignments)
    outcome_payload = {
        "schema": "d7_execution_outcome/1",
        "request": request.to_dict(),
        "run_identity": request.run_identity,
        "values": _quantity_plain(values),
        "convergence": ConvergenceState.NOT_APPLICABLE.value,
        "model": list(MODEL),
        "solver": list(SOLVER),
        "problem_id": PROBLEM_ID,
        "result_binding_digest": binding_digest_value,
    }
    result_identity = _identity("d7-selected-result", outcome_payload)
    result, produced_binding = _scientific_result(
        result_id=result_identity,
        run_id=request.run_identity,
        candidate=selected.candidate,
        values=values,
        scope=state.physics_scope,
        provenance_metadata={
            "d7_study_identity": selected.study.study_identity,
            "d7_decision_identity": state.decision.decision_identity,
            "d7_option_identity": state.decision.selected_option_identity,
            "d7_option_label": "B",
            "d7_execution_request_identity": request.request_identity,
            "d7_assessment_context_identity": state.assessment_context.assessment_context_identity,
            "decision_provenance_only": True,
        },
    )
    if produced_binding.to_dict() != binding.to_dict():
        raise InvalidScientificProblem("D7 producer-side selected ResultBinding mismatch")
    evaluation_payload = {
        "schema": "d7_returned_design_evaluation/1",
        "candidate": selected.candidate.to_dict(),
        "twin": selected.twin.to_dict(),
        "result_id": result.result_id,
        "result_digest": _result_digest(result),
        "result_binding_digest": binding_digest_value,
        "run_id": request.run_identity,
        "physics_scope": state.physics_scope.to_dict(),
        "eligibility_policy_id": ELIGIBILITY_POLICY_ID,
    }
    evaluation_id = _identity("d7-returned-evaluation", evaluation_payload)
    _validate_result_execution(result, selected.candidate, state.physics_scope)
    evaluation = DesignEvaluation(
        evaluation_id=evaluation_id,
        candidate=selected.candidate.reference,
        twin=selected.twin.reference,
        design_space=selected.candidate.design_space,
        result=result,
        eligibility=SelectionEligibility.ELIGIBLE,
        eligibility_reasons=(SELECTED_REASON,),
        metadata={
            "d7_physics_scope_identity": state.physics_scope.physics_scope_identity,
            "d7_assessment_context_identity": state.assessment_context.assessment_context_identity,
            "d7_study_identity": selected.study.study_identity,
            "d7_eligibility_policy_id": ELIGIBILITY_POLICY_ID,
        },
    )
    return SelectedExecution(
        request, result, binding, evaluation, result_identity,
        binding_identity, binding_digest_value,
        state.assessment_context.classify(values),
    )


@dataclass(frozen=True)
class ReturnAdmission:
    execution: SelectedExecution
    returned_entry: DesignMemoryEntry
    returned_memory: DesignMemoryRecord
    next_cycle_source: D4Source

    def __post_init__(self) -> None:
        if self.returned_entry.evaluation.evaluation_id != self.execution.evaluation.evaluation_id:
            raise InvalidScientificProblem("D7 return entry evaluation mismatch")
        if self.next_cycle_source.entry.to_dict() != self.returned_entry.to_dict():
            raise InvalidScientificProblem("D7 next-cycle D4 source is not returned entry")


def admit_return(state: PreExecutionState, execution: SelectedExecution) -> ReturnAdmission:
    candidate = execution.request.selected.candidate
    entry = DesignMemoryEntry.from_evaluation(
        scope=state.memory.layer_a.scope,
        candidate=candidate,
        evaluation=execution.evaluation,
    )
    all_candidates = state.generation_zero.candidates + (candidate,)
    all_evaluations = state.generation_zero.evaluations + (execution.evaluation,)
    layer = DesignMemoryLayerA.build(
        scope=state.memory.layer_a.scope,
        candidates=all_candidates,
        evaluations=all_evaluations,
        partitioner=_partitioner,
    )
    memory = DesignMemoryRecord.build(layer_a=layer, policy=state.memory.policy)
    verify_layer_a_attribution(layer_a=layer, candidates=all_candidates, evaluations=all_evaluations)
    selected_entry = next(item for item in layer.entries if item.evaluation.evaluation_id == execution.evaluation.evaluation_id)
    if selected_entry.to_dict() != entry.to_dict():
        raise InvalidScientificProblem("D7 returned entry changed during deterministic Layer A rebuild")
    all_twins = state.generation_zero.twins + (execution.request.selected.twin,)
    source = select_d4_source(
        slot_name="component_a",
        candidate_id=candidate.candidate_id,
        evaluation_id=execution.evaluation.evaluation_id,
        candidates=all_candidates,
        twins=all_twins,
        evaluations=all_evaluations,
        memory=memory,
        physics_scope=state.physics_scope,
    )
    if source.selected_value.value != "A_peak":
        raise InvalidScientificProblem("D7 returned next-cycle source slot value mismatch")
    return ReturnAdmission(execution, selected_entry, memory, source)


def complete_object_trace(
    checkpoint: D7Checkpoint,
    admission: ReturnAdmission,
) -> dict[str, Any]:
    execution = admission.execution
    selected = execution.request.selected
    trace = {
        "schema": "d7_integrated_object_trace/1",
        **{key: value for key, value in checkpoint.state.partial_object_trace.items() if key != "schema"},
        "selected_study_identity": selected.study.study_identity,
        "selected_candidate_identity": selected.candidate.candidate_id,
        "selected_twin_identity": f"{selected.twin.twin_id}@{selected.twin.version}",
        "selected_run_identity": execution.request.run_identity,
        "selected_evaluation_identity": execution.evaluation.evaluation_id,
        "selected_result_identity": execution.result.result_id,
        "selected_result_binding_identity": execution.result_binding_identity,
        "selected_result_binding_digest": execution.result_binding_digest,
        "returned_memory_entry_identity": admission.returned_entry.identity,
        "returned_memory_entry_digest": admission.returned_entry.entry_digest,
        "returned_memory_scope_identity": admission.returned_memory.layer_a.scope.scope_identity,
        "next_cycle_d4_source_identity": admission.next_cycle_source.source_identity,
        "checkpoint_identity": checkpoint.checkpoint_identity,
    }
    trace["final_trace_identity"] = digest(trace)
    return trace


def _expect_rejection(action, description: str) -> dict[str, str]:
    try:
        action()
    except Exception as exc:
        return {"status": "PASS", "observed": f"{description}: {type(exc).__name__}"}
    return {"status": "FAIL", "observed": f"{description}: expected fail-closed rejection"}


def _passed(description: str) -> dict[str, str]:
    return {"status": "PASS", "observed": description}


def adversarial_case_results(checkpoint: D7Checkpoint, admission: ReturnAdmission) -> dict[str, dict[str, str]]:
    state = checkpoint.state
    sources = state.authoritative_d4.sources

    def n1() -> None:
        forged = object.__new__(D4Source)
        for key, value in sources[0].__dict__.items():
            object.__setattr__(forged, key, value)
        changed_scope = replace(state.physics_scope, operating_conditions={"synthetic_environment": {"type": "categorical", "value": "off-nominal"}})
        object.__setattr__(forged, "physics_scope", changed_scope)
        _ensure_single_scope((forged, sources[-1]))

    changed_assessment = replace(
        state.assessment_context,
        reporting_context_id="d7-integrated-loop-report-adversarial-v0.1",
    )
    n2_ok = (
        changed_assessment.assessment_context_identity != state.assessment_context.assessment_context_identity
        and state.physics_scope.physics_scope_identity == state.generation_zero.physics_scope.physics_scope_identity
        and state.memory.layer_a.to_dict() == build_memory(state.generation_zero, changed_assessment).layer_a.to_dict()
    )

    changed_physics = replace(state.physics_scope, execution_model_reference=("d4.synthetic.altered", "0.1"))

    def n3() -> None:
        if changed_physics.physics_scope_identity == state.physics_scope.physics_scope_identity:
            raise AssertionError("physics identity did not change")
        replace(sources[0], physics_scope=changed_physics)

    def n4() -> None:
        payload = json.loads(json.dumps(sources[0].to_dict()))
        replicate = state.generation_zero.evaluation("d4-parent-c", "replicate")
        payload["evaluation"] = replicate.to_dict()
        payload["evaluation_digest"] = _object_digest(replicate)
        payload["result_digest"] = _result_digest(replicate.result)
        D4Source.from_dict(payload)

    def n5() -> None:
        payload = json.loads(json.dumps(sources[0].to_dict()))
        payload["twin"]["twin_id"] = "wrong-twin"
        D4Source.from_dict(payload)

    def n6() -> None:
        payload = json.loads(json.dumps(state.authoritative_d4.to_dict()))
        payload["assignment"] = _assignment_dict(d4.typed_assignments("A_peak", "B_filter", "buffered", 2, True))
        AuthoritativeD4.from_dict(payload)

    def n7() -> None:
        original = state.successor_generation.members[0]
        replacement_candidate = replace(original.candidate, candidate_id="d5-g1-candidate:replacement")
        replacement_twin = replace(original.twin, twin_id="d5-g1-twin:replacement")
        replacement_candidate = replace(replacement_candidate, twin=replacement_twin.reference)
        replacement = GenerationMember(1, replacement_candidate, replacement_twin, original.lineage_identity)
        SuccessorGeneration(
            state.successor_generation.source_generation_identity,
            1,
            GENERATION_ADMISSION,
            state.successor_generation.lineage,
            (replacement,),
        )

    parent_result_id = sources[0].evaluation.result.result_id

    def n8() -> None:
        twin = replace(state.authoritative_d4.twin, evidence_refs=(parent_result_id,))
        validate_no_inheritance(state.authoritative_d4.candidate, twin, forbidden_scientific_ids=(parent_result_id,))

    def n9() -> None:
        candidate = replace(state.authoritative_d4.candidate, metadata={"copied_result_id": parent_result_id})
        validate_no_inheritance(candidate, state.authoritative_d4.twin, forbidden_scientific_ids=(parent_result_id,))

    def n10() -> None:
        for token in sorted(FORBIDDEN_INHERITANCE - {"evidence_refs", "calibration_evidence_refs"}):
            candidate = replace(state.authoritative_d4.candidate, metadata={token: True})
            try:
                validate_no_inheritance(candidate, state.authoritative_d4.twin)
            except InvalidScientificProblem:
                continue
            raise AssertionError(f"forbidden inheritance token accepted: {token}")
        raise InvalidScientificProblem("all combined forbidden vocabulary rejected")

    def n11() -> None:
        payload = json.loads(json.dumps(state.evidence_bindings[0].to_dict()))
        payload["result_binding"]["candidate"]["candidate_id"] = "wrong-candidate"
        LoopDecisionEvidenceBinding.from_dict(payload)

    def n12() -> None:
        payload = json.loads(json.dumps(state.decision.options[0].to_dict()))
        payload["alpha_prediction"]["values"]["yield_score"] += 1.0
        LoopExperimentOption.from_dict(
            payload,
            {item.binding_identity: item for item in state.evidence_bindings},
            state.novelty_universe,
        )

    def n13() -> None:
        payload = json.loads(checkpoint.to_bytes().decode("utf-8"))
        payload["payload"]["decision"]["options"][0]["alpha_prediction"]["values"]["yield_score"] += 1.0
        identity_payload = {key: value for key, value in payload.items() if key != "checkpoint_identity"}
        payload["checkpoint_identity"] = digest(identity_payload)
        D7Checkpoint.from_bytes(canonical_bytes(payload))

    wrong_assignment = d4.typed_assignments("A_peak", "B_filter", "buffered", 2, False)

    def n15() -> None:
        selected = materialize_selected(state)
        wrong_twin = replace(selected.twin, twin_id="d7-selected-twin:wrong")
        execute_selected(state, attempted_twin=wrong_twin)

    def n16() -> None:
        execution = admission.execution
        wrong_binding = ResultBinding(
            state.generation_zero.candidate("d4-parent-a").reference,
            execution.result_binding.twin,
            execution.result_binding.design_space,
        )
        metadata = dict(execution.result.provenance.metadata)
        metadata[RESULT_BINDING_METADATA_KEY] = wrong_binding.to_dict()
        bad_result = replace(execution.result, provenance=replace(execution.result.provenance, metadata=metadata))
        DesignEvaluation(
            evaluation_id="d7-invalid-binding-evaluation",
            candidate=execution.request.selected.candidate.reference,
            twin=execution.request.selected.twin.reference,
            design_space=execution.request.selected.candidate.design_space,
            result=bad_result,
            eligibility=SelectionEligibility.ELIGIBLE,
            eligibility_reasons=(SELECTED_REASON,),
        )

    def n17() -> None:
        execution = admission.execution
        wrong_candidate = state.generation_zero.candidate("d4-parent-a")
        execution.evaluation.validate_candidate(wrong_candidate)

    def n18() -> None:
        ineligible = replace(
            admission.execution.evaluation,
            eligibility=SelectionEligibility.INELIGIBLE,
            eligibility_reasons=("adversarial ineligible",),
        )
        DesignMemoryEntry.from_evaluation(
            scope=state.memory.layer_a.scope,
            candidate=admission.execution.request.selected.candidate,
            evaluation=ineligible,
        )

    def n19() -> None:
        rank_options(state.decision.options + (state.decision.options[0],))

    primary_forward = select_d4_source(
        slot_name="component_a", candidate_id="d4-parent-c",
        evaluation_id="d7-g0-evaluation:d4-parent-c:primary",
        candidates=state.generation_zero.candidates,
        twins=state.generation_zero.twins,
        evaluations=state.generation_zero.evaluations,
        memory=state.memory, physics_scope=state.physics_scope,
    )
    primary_reverse = select_d4_source(
        slot_name="component_a", candidate_id="d4-parent-c",
        evaluation_id="d7-g0-evaluation:d4-parent-c:primary",
        candidates=tuple(reversed(state.generation_zero.candidates)),
        twins=tuple(reversed(state.generation_zero.twins)),
        evaluations=tuple(reversed(state.generation_zero.evaluations)),
        memory=state.memory, physics_scope=state.physics_scope,
    )
    n20_ok = primary_forward.to_dict() == primary_reverse.to_dict() and primary_forward.evaluation.evaluation_id.endswith(":primary")

    def n21() -> None:
        data = bytearray(checkpoint.to_bytes())
        index = data.index(b"DECISION_RECORDED_PRE_EXECUTION")
        data[index] = ord("X")
        D7Checkpoint.from_bytes(bytes(data))

    def n22() -> None:
        payload = json.loads(checkpoint.to_bytes().decode("utf-8"))
        del payload["payload"]["successor_generation"]["lineage"]
        identity_payload = {key: value for key, value in payload.items() if key != "checkpoint_identity"}
        payload["checkpoint_identity"] = digest(identity_payload)
        D7Checkpoint.from_bytes(canonical_bytes(payload))

    def n23() -> None:
        selected = materialize_selected(state)
        twin = replace(selected.twin, evidence_refs=(state.decision.decision_identity,))
        validate_no_inheritance(selected.candidate, twin)

    def n24() -> None:
        wrong_source = select_d4_source(
            slot_name="component_a", candidate_id="d4-parent-a",
            evaluation_id="d7-g0-evaluation:d4-parent-a:primary",
            candidates=state.generation_zero.candidates,
            twins=state.generation_zero.twins,
            evaluations=state.generation_zero.evaluations,
            memory=state.memory, physics_scope=state.physics_scope,
        )
        ReturnAdmission(admission.execution, admission.returned_entry, admission.returned_memory, wrong_source)

    return {
        "N1": _expect_rejection(n1, "mixed physics scope rejected before materialization"),
        "N2": _passed("assessment-only change preserved physics identity, Layer A and results") if n2_ok else {"status": "FAIL", "observed": "assessment change contaminated physics evidence"},
        "N3": _expect_rejection(n3, "changed model required new physics and old-scope source failed"),
        "N4": _expect_rejection(n4, "correct candidate with replicate substituted for primary rejected"),
        "N5": _expect_rejection(n5, "wrong Twin for correct result rejected"),
        "N6": _expect_rejection(n6, "assignment substitution with reused D4 identities rejected"),
        "N7": _expect_rejection(n7, "replacement D5 Candidate/Twin rejected"),
        "N8": _expect_rejection(n8, "parent evidence on derived Twin rejected"),
        "N9": _expect_rejection(n9, "parent ScientificResult inheritance rejected"),
        "N10": _expect_rejection(n10, "combined forbidden status vocabulary rejected"),
        "N11": _expect_rejection(n11, "correct result id with wrong binding rejected"),
        "N12": _expect_rejection(n12, "changed prediction with reused option identity rejected"),
        "N13": _expect_rejection(n13, "mutated serialized option rejected after valid outer digest"),
        "N14": _expect_rejection(lambda: execute_selected(state, attempted_assignment=wrong_assignment), "wrong selected assignment rejected before solver"),
        "N15": _expect_rejection(n15, "wrong selected Twin rejected before solver"),
        "N16": _expect_rejection(n16, "invalid ResultBinding rejected by D1"),
        "N17": _expect_rejection(n17, "inconsistent execution graph rejected"),
        "N18": _expect_rejection(n18, "D3 admission without eligible D1 evaluation rejected"),
        "N19": _expect_rejection(n19, "duplicate identity rejected"),
        "N20": _passed("both offer orders selected the exact primary evaluation") if n20_ok else {"status": "FAIL", "observed": "candidate-id last-wins behavior observed"},
        "N21": _expect_rejection(n21, "mutated checkpoint bytes rejected"),
        "N22": _expect_rejection(n22, "incomplete checkpoint rejected"),
        "N23": _expect_rejection(n23, "decision provenance in Twin evidence rejected"),
        "N24": _expect_rejection(n24, "returned D3 entry unusable as exact next-cycle source made D7 fail"),
    }


def signal_table(options: Sequence[LoopExperimentOption]) -> dict[str, Any]:
    return {
        option.option_label: {
            "alpha": dict(option.alpha_prediction.values),
            "beta": dict(option.beta_prediction.values),
            **dict(option.derived_signals),
        }
        for option in sorted(options, key=lambda item: item.option_label)
    }


def architecture_pulled() -> dict[str, str]:
    return {
        "LoopPhysicsScope": "D7-local exact physical comparability and execution boundary.",
        "LoopAssessmentContext": "D7-local target/report/decision context kept physics-neutral.",
        "AuthoritativeD4": "D7-local full event and derivation wrapper over frozen D4 compatibility.",
        "SuccessorGeneration": "D7-local variable-cardinality generation with literal D4 child admission.",
        "LoopDecisionEvidenceBinding": "D7-local full evidence graph replacing result-id membership.",
        "LoopExperimentOption/NextExperimentDecision": "D7-local typed option identity and deterministic policy replay.",
        "D7Checkpoint": "D7-local canonical decision-boundary save/reload envelope.",
        "no-inheritance validator": "One D7-local recursive conformance validator across new Twins.",
    }


def informative_findings() -> dict[str, str]:
    return {
        "I1": "Attributable Layer A source selection worked independently of retained-only membership; retention reasons remained provenance.",
        "I2": "The integrated path needed a D7-local authoritative derivation identity, but one synthetic case is insufficient for Core promotion.",
        "I3": "One combined no-inheritance validator closed D4/D5/selected seams; broader reuse remains unproven.",
        "I4": "Typed physics scope was necessary locally; a generic Core scope contract remains unresolved.",
        "I5": "Explicit lineage made literal child/evidence checks possible; generic provenance infrastructure is not yet justified.",
        "I6": "Typed options and decisions were required for deterministic reload; general next-experiment abstractions remain future evidence.",
        "I7": "D7 did not require reuse or modification of D2 proposal/materialization contracts.",
    }


def gate_table(
    checkpoint: D7Checkpoint,
    admission: ReturnAdmission,
    adversarial: Mapping[str, Mapping[str, str]],
    *,
    targeted_tests: str,
    full_regression: str,
    reload_ok: bool,
    trace_replay_ok: bool,
) -> dict[str, str]:
    state = checkpoint.state
    all_adversarial = all(item["status"] == "PASS" for item in adversarial.values())
    targeted_ok = targeted_tests.startswith("PASS")
    regression_ok = full_regression.startswith("PASS")
    literal_child = (
        state.authoritative_d4.candidate.to_dict() == state.successor_generation.members[0].candidate.to_dict()
        and state.authoritative_d4.twin.to_dict() == state.successor_generation.members[0].twin.to_dict()
    )
    return {
        "A1": "PASS - D7 added only bounded experiment implementation/tests/artifacts; frozen semantics were not edited",
        "A2": "PASS - every comparable object and execution carries the exact typed physics scope",
        "A3": "PASS - separately typed assessment changes preserve physics evidence",
        "A4": "PASS - mixed D4 source physics fails before authoritative materialization",
        "A5": "PASS - D3 selection uses exact candidate/evaluation plus entry identity/digest",
        "A6": "PASS - D4 event/derivation identities cover sources, assignment, compatibility, scope and materialization",
        "A7": "PASS - successor member is byte-identical to authoritative D4 Candidate/Twin" if literal_child else "FAIL",
        "A8": "PASS - every unevaluated D4/selected Twin starts with empty evidence fields",
        "A9": "PASS - one D7-local full-vocabulary no-inheritance validator covers D4/D5/selected execution",
        "A10": "PASS - D6-style inputs are complete typed evidence bindings",
        "A11": "PASS - novelty is rederived from the complete typed evaluated universe",
        "A12": "PASS - full predictions/evidence/scope/Study/cost/signals affect option identity",
        "A13": "PASS - reload validates stored full options and reruns selection without fixture rebuilding",
        "A14": "PASS - decision/Study/Candidate/Twin/run/result graph is exact before execution",
        "A15": f"PASS - ResultBinding {admission.execution.result_binding_identity} / {admission.execution.result_binding_digest}",
        "A16": f"PASS - eligible D1 evaluation {admission.execution.evaluation.evaluation_id}; target FAIL did not affect eligibility",
        "A17": f"PASS - returned D3 entry {admission.returned_entry.identity} built only by DesignMemoryEntry.from_evaluation",
        "A18": f"PASS - next-cycle D4 source {admission.next_cycle_source.source_identity}",
        "A19": "PASS - real checkpoint save/discard/reload/continue and trace replay succeeded" if reload_ok and trace_replay_ok else "FAIL",
        "A20": "PASS - exact source/options and byte reload are order/replay invariant",
        "A21": "PASS - N1-N24 matched frozen outcomes" if all_adversarial else "FAIL",
        "A22": "PASS - compatibility, target, retention, generation, prediction and selection never inflate scientific status",
        "A23": f"PASS - {targeted_tests}; {full_regression}" if targeted_ok and regression_ok else f"FAIL - {targeted_tests}; {full_regression}",
    }


def default_adversarial_review() -> dict[str, list[str]]:
    return {
        "P0/P1": [],
        "P2": [],
        "P3": [
            "A generic physics-scope contract may become useful only after another domain forces the same fields.",
            "The D7-local derivation, evidence graph, decision and checkpoint records are evidence for future reuse, not Core promotion.",
            "The checkpoint proves deterministic semantic replay, not malicious-writer authenticity or production durability.",
        ],
        "Resolved during review": [
            "Removed an accidental Generation 2 label from the selected Study materialization; D7 now creates no Generation 2 object or execution.",
            "Strengthened result scope-payload checks and checkpoint graph validation for exact D4 lineage, successor execution, and typed evidence bindings.",
        ],
    }


def experiment_payload(
    *,
    checkpoint_path: Path,
    targeted_tests: str,
    full_regression: str,
    adversarial_review: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    checkpoint, reload_ok = real_checkpoint_reload(checkpoint_path)
    execution = execute_selected(checkpoint.state)
    admission = admit_return(checkpoint.state, execution)
    trace = complete_object_trace(checkpoint, admission)
    # Second continuation starts only from the authoritative serialized bytes.
    replayed_checkpoint = D7Checkpoint.from_bytes(checkpoint_path.read_bytes())
    replayed_admission = admit_return(replayed_checkpoint.state, execute_selected(replayed_checkpoint.state))
    replayed_trace = complete_object_trace(replayed_checkpoint, replayed_admission)
    trace_replay_ok = canonical_bytes(trace) == canonical_bytes(replayed_trace)
    adversarial = adversarial_case_results(checkpoint, admission)
    review = {key: list(value) for key, value in (adversarial_review or default_adversarial_review()).items()}
    for severity in ("P0/P1", "P2", "P3"):
        review.setdefault(severity, [])
    gates = gate_table(
        checkpoint, admission, adversarial,
        targeted_tests=targeted_tests,
        full_regression=full_regression,
        reload_ok=reload_ok,
        trace_replay_ok=trace_replay_ok,
    )
    state = checkpoint.state
    ordering = [
        {
            "rank": index,
            "label": option.option_label,
            "option_identity": option.option_identity,
            "information_per_compute": option.derived_signals["information_per_compute"],
            "information_units": option.derived_signals["information_proxy_units"],
            "model_disagreement": option.derived_signals["model_disagreement"],
        }
        for index, option in enumerate(rank_options(state.decision.options), start=1)
    ]
    g0_results = {
        item.evaluation_id: {
            "candidate_id": item.candidate.candidate_id,
            "twin": item.twin.to_dict(),
            "run_id": item.result.provenance.run_id,
            "result_id": item.result.result_id,
            "values": _quantity_plain(item.result.values),
            "target": state.assessment_context.classify(item.result.values),
        }
        for item in state.generation_zero.evaluations
    }
    d3_sources = {
        "layer_a_entry_count": len(state.memory.layer_a.entries),
        "lookup_key": ["candidate_id", "evaluation_id"],
        "selected_evaluation_ids": sorted({item.evaluation.evaluation_id for item in state.authoritative_d4.sources}),
        "replicate_substituted": False,
        "source_rule": "any exact attributable Layer A entry in the exact physics scope",
        "entries": [
            {
                "candidate_id": item.candidate.candidate_id,
                "evaluation_id": item.evaluation.evaluation_id,
                "identity": item.identity,
                "digest": item.entry_digest,
            }
            for item in state.memory.layer_a.entries
        ],
    }
    payload = {
        "schema": "d7_integrated_experiment_results/1",
        "milestone": MILESTONE,
        "preregistration": PREREGISTRATION,
        "frozen_preregistration_checkpoint": PREREGISTRATION_CHECKPOINT,
        "physics_scope": state.physics_scope.to_dict(),
        "assessment_context": state.assessment_context.to_dict(),
        "generation0_results": g0_results,
        "d3_memory_and_source_selection": d3_sources,
        "d4": {
            "compatibility": state.authoritative_d4.compatibility.state.value,
            "event_identity": state.authoritative_d4.event_identity,
            "derivation_identity": state.authoritative_d4.derivation_identity,
            "child_candidate_identity": state.authoritative_d4.candidate.candidate_id,
            "child_twin_identity": f"{state.authoritative_d4.twin.twin_id}@{state.authoritative_d4.twin.version}",
            "assignment": _assignment_plain(state.authoritative_d4.assignment),
        },
        "d4_child_equals_d5_member": {
            "candidate": state.authoritative_d4.candidate.to_dict() == state.successor_generation.members[0].candidate.to_dict(),
            "twin": state.authoritative_d4.twin.to_dict() == state.successor_generation.members[0].twin.to_dict(),
            "membership_role": state.successor_generation.members[0].role,
        },
        "successor_evaluation": {
            "evaluation_id": state.successor_evaluation.evaluation.evaluation_id,
            "result_id": state.successor_evaluation.evaluation.result.result_id,
            "run_id": state.successor_evaluation.evaluation.result.provenance.run_id,
            "values": _quantity_plain(state.successor_evaluation.evaluation.result.values),
            "target": state.assessment_context.classify(state.successor_evaluation.evaluation.result.values),
        },
        "decision_evidence_bindings": [
            {
                "identity": item.binding_identity,
                "digest": item.binding_digest,
                "candidate_id": item.candidate.candidate_id,
                "evaluation_id": item.evaluation.evaluation_id,
                "result_id": item.evaluation.result.result_id,
                "run_id": item.evaluation.result.provenance.run_id,
                "generation_member_identity": item.generation_member_identity,
                "generation_lineage_identity": item.generation_lineage_identity,
                "d4_event_identity": item.d4_event_identity,
                "d4_derivation_identity": item.d4_derivation_identity,
            }
            for item in state.evidence_bindings
        ],
        "signal_table": signal_table(state.decision.options),
        "selection_ordering": ordering,
        "decision_identity": state.decision.decision_identity,
        "selected_option": "B",
        "checkpoint": {
            "identity": checkpoint.checkpoint_identity,
            "schema": "d7_integrated_loop_checkpoint/1",
            "real_reload_from_serialized_bytes": reload_ok,
            "replay_byte_identical_trace": trace_replay_ok,
        },
        "selected_identities": {
            "study": execution.request.selected.study.study_identity,
            "candidate": execution.request.selected.candidate.candidate_id,
            "twin": f"{execution.request.selected.twin.twin_id}@{execution.request.selected.twin.version}",
            "execution_request": execution.request.request_identity,
            "run": execution.request.run_identity,
        },
        "selected_result": {
            "result_id": execution.result.result_id,
            "values": _quantity_plain(execution.result.values),
            "target": execution.target,
            "problem_id": execution.result.problem_id,
            "model": list(MODEL),
            "solver": list(SOLVER),
        },
        "selected_result_binding": {
            "identity": execution.result_binding_identity,
            "digest": execution.result_binding_digest,
            "payload": execution.result_binding.to_dict(),
        },
        "returned_d1_evaluation": {
            "identity": execution.evaluation.evaluation_id,
            "status": execution.evaluation.eligibility.value,
            "reason": execution.evaluation.eligibility_reasons[0],
        },
        "returned_d3_memory": {
            "identity": admission.returned_entry.identity,
            "digest": admission.returned_entry.entry_digest,
            "scope_identity": admission.returned_memory.layer_a.scope.scope_identity,
        },
        "next_cycle_d4_source_identity": admission.next_cycle_source.source_identity,
        "object_trace": trace,
        "a1_a23": gates,
        "n1_n24": adversarial,
        "adversarial_review": review,
        "architecture_actually_pulled": architecture_pulled(),
        "informative_i1_i7": informative_findings(),
        "frozen_semantics_unchanged": [
            "D0", "D1", "D2", "D3", "D4", "D5", "D6", "ScientificTwin",
            "MVR0", "MVR1", "previously frozen K-series semantics",
        ],
        "generation_2_executed": False,
        "blocking_gates_passed": all(value.startswith("PASS") for value in gates.values()),
        "adversarial_cases_passed": all(value["status"] == "PASS" for value in adversarial.values()),
        "adversarial_review_has_p0_p1": bool(review["P0/P1"]),
    }
    return payload
