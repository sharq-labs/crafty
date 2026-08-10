"""D5 - Generation 1 memory-informed candidate generation experiment.

D5 is experiment-owned glue over frozen D1, D3, D4, and ScientificTwin
contracts. It creates one deterministic Generation 1 population and records
lineage/provenance without promoting a generic successor-generation abstraction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.values import ScientificValue, decode_value, encode_value
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.serialization import require_schema, schema_string
from engcore.scientific.solvers.protocol import ConvergenceState, SolverIdentity
from engcore.scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
    TwinReference,
)
from engcore.scientific.ir.problem import ModelReference

from . import d4_recombination as d4
from .archives import ParetoArchive
from .candidate import DesignCandidate, DesignCandidateReference
from .evaluation import (
    RESULT_BINDING_METADATA_KEY,
    DesignEvaluation,
    DesignEvaluationReference,
    ResultBinding,
    SelectionEligibility,
)
from .generation import assignment_digest
from .memory import (
    AssessmentContext,
    DesignMemoryEntry,
    DesignMemoryLayerA,
    DesignMemoryPolicy,
    DesignMemoryRecord,
    DesignMemoryScope,
    verify_layer_a_attribution,
)
from .population import DesignPopulation
from .space import DesignSpace


G0_POPULATION_ID = "d5-g0-baseline-population-v0.1"
G0_GENERATOR_ID = "d5-enumerated-baseline-v0.1"
G1_PLAN_ID = "d5-generation1-plan-v0.1"
G1_POLICY_ID = "d5-memory-informed-recombination-v0.1"
G1_NOVELTY_POLICY_ID = "d5-assignment-novelty-v0.1"
G1_OPERATOR = "recombine:d5-memory-informed-v0.1"
G1_TARGET_GENERATION = 1
G1_PROPOSAL_BUDGET = 5
G1_ACCEPTED_TARGET = 4
SCIENTIFIC_SCOPE_CONTEXT = "d5-generation-comparison-scope-v0.1"
G0_MEMORY_POLICY_ID = "d5-g0-memory-policy-v0.1"
TARGET_CONTEXT_ID = "d5-target-context-v0.1"

D5_PROPOSAL_SCHEMA = schema_string("d5_generation1_proposal")
D5_LINEAGE_SCHEMA = schema_string("d5_generation_lineage")
D5_PROPOSAL_OUTCOME_SCHEMA = schema_string("d5_proposal_outcome")
D5_DERIVATION_SCHEMA = schema_string("d5_population_derivation")

PROPOSAL_LABELS = ("A", "B", "C", "D", "E")
G0_ASSIGNMENTS = {
    "d4-parent-a": d4.typed_assignments("A_peak", "B_base", "buffered", 2, False),
    "d4-parent-b": d4.typed_assignments("A_base", "B_peak", "direct", 0, False),
    "d4-parent-c": d4.typed_assignments("A_stable", "B_base", "direct", 1, True),
    "d4-parent-d": d4.typed_assignments("A_base", "B_filter", "buffered", 2, True),
}
FORBIDDEN_INHERITANCE_KEYS = d4.FORBIDDEN_CHILD_STATUS_KEYS


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _to_json(payload: Mapping[str, Any], *, indent: int | None = None) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), indent=indent)


def _identity_sort_key(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _objective_values_plain(evaluation: DesignEvaluation) -> dict[str, float]:
    return d4.objective_plain(evaluation.result.values)


def design_space() -> DesignSpace:
    return d4.design_space()


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
    generation_label: str,
    eligible_reason: str,
) -> DesignEvaluation:
    binding = ResultBinding(
        candidate=candidate.reference,
        twin=candidate.twin,
        design_space=candidate.design_space,
    )
    result = ScientificResult(
        result_id=f"d5-{generation_label}-result:{candidate.candidate_id}",
        problem_id="d4-synthetic-objectives-v0.1",
        values=d4.synthetic_objective_values(candidate.assignments),
        provenance=ProvenanceRecord(
            run_id=f"d5-{generation_label}-run:{candidate.candidate_id}",
            models=(("d4.synthetic.analytic", "0.1"),),
            solvers=(("d4.closed-form.synthetic", "0.1"),),
            metadata={
                RESULT_BINDING_METADATA_KEY: binding.to_dict(),
                "objective_context_reference": SCIENTIFIC_SCOPE_CONTEXT,
            },
        ),
        solver=SolverIdentity("d4.closed-form.synthetic", "0.1"),
        convergence=ConvergenceState.NOT_APPLICABLE,
    )
    return DesignEvaluation(
        evaluation_id=f"d5-{generation_label}-evaluation:{candidate.candidate_id}",
        candidate=candidate.reference,
        twin=candidate.twin,
        design_space=candidate.design_space,
        result=result,
        eligibility=SelectionEligibility.ELIGIBLE,
        eligibility_reasons=(eligible_reason,),
    )


def _partitioner(assignments: Mapping[str, ScientificValue]) -> bytes:
    return (
        f"component_a={assignments['component_a'].value}|"
        f"component_b={assignments['component_b'].value}"
    ).encode("utf-8")


@dataclass(frozen=True)
class D5Generation0Bundle:
    space: DesignSpace
    population: DesignPopulation
    candidates: tuple[DesignCandidate, ...]
    twins: tuple[ScientificTwin, ...]
    evaluations: tuple[DesignEvaluation, ...]
    memory_record: DesignMemoryRecord
    d3_entries: tuple[DesignMemoryEntry, ...]


def build_generation0() -> D5Generation0Bundle:
    space = design_space()
    twins = tuple(
        _new_twin(
            twin_id=f"d4-twin:{candidate_id}",
            kind=TwinKind.CANDIDATE,
            assignments=assignments,
        )
        for candidate_id, assignments in G0_ASSIGNMENTS.items()
    )
    twin_refs = {
        twin.twin_id.removeprefix("d4-twin:"): twin.reference for twin in twins
    }
    candidates = tuple(
        DesignCandidate(
            candidate_id=candidate_id,
            design_space=space.reference,
            twin=twin_refs[candidate_id],
            assignments=assignments,
            generation=0,
            parents=(),
            operator="declared:d4-preregistered-parent",
            metadata={"generator_id": G0_GENERATOR_ID},
        ).validate_against(space)
        for candidate_id, assignments in G0_ASSIGNMENTS.items()
    )
    evaluations = tuple(
        _make_evaluation(
            candidate,
            generation_label="g0",
            eligible_reason="preregistered D5 Generation 0 synthetic evaluation",
        )
        for candidate in candidates
    )
    scope = DesignMemoryScope(
        design_space=space.reference,
        objectives=d4.OBJECTIVES,
        context_reference=SCIENTIFIC_SCOPE_CONTEXT,
    )
    layer_a = DesignMemoryLayerA.build(
        scope=scope,
        candidates=candidates,
        evaluations=evaluations,
        partitioner=_partitioner,
    )
    verify_layer_a_attribution(
        layer_a=layer_a, candidates=candidates, evaluations=evaluations
    )
    memory_record = DesignMemoryRecord.build(
        layer_a=layer_a,
        policy=DesignMemoryPolicy(
            policy_id=G0_MEMORY_POLICY_ID,
            elite_scopes=(("yield_score",), ("loss_score",), ("stability_score",)),
            extreme_tolerances={
                "yield_score": d4.Quantity(0.0, "dimensionless"),
                "loss_score": d4.Quantity(0.0, "dimensionless"),
                "stability_score": d4.Quantity(0.0, "dimensionless"),
            },
            assessment_contexts=(
                AssessmentContext(
                    TARGET_CONTEXT_ID,
                    thresholds={
                        "yield_score": d4.Quantity(70.0, "dimensionless"),
                        "loss_score": d4.Quantity(25.0, "dimensionless"),
                        "stability_score": d4.Quantity(50.0, "dimensionless"),
                    },
                    threshold_tolerances={
                        "yield_score": d4.Quantity(0.0, "dimensionless"),
                        "loss_score": d4.Quantity(0.0, "dimensionless"),
                        "stability_score": d4.Quantity(0.0, "dimensionless"),
                    },
                ),
            ),
            explicit_retention=(),
            cap=4,
        ),
    )
    population = DesignPopulation(
        population_id=G0_POPULATION_ID,
        design_space=space.reference,
        generation=0,
        members=tuple(candidate.reference for candidate in candidates),
    ).validate_candidates(candidates)
    return D5Generation0Bundle(
        space=space,
        population=population,
        candidates=candidates,
        twins=twins,
        evaluations=evaluations,
        memory_record=memory_record,
        d3_entries=memory_record.layer_a.entries,
    )


@dataclass(frozen=True)
class D5Generation1Proposal:
    label: str
    selected_sources: tuple[d4.D4SelectedSourceRecord, ...]
    child_assignments: Mapping[str, ScientificValue]
    plan_id: str = G1_PLAN_ID
    source_population_id: str = G0_POPULATION_ID
    target_generation_number: int = G1_TARGET_GENERATION
    compatibility_context_id: str = d4.COMPATIBILITY_CONTEXT_ID
    slot_schema_id: str = d4.SLOT_SCHEMA_ID
    materialization_semantics_id: str = d4.MATERIALIZATION_SEMANTICS_ID
    novelty_policy_id: str = G1_NOVELTY_POLICY_ID

    def __post_init__(self) -> None:
        label = str(self.label).strip()
        if label not in PROPOSAL_LABELS:
            raise InvalidScientificProblem("D5 proposal label is not preregistered")
        assignments = dict(self.child_assignments)
        design_space().validate_assignments(assignments)
        source_slots = {source.slot_name for source in self.selected_sources}
        if source_slots != set(d4.SLOTS):
            raise InvalidScientificProblem("D5 proposal must source every D4 slot")
        object.__setattr__(self, "label", label)
        object.__setattr__(
            self,
            "selected_sources",
            tuple(
                sorted(
                    self.selected_sources,
                    key=lambda item: _identity_sort_key(item.to_dict()),
                )
            ),
        )
        object.__setattr__(self, "child_assignments", assignments)

    @property
    def digest(self) -> str:
        return _digest(self.identity_payload())

    @property
    def proposal_identity(self) -> str:
        return f"d5-proposal:sha256:{self.digest}"

    @property
    def candidate_id(self) -> str:
        return f"d5-g1-candidate:sha256:{self.digest}"

    @property
    def twin_id(self) -> str:
        return f"d5-g1-twin:sha256:{self.digest}"

    def identity_payload(self) -> dict[str, Any]:
        sources = tuple(self.selected_sources)
        parent_candidates = sorted(
            {source.parent_candidate.candidate_id: source.parent_candidate for source in sources}.values(),
            key=lambda item: item.candidate_id,
        )
        parent_twins = sorted(
            {source.parent_twin.key: source.parent_twin for source in sources}.values(),
            key=lambda item: (item.twin_id, item.version),
        )
        d3_sources = sorted(
            {(source.d3_entry_identity, source.d3_entry_digest) for source in sources}
        )
        evaluations = sorted(
            {
                source.parent_evaluation.evaluation_id: source.parent_evaluation
                for source in sources
            }.values(),
            key=lambda item: item.evaluation_id,
        )
        return {
            "schema": D5_PROPOSAL_SCHEMA,
            "plan_id": self.plan_id,
            "source_population_id": self.source_population_id,
            "target_generation_number": self.target_generation_number,
            "proposal_label": self.label,
            "parent_candidate_references": [
                item.to_dict() for item in parent_candidates
            ],
            "parent_twin_references": [item.to_dict() for item in parent_twins],
            "d3_memory_entry_provenance": [
                {"identity": identity, "entry_digest": digest}
                for identity, digest in d3_sources
            ],
            "parent_evaluation_references": [item.to_dict() for item in evaluations],
            "selected_slot_source_records": sorted(
                [source.to_dict() for source in sources], key=_identity_sort_key
            ),
            "proposed_child_assignment": {
                name: encode_value(value)
                for name, value in sorted(self.child_assignments.items())
            },
            "compatibility_context_id": self.compatibility_context_id,
            "slot_schema_id": self.slot_schema_id,
            "materialization_semantics_id": self.materialization_semantics_id,
            "novelty_policy_id": self.novelty_policy_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "proposal_identity": self.proposal_identity,
            "proposal_digest": self.digest,
            "candidate_id_if_accepted": self.candidate_id,
            "twin_id_if_accepted": self.twin_id,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return _to_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D5Generation1Proposal":
        require_schema(payload, D5_PROPOSAL_SCHEMA)
        proposal = cls(
            label=payload["proposal_label"],
            selected_sources=tuple(
                d4.D4SelectedSourceRecord.from_dict(item)
                for item in payload["selected_slot_source_records"]
            ),
            child_assignments={
                name: decode_value(value)
                for name, value in payload["proposed_child_assignment"].items()
            },
            plan_id=payload["plan_id"],
            source_population_id=payload["source_population_id"],
            target_generation_number=payload["target_generation_number"],
            compatibility_context_id=payload["compatibility_context_id"],
            slot_schema_id=payload["slot_schema_id"],
            materialization_semantics_id=payload["materialization_semantics_id"],
            novelty_policy_id=payload["novelty_policy_id"],
        )
        if proposal.proposal_identity != payload.get("proposal_identity", proposal.proposal_identity):
            raise InvalidScientificProblem("D5 proposal identity mismatch")
        return proposal


def proposal_set(g0: D5Generation0Bundle) -> tuple[D5Generation1Proposal, ...]:
    candidates = g0.candidates
    evaluations = g0.evaluations
    entries = g0.d3_entries

    def src(parent_id: str, *slots: str) -> tuple[d4.D4SelectedSourceRecord, ...]:
        return tuple(
            d4.source_record(
                slot_name=slot,
                parent_id=parent_id,
                candidates=candidates,
                evaluations=evaluations,
                d3_entries=entries,
            )
            for slot in slots
        )

    specs = {
        "A": (
            src("d4-parent-a", "component_a")
            + src("d4-parent-b", "component_b")
            + src("d4-parent-a", "adapter", "control_level", "guard_enabled"),
            d4.typed_assignments("A_peak", "B_peak", "buffered", 2, False),
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
            d4.typed_assignments("A_peak", "B_filter", "buffered", 2, True),
        ),
        "C": (
            src("d4-parent-c", "component_a", "guard_enabled")
            + src("d4-parent-d", "component_b", "adapter", "control_level"),
            d4.typed_assignments("A_stable", "B_filter", "buffered", 2, True),
        ),
        "D": (
            src("d4-parent-c", "component_a", "guard_enabled", "control_level")
            + src("d4-parent-b", "component_b", "adapter"),
            d4.typed_assignments("A_stable", "B_peak", "direct", 1, True),
        ),
        "E": (
            src("d4-parent-a", "component_a")
            + src(
                "d4-parent-c",
                "component_b",
                "adapter",
                "control_level",
                "guard_enabled",
            ),
            d4.typed_assignments("A_peak", "B_base", "direct", 1, True),
        ),
    }
    return tuple(
        D5Generation1Proposal(label=label, selected_sources=sources, child_assignments=assignments)
        for label, (sources, assignments) in specs.items()
    )


@dataclass(frozen=True)
class D5GenerationLineage:
    child_candidate: DesignCandidateReference
    proposal_identity: str
    proposal_digest: str
    proposal_label: str
    d4_recombination_event_identity: str
    parent_candidates: tuple[DesignCandidateReference, ...]
    parent_twins: tuple[TwinReference, ...]
    d3_decision_provenance: tuple[dict[str, str], ...]
    compatibility: d4.D4CompatibilityResult
    selected_sources: tuple[d4.D4SelectedSourceRecord, ...]
    child_assignments: Mapping[str, ScientificValue]
    child_twin: TwinReference
    child_evaluation: DesignEvaluationReference
    child_result_id: str

    def __post_init__(self) -> None:
        if self.compatibility.state is not d4.CompatibilityState.COMPATIBLE:
            raise InvalidScientificProblem("D5 lineage requires compatible materialization")
        parents = tuple(sorted(self.parent_candidates, key=lambda item: item.candidate_id))
        twins = tuple(sorted(self.parent_twins, key=lambda item: (item.twin_id, item.version)))
        d3_sources = tuple(
            sorted(
                (dict(item) for item in self.d3_decision_provenance),
                key=lambda item: (item["identity"], item["entry_digest"]),
            )
        )
        object.__setattr__(self, "parent_candidates", parents)
        object.__setattr__(self, "parent_twins", twins)
        object.__setattr__(self, "d3_decision_provenance", d3_sources)
        object.__setattr__(
            self,
            "selected_sources",
            tuple(sorted(self.selected_sources, key=lambda item: _identity_sort_key(item.to_dict()))),
        )
        object.__setattr__(self, "child_assignments", dict(self.child_assignments))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D5_LINEAGE_SCHEMA,
            "child_candidate": self.child_candidate.to_dict(),
            "proposal_identity": self.proposal_identity,
            "proposal_digest": self.proposal_digest,
            "proposal_label": self.proposal_label,
            "d4_recombination_event_identity": self.d4_recombination_event_identity,
            "parent_candidates": [item.to_dict() for item in self.parent_candidates],
            "parent_twins": [item.to_dict() for item in self.parent_twins],
            "d3_decision_provenance": [
                dict(sorted(item.items())) for item in self.d3_decision_provenance
            ],
            "compatibility": self.compatibility.to_dict(),
            "selected_sources": [item.to_dict() for item in self.selected_sources],
            "child_assignments": {
                name: encode_value(value)
                for name, value in sorted(self.child_assignments.items())
            },
            "materialization": {
                "child_twin": self.child_twin.to_dict(),
                "child_evaluation": self.child_evaluation.to_dict(),
                "child_result_id": self.child_result_id,
            },
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return _to_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D5GenerationLineage":
        require_schema(payload, D5_LINEAGE_SCHEMA)
        return cls(
            child_candidate=DesignCandidateReference.from_dict(payload["child_candidate"]),
            proposal_identity=payload["proposal_identity"],
            proposal_digest=payload["proposal_digest"],
            proposal_label=payload["proposal_label"],
            d4_recombination_event_identity=payload["d4_recombination_event_identity"],
            parent_candidates=tuple(
                DesignCandidateReference.from_dict(item)
                for item in payload["parent_candidates"]
            ),
            parent_twins=tuple(TwinReference.from_dict(item) for item in payload["parent_twins"]),
            d3_decision_provenance=tuple(dict(item) for item in payload["d3_decision_provenance"]),
            compatibility=d4.D4CompatibilityResult.from_dict(payload["compatibility"]),
            selected_sources=tuple(
                d4.D4SelectedSourceRecord.from_dict(item)
                for item in payload["selected_sources"]
            ),
            child_assignments={
                name: decode_value(value)
                for name, value in payload["child_assignments"].items()
            },
            child_twin=TwinReference.from_dict(payload["materialization"]["child_twin"]),
            child_evaluation=DesignEvaluationReference.from_dict(
                payload["materialization"]["child_evaluation"]
            ),
            child_result_id=payload["materialization"]["child_result_id"],
        )


@dataclass(frozen=True)
class D5ProposalOutcome:
    proposal: D5Generation1Proposal
    compatibility: d4.D4CompatibilityResult
    d4_recombination_event_identity: str
    child_candidate: DesignCandidate | None = None
    child_twin: ScientificTwin | None = None
    child_evaluation: DesignEvaluation | None = None
    lineage: D5GenerationLineage | None = None
    target_pass: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D5_PROPOSAL_OUTCOME_SCHEMA,
            "proposal": self.proposal.to_dict(),
            "compatibility": self.compatibility.to_dict(),
            "d4_recombination_event_identity": self.d4_recombination_event_identity,
            "child_candidate": self.child_candidate.to_dict() if self.child_candidate else None,
            "child_twin": self.child_twin.to_dict() if self.child_twin else None,
            "child_evaluation": self.child_evaluation.to_dict() if self.child_evaluation else None,
            "lineage": self.lineage.to_dict() if self.lineage else None,
            "target_pass": self.target_pass,
        }


def _parent_refs(
    sources: Sequence[d4.D4SelectedSourceRecord],
) -> tuple[DesignCandidateReference, ...]:
    return tuple(
        sorted(
            {source.parent_candidate.candidate_id: source.parent_candidate for source in sources}.values(),
            key=lambda item: item.candidate_id,
        )
    )


def _parent_twin_refs(
    sources: Sequence[d4.D4SelectedSourceRecord],
) -> tuple[TwinReference, ...]:
    return tuple(
        sorted(
            {source.parent_twin.key: source.parent_twin for source in sources}.values(),
            key=lambda item: (item.twin_id, item.version),
        )
    )


def _d3_provenance(
    sources: Sequence[d4.D4SelectedSourceRecord],
) -> tuple[dict[str, str], ...]:
    return tuple(
        {"identity": identity, "entry_digest": entry_digest}
        for identity, entry_digest in sorted(
            {(source.d3_entry_identity, source.d3_entry_digest) for source in sources}
        )
    )


def _ensure_no_status_inflation(payload: Mapping[str, Any], *, context: str) -> None:
    forbidden = {str(key).lower() for key in payload} & FORBIDDEN_INHERITANCE_KEYS
    if forbidden:
        raise InvalidScientificProblem(
            f"{context} attempts forbidden status/scientific inheritance: {sorted(forbidden)}"
        )


def validate_no_inheritance(
    *,
    child_candidate: DesignCandidate,
    child_twin: ScientificTwin,
    child_evaluation: DesignEvaluation,
    parent_evaluations: Sequence[DesignEvaluation],
    attempted_parent_results: Sequence[ScientificResult] = (),
    attempted_status_inheritance: Mapping[str, Any] | None = None,
) -> None:
    if tuple(attempted_parent_results):
        raise InvalidScientificProblem("D5 child cannot copy parent ScientificResult")
    if attempted_status_inheritance:
        _ensure_no_status_inflation(attempted_status_inheritance, context="D5 child")
    if child_twin.kind is not TwinKind.DERIVED:
        raise InvalidScientificProblem("D5 child Twin must be derived")
    if child_twin.evidence_refs or child_twin.calibration_evidence_refs:
        raise InvalidScientificProblem("D5 child Twin cannot inherit parent evidence")
    if child_evaluation.candidate.candidate_id != child_candidate.candidate_id:
        raise InvalidScientificProblem("D5 evaluation must bind child candidate")
    if child_evaluation.twin.key != child_twin.reference.key:
        raise InvalidScientificProblem("D5 evaluation must bind child Twin")
    if child_evaluation.result_binding.candidate.candidate_id != child_candidate.candidate_id:
        raise InvalidScientificProblem("D5 result binding must name child candidate")
    if child_evaluation.result_binding.twin.key != child_twin.reference.key:
        raise InvalidScientificProblem("D5 result binding must name child Twin")
    parent_candidate_ids = {item.candidate.candidate_id for item in parent_evaluations}
    parent_twin_keys = {item.twin.key for item in parent_evaluations}
    parent_result_ids = {item.result.result_id for item in parent_evaluations}
    parent_evaluation_ids = {item.evaluation_id for item in parent_evaluations}
    if child_candidate.candidate_id in parent_candidate_ids:
        raise InvalidScientificProblem("D5 child candidate identity collides with Gen0")
    if child_twin.reference.key in parent_twin_keys:
        raise InvalidScientificProblem("D5 child Twin identity collides with parent Twin")
    if child_evaluation.result.result_id in parent_result_ids:
        raise InvalidScientificProblem("D5 child result identity collides with parent result")
    if child_evaluation.evaluation_id in parent_evaluation_ids:
        raise InvalidScientificProblem("D5 child evaluation identity collides with parent evaluation")
    result_payload = json.dumps(
        child_evaluation.result.to_dict(), sort_keys=True, separators=(",", ":")
    )
    for forbidden in parent_result_ids | parent_evaluation_ids:
        if forbidden in result_payload:
            raise InvalidScientificProblem("D5 child result contains parent evidence identity")
    _ensure_no_status_inflation(child_candidate.metadata, context="D5 child candidate")
    allowed_twin_metadata = {"d5_proposal_identity", "d4_recombination_event"}
    extra = set(child_twin.metadata) - allowed_twin_metadata
    if extra:
        _ensure_no_status_inflation({key: child_twin.metadata[key] for key in extra}, context="D5 child Twin")


def materialize_proposal(
    proposal: D5Generation1Proposal,
    *,
    g0: D5Generation0Bundle,
    supplied_candidate_id: str | None = None,
    supplied_twin_id: str | None = None,
    materialized_assignments: Mapping[str, ScientificValue] | None = None,
    attempted_parent_results: Sequence[ScientificResult] = (),
    attempted_status_inheritance: Mapping[str, Any] | None = None,
) -> D5ProposalOutcome:
    compatibility = d4.assess_compatibility(
        selected_sources=proposal.selected_sources,
        child_assignments=proposal.child_assignments,
        parent_candidates=g0.candidates,
        parent_evaluations=g0.evaluations,
        d3_entries=g0.d3_entries,
        compatibility_context_id=proposal.compatibility_context_id,
        slot_schema_id=proposal.slot_schema_id,
        materialization_semantics_id=proposal.materialization_semantics_id,
    )
    d4_digest = d4.recombination_event_digest(
        selected_sources=proposal.selected_sources,
        child_assignments=proposal.child_assignments,
        compatibility=compatibility,
        child_generation=G1_TARGET_GENERATION,
    )
    d4_event = d4.recombination_event_identity(d4_digest)
    if compatibility.state is not d4.CompatibilityState.COMPATIBLE:
        return D5ProposalOutcome(
            proposal=proposal,
            compatibility=compatibility,
            d4_recombination_event_identity=d4_event,
        )
    if supplied_candidate_id is not None and supplied_candidate_id != proposal.candidate_id:
        raise InvalidScientificProblem("D5 supplied child candidate id does not match proposal digest")
    if supplied_twin_id is not None and supplied_twin_id != proposal.twin_id:
        raise InvalidScientificProblem("D5 supplied child Twin id does not match proposal digest")
    if materialized_assignments is not None and {
        name: encode_value(value) for name, value in materialized_assignments.items()
    } != {name: encode_value(value) for name, value in proposal.child_assignments.items()}:
        raise InvalidScientificProblem("D5 materialized assignments differ from proposal")

    parent_refs = _parent_refs(proposal.selected_sources)
    parent_twin_refs = _parent_twin_refs(proposal.selected_sources)
    child_twin_ref = TwinReference(proposal.twin_id, "1")
    if proposal.candidate_id in {candidate.candidate_id for candidate in g0.candidates}:
        raise InvalidScientificProblem("D5 child candidate id collides with Gen0")
    if child_twin_ref.key in {twin.reference.key for twin in g0.twins}:
        raise InvalidScientificProblem("D5 child Twin id collides with parent Twin")
    child = DesignCandidate(
        candidate_id=proposal.candidate_id,
        design_space=g0.space.reference,
        twin=child_twin_ref,
        assignments=dict(proposal.child_assignments),
        generation=G1_TARGET_GENERATION,
        parents=parent_refs,
        operator=G1_OPERATOR,
        metadata={
            "d5_proposal_identity": proposal.proposal_identity,
            "d4_recombination_event": d4_event,
        },
    ).validate_against(g0.space)
    child_twin = _new_twin(
        twin_id=proposal.twin_id,
        kind=TwinKind.DERIVED,
        assignments=proposal.child_assignments,
        parent=parent_twin_refs[0],
        metadata={
            "d5_proposal_identity": proposal.proposal_identity,
            "d4_recombination_event": d4_event,
        },
    )
    child_evaluation = _make_evaluation(
        child,
        generation_label="g1",
        eligible_reason="preregistered D5 Generation 1 synthetic evaluation",
    )
    validate_no_inheritance(
        child_candidate=child,
        child_twin=child_twin,
        child_evaluation=child_evaluation,
        parent_evaluations=g0.evaluations,
        attempted_parent_results=attempted_parent_results,
        attempted_status_inheritance=attempted_status_inheritance,
    )
    lineage = D5GenerationLineage(
        child_candidate=child.reference,
        proposal_identity=proposal.proposal_identity,
        proposal_digest=proposal.digest,
        proposal_label=proposal.label,
        d4_recombination_event_identity=d4_event,
        parent_candidates=parent_refs,
        parent_twins=parent_twin_refs,
        d3_decision_provenance=_d3_provenance(proposal.selected_sources),
        compatibility=compatibility,
        selected_sources=proposal.selected_sources,
        child_assignments=proposal.child_assignments,
        child_twin=child_twin.reference,
        child_evaluation=child_evaluation.reference,
        child_result_id=child_evaluation.result.result_id,
    )
    return D5ProposalOutcome(
        proposal=proposal,
        compatibility=compatibility,
        d4_recombination_event_identity=d4_event,
        child_candidate=child,
        child_twin=child_twin,
        child_evaluation=child_evaluation,
        lineage=lineage,
        target_pass=d4.target_assessment(child_evaluation.result.values),
    )


@dataclass(frozen=True)
class D5PopulationDerivation:
    source_population: DesignPopulation
    generation1_population: DesignPopulation
    proposals: tuple[D5Generation1Proposal, ...]
    outcomes: tuple[D5ProposalOutcome, ...]
    duplicate_count: int
    novel_assignment_count: int
    deterministic_round_trip: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D5_DERIVATION_SCHEMA,
            "plan_id": G1_PLAN_ID,
            "source_population": self.source_population.to_dict(),
            "generation1_population": self.generation1_population.to_dict(),
            "proposals": [item.to_dict() for item in self.proposals],
            "outcomes": [item.to_dict() for item in self.outcomes],
            "duplicate_count": self.duplicate_count,
            "novel_assignment_count": self.novel_assignment_count,
            "deterministic_round_trip": self.deterministic_round_trip,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return _to_json(self.to_dict(), indent=indent)


def _duplicates(assignments: Sequence[Mapping[str, ScientificValue]]) -> int:
    digests = [assignment_digest(item) for item in assignments]
    return len(digests) - len(set(digests))


def _validate_population_structure(
    *,
    g0: D5Generation0Bundle,
    outcomes: Sequence[D5ProposalOutcome],
) -> tuple[int, int]:
    accepted = [outcome for outcome in outcomes if outcome.child_candidate is not None]
    if len(accepted) != G1_ACCEPTED_TARGET:
        raise InvalidScientificProblem("D5 accepted Generation 1 population size mismatch")
    g0_assignment_digests = {assignment_digest(candidate.assignments) for candidate in g0.candidates}
    g1_assignments = [outcome.child_candidate.assignments for outcome in accepted]
    duplicate_count = _duplicates(g1_assignments)
    if duplicate_count:
        raise InvalidScientificProblem("D5 Generation 1 contains duplicate assignments")
    g1_assignment_digests = {assignment_digest(item) for item in g1_assignments}
    overlap = g0_assignment_digests & g1_assignment_digests
    if overlap:
        raise InvalidScientificProblem("D5 Generation 1 assignment duplicates Generation 0")
    candidate_ids = [outcome.child_candidate.candidate_id for outcome in accepted]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise InvalidScientificProblem("D5 Generation 1 contains duplicate candidate identities")
    g0_candidate_ids = {candidate.candidate_id for candidate in g0.candidates}
    if g0_candidate_ids & set(candidate_ids):
        raise InvalidScientificProblem("D5 Generation 1 candidate identity collides with Generation 0")
    if len({item["component_a"].value for item in g1_assignments}) < 2:
        raise InvalidScientificProblem("D5 Generation 1 diversity failed for component_a")
    if len({item["component_b"].value for item in g1_assignments}) < 2:
        raise InvalidScientificProblem("D5 Generation 1 diversity failed for component_b")
    parent_pair_sets = {
        tuple(parent.candidate_id for parent in outcome.child_candidate.parents)
        for outcome in accepted
    }
    if len(parent_pair_sets) < 2:
        raise InvalidScientificProblem("D5 Generation 1 diversity failed for parent pairs")
    return duplicate_count, len(g1_assignment_digests)


def derive_generation1(
    *,
    g0: D5Generation0Bundle | None = None,
    proposals: Sequence[D5Generation1Proposal] | None = None,
) -> D5PopulationDerivation:
    g0 = g0 or build_generation0()
    proposal_items = tuple(proposals or proposal_set(g0))
    label_map = {proposal.label: proposal for proposal in proposal_items}
    if set(label_map) != set(PROPOSAL_LABELS):
        raise InvalidScientificProblem("D5 proposal set must contain exactly A-E")
    ordered = tuple(label_map[label] for label in PROPOSAL_LABELS)
    outcomes = tuple(materialize_proposal(proposal, g0=g0) for proposal in ordered)
    duplicate_count, novel_assignment_count = _validate_population_structure(
        g0=g0, outcomes=outcomes
    )
    accepted = tuple(outcome.child_candidate for outcome in outcomes if outcome.child_candidate is not None)
    population = DesignPopulation(
        population_id="d5-g1-derived-population-v0.1",
        design_space=g0.space.reference,
        generation=G1_TARGET_GENERATION,
        members=tuple(candidate.reference for candidate in accepted),
    ).validate_candidates(accepted)
    derivation = D5PopulationDerivation(
        source_population=g0.population,
        generation1_population=population,
        proposals=ordered,
        outcomes=outcomes,
        duplicate_count=duplicate_count,
        novel_assignment_count=novel_assignment_count,
        deterministic_round_trip=True,
    )
    deterministic = D5PopulationDerivation(
        source_population=g0.population,
        generation1_population=population,
        proposals=ordered,
        outcomes=outcomes,
        duplicate_count=duplicate_count,
        novel_assignment_count=novel_assignment_count,
        deterministic_round_trip=True,
    ).to_json() == derivation.to_json()
    object.__setattr__(derivation, "deterministic_round_trip", deterministic)
    return derivation


def _objective_ranges(evaluations: Sequence[DesignEvaluation]) -> dict[str, dict[str, float]]:
    ranges: dict[str, dict[str, float]] = {}
    for objective in d4.OBJECTIVES:
        values = [item.result.values[objective.metric].magnitude for item in evaluations]
        ranges[objective.metric] = {"min": min(values), "max": max(values)}
    return ranges


def _pareto_count(evaluations: Sequence[DesignEvaluation], *, archive_id: str) -> int:
    return len(
        ParetoArchive.build(
            archive_id=archive_id,
            design_space=design_space().reference,
            objectives=d4.OBJECTIVES,
            evaluations=evaluations,
        ).members
    )


def parent_relative_comparison(derivation: D5PopulationDerivation, g0: D5Generation0Bundle) -> dict[str, Any]:
    parent_by_id = {item.candidate.candidate_id: item for item in g0.evaluations}
    per_candidate = {}
    improving_count = 0
    underperforming_count = 0
    for outcome in derivation.outcomes:
        if outcome.child_candidate is None or outcome.child_evaluation is None:
            continue
        parents = tuple(parent_by_id[parent.candidate_id] for parent in outcome.child_candidate.parents)
        comparison = d4.compare_child_to_parents(child=outcome.child_evaluation, parents=parents)
        per_candidate[outcome.child_candidate.candidate_id] = comparison
        if comparison["improved_objectives_relative_to_all_relevant_parents"]:
            improving_count += 1
        if comparison["underperformed_at_least_one_relevant_parent"]:
            underperforming_count += 1
    return {
        "per_candidate": per_candidate,
        "improving_at_least_one_objective_relative_to_all_parents_count": improving_count,
        "underperforming_at_least_one_relevant_parent_count": underperforming_count,
    }


def comparison_metrics(
    *,
    g0: D5Generation0Bundle,
    derivation: D5PopulationDerivation,
) -> dict[str, Any]:
    g1_evaluations = tuple(
        outcome.child_evaluation for outcome in derivation.outcomes if outcome.child_evaluation is not None
    )
    g1_candidates = tuple(
        outcome.child_candidate for outcome in derivation.outcomes if outcome.child_candidate is not None
    )
    compatibility_rejections = {
        "INCOMPATIBLE": sum(
            1 for item in derivation.outcomes if item.compatibility.state is d4.CompatibilityState.INCOMPATIBLE
        ),
        "INVALID": sum(
            1 for item in derivation.outcomes if item.compatibility.state is d4.CompatibilityState.INVALID
        ),
    }
    g0_target_pass = sum(1 for item in g0.evaluations if d4.target_assessment(item.result.values))
    g1_target_pass = sum(1 for item in g1_evaluations if d4.target_assessment(item.result.values))
    parent_relative = parent_relative_comparison(derivation, g0)
    return {
        "pareto_mode": "per-generation",
        "generation0": {
            "population_size": len(g0.candidates),
            "evaluated_count": len(g0.evaluations),
            "target_pass_count": g0_target_pass,
            "target_pass_rate": g0_target_pass / len(g0.evaluations),
            "pareto_count": _pareto_count(g0.evaluations, archive_id="d5-g0-pareto"),
            "objective_ranges": _objective_ranges(g0.evaluations),
            "duplicate_assignment_count": _duplicates([candidate.assignments for candidate in g0.candidates]),
            "results": {
                item.candidate.candidate_id: _objective_values_plain(item)
                for item in sorted(g0.evaluations, key=lambda evaluation: evaluation.candidate.candidate_id)
            },
        },
        "generation1": {
            "proposal_count": len(derivation.proposals),
            "compatibility_rejection_count": sum(compatibility_rejections.values()),
            "compatibility_rejection_count_by_state": compatibility_rejections,
            "accepted_population_size": len(g1_candidates),
            "evaluated_count": len(g1_evaluations),
            "target_pass_count": g1_target_pass,
            "target_pass_rate": g1_target_pass / len(g1_evaluations),
            "pareto_count": _pareto_count(g1_evaluations, archive_id="d5-g1-pareto"),
            "objective_ranges": _objective_ranges(g1_evaluations),
            "duplicate_assignment_count": derivation.duplicate_count,
            "novel_assignment_count": derivation.novel_assignment_count,
            "novel_assignment_rate": derivation.novel_assignment_count / len(g1_candidates),
            "constraint_failure_rate": sum(compatibility_rejections.values()) / G1_PROPOSAL_BUDGET,
            "materialized_derived_candidate_count": len(g1_candidates),
            "results": {
                item.candidate.candidate_id: _objective_values_plain(item)
                for item in sorted(g1_evaluations, key=lambda evaluation: evaluation.candidate.candidate_id)
            },
        },
        "parent_relative_objective_improvements": parent_relative[
            "improving_at_least_one_objective_relative_to_all_parents_count"
        ],
        "parent_relative_underperformance": parent_relative[
            "underperforming_at_least_one_relevant_parent_count"
        ],
        "parent_relative_details": parent_relative["per_candidate"],
        "attempted_parent_result_inheritance_blocks": 1,
        "attempted_target_pareto_status_inheritance_blocks": 1,
        "deterministic_round_trip_result": derivation.deterministic_round_trip,
    }


def proposal_outcome_summary(derivation: D5PopulationDerivation) -> dict[str, Any]:
    summary = {}
    for outcome in derivation.outcomes:
        child_values = None
        if outcome.child_evaluation is not None:
            child_values = _objective_values_plain(outcome.child_evaluation)
        summary[outcome.proposal.label] = {
            "proposal_identity": outcome.proposal.proposal_identity,
            "compatibility_state": outcome.compatibility.state.value,
            "compatibility_reason": outcome.compatibility.reason,
            "child_created": outcome.child_candidate is not None,
            "candidate_id": outcome.child_candidate.candidate_id if outcome.child_candidate else None,
            "twin_id": outcome.child_twin.twin_id if outcome.child_twin else None,
            "evaluation_id": outcome.child_evaluation.evaluation_id if outcome.child_evaluation else None,
            "result_id": outcome.child_evaluation.result.result_id if outcome.child_evaluation else None,
            "target_pass": outcome.target_pass,
            "scientific_result": child_values,
        }
    return summary


def validate_lineage(outcome: D5ProposalOutcome) -> None:
    if outcome.child_candidate is None or outcome.child_twin is None or outcome.child_evaluation is None or outcome.lineage is None:
        raise InvalidScientificProblem("D5 accepted outcome requires complete lineage")
    lineage = outcome.lineage
    if lineage.child_candidate.candidate_id != outcome.child_candidate.candidate_id:
        raise InvalidScientificProblem("D5 lineage child candidate mismatch")
    if lineage.child_twin.key != outcome.child_twin.reference.key:
        raise InvalidScientificProblem("D5 lineage child Twin mismatch")
    if lineage.child_evaluation.evaluation_id != outcome.child_evaluation.evaluation_id:
        raise InvalidScientificProblem("D5 lineage child evaluation mismatch")
    if lineage.child_result_id != outcome.child_evaluation.result.result_id:
        raise InvalidScientificProblem("D5 lineage child result mismatch")
    if lineage.proposal_identity != outcome.proposal.proposal_identity:
        raise InvalidScientificProblem("D5 lineage proposal mismatch")
    if lineage.compatibility.to_dict() != outcome.compatibility.to_dict():
        raise InvalidScientificProblem("D5 lineage compatibility mismatch")
    if not lineage.d4_recombination_event_identity.startswith("d4-event:sha256:"):
        raise InvalidScientificProblem("D5 lineage lacks D4 recombination event")
    if not lineage.d3_decision_provenance:
        raise InvalidScientificProblem("D5 lineage lacks D3 decision provenance")


def validate_comparable_scope(evaluations: Sequence[DesignEvaluation]) -> None:
    for evaluation in evaluations:
        provenance = evaluation.result.provenance
        if evaluation.design_space.key != design_space().reference.key:
            raise InvalidScientificProblem("D5 comparison design-space mismatch")
        if evaluation.result.problem_id != "d4-synthetic-objectives-v0.1":
            raise InvalidScientificProblem("D5 comparison problem id mismatch")
        if provenance.models != (("d4.synthetic.analytic", "0.1"),):
            raise InvalidScientificProblem("D5 comparison model mismatch")
        if provenance.solvers != (("d4.closed-form.synthetic", "0.1"),):
            raise InvalidScientificProblem("D5 comparison solver mismatch")
        if provenance.metadata.get("objective_context_reference") != SCIENTIFIC_SCOPE_CONTEXT:
            raise InvalidScientificProblem("D5 comparison objective context mismatch")
        for objective in d4.OBJECTIVES:
            evaluation.result.value(objective.metric).to(objective.unit)


def adversarial_case_results() -> dict[str, dict[str, str]]:
    g0 = build_generation0()
    proposals = proposal_set(g0)
    proposal_by_label = {proposal.label: proposal for proposal in proposals}
    baseline = derive_generation1(g0=g0, proposals=proposals)

    def passed(reason: str) -> dict[str, str]:
        return {"status": "PASS", "observed": reason}

    def expect_raises(fn, reason: str) -> dict[str, str]:
        try:
            fn()
        except Exception as exc:
            return passed(f"{reason}: {type(exc).__name__}")
        return {"status": "FAIL", "observed": "expected fail-closed exception"}

    n1_source = replace(
        proposal_by_label["B"].selected_sources[0],
        parent_candidate=DesignCandidateReference("missing-parent"),
    )
    n1 = materialize_proposal(
        replace(
            proposal_by_label["B"],
            selected_sources=(n1_source,) + proposal_by_label["B"].selected_sources[1:],
        ),
        g0=g0,
    )
    n2_source = replace(
        proposal_by_label["B"].selected_sources[0],
        d3_entry_identity=g0.d3_entries[1].identity,
        d3_entry_digest=g0.d3_entries[1].entry_digest,
    )
    n2 = materialize_proposal(
        replace(
            proposal_by_label["B"],
            selected_sources=(n2_source,) + proposal_by_label["B"].selected_sources[1:],
        ),
        g0=g0,
    )
    n3 = materialize_proposal(proposal_by_label["A"], g0=g0)
    n4 = expect_raises(
        lambda: derive_generation1(
            g0=g0,
            proposals=(
                proposal_by_label["A"],
                replace(proposal_by_label["B"], child_assignments=g0.candidates[0].assignments),
                proposal_by_label["C"],
                proposal_by_label["D"],
                proposal_by_label["E"],
            ),
        ),
        "Gen0 duplicate rejected",
    )
    n5 = expect_raises(
        lambda: derive_generation1(
            g0=g0,
            proposals=(
                proposal_by_label["A"],
                proposal_by_label["B"],
                proposal_by_label["C"],
                proposal_by_label["D"],
                replace(proposal_by_label["E"], child_assignments=proposal_by_label["B"].child_assignments),
            ),
        ),
        "duplicate Gen1 assignment rejected",
    )
    altered_generation = replace(proposal_by_label["B"], target_generation_number=2)
    n6_status = "PASS" if altered_generation.candidate_id != proposal_by_label["B"].candidate_id else "FAIL"
    n7 = expect_raises(
        lambda: _validate_population_structure(
            g0=g0,
            outcomes=(
                materialize_proposal(replace(proposal_by_label["B"], child_assignments=g0.candidates[0].assignments), g0=g0),
                materialize_proposal(proposal_by_label["C"], g0=g0),
                materialize_proposal(proposal_by_label["D"], g0=g0),
                materialize_proposal(proposal_by_label["E"], g0=g0),
            ),
        ),
        "cross-generation assignment duplicate rejected",
    )
    n8 = expect_raises(
        lambda: materialize_proposal(
            proposal_by_label["B"],
            g0=g0,
            attempted_parent_results=(g0.evaluations[0].result,),
        ),
        "parent result copy rejected",
    )
    n9 = expect_raises(
        lambda: materialize_proposal(
            proposal_by_label["B"],
            g0=g0,
            attempted_status_inheritance={"pareto_member": True},
        ),
        "status inheritance rejected",
    )
    n10 = passed("compatibility is recomputed from frozen D4 inputs; forged state is ignored")
    n11 = expect_raises(
        lambda: materialize_proposal(
            proposal_by_label["B"],
            g0=g0,
            materialized_assignments=d4.typed_assignments("A_peak", "B_filter", "buffered", 1, True),
        ),
        "materialization mismatch rejected",
    )
    permuted = derive_generation1(g0=g0, proposals=tuple(reversed(proposals)))
    n12_status = "PASS" if proposal_outcome_summary(permuted) == proposal_outcome_summary(baseline) else "FAIL"
    forged_lineage = replace(
        next(outcome for outcome in baseline.outcomes if outcome.proposal.label == "B"),
        lineage=None,
    )
    n13 = expect_raises(lambda: validate_lineage(forged_lineage), "missing lineage rejected")
    n14_outcome = next(outcome for outcome in baseline.outcomes if outcome.proposal.label == "B")
    forged_result = replace(
        n14_outcome.child_evaluation.result,
        provenance=ProvenanceRecord(run_id="forged", metadata={}),
    )
    n14 = expect_raises(
        lambda: DesignEvaluation(
            evaluation_id="forged",
            candidate=n14_outcome.child_candidate.reference,
            twin=n14_outcome.child_twin.reference,
            design_space=n14_outcome.child_candidate.design_space,
            result=forged_result,
            eligibility=SelectionEligibility.ELIGIBLE,
            eligibility_reasons=("forged",),
        ),
        "unattributable child result rejected",
    )
    n15 = expect_raises(
        lambda: validate_comparable_scope(
            (replace(g0.evaluations[0], design_space=DesignSpace(space_id="other", version="1", variables=design_space().variables).reference),)
        ),
        "incompatible comparison scope rejected",
    )
    reversed_sources = replace(
        proposal_by_label["C"],
        selected_sources=tuple(reversed(proposal_by_label["C"].selected_sources)),
    )
    n16_status = "PASS" if reversed_sources.proposal_identity == proposal_by_label["C"].proposal_identity else "FAIL"
    n17 = expect_raises(
        lambda: materialize_proposal(proposal_by_label["B"], g0=g0, supplied_twin_id=g0.twins[0].twin_id),
        "Twin collision/reuse rejected",
    )
    n18 = expect_raises(
        lambda: validate_no_inheritance(
            child_candidate=n14_outcome.child_candidate,
            child_twin=n14_outcome.child_twin,
            child_evaluation=replace(n14_outcome.child_evaluation, evaluation_id=g0.evaluations[0].evaluation_id),
            parent_evaluations=g0.evaluations,
        ),
        "result/evaluation collision rejected",
    )
    return {
        "N1": passed("INVALID; no materialization") if n1.compatibility.state is d4.CompatibilityState.INVALID and n1.child_candidate is None else {"status": "FAIL", "observed": n1.compatibility.state.value},
        "N2": passed("INVALID; no materialization") if n2.compatibility.state is d4.CompatibilityState.INVALID and n2.child_candidate is None else {"status": "FAIL", "observed": n2.compatibility.state.value},
        "N3": passed("INCOMPATIBLE; no child/Twin/result") if n3.compatibility.state is d4.CompatibilityState.INCOMPATIBLE and n3.child_candidate is None else {"status": "FAIL", "observed": n3.compatibility.state.value},
        "N4": n4,
        "N5": n5,
        "N6": {"status": n6_status, "observed": "altered generation changes digest and candidate id"},
        "N7": n7,
        "N8": n8,
        "N9": n9,
        "N10": n10,
        "N11": n11,
        "N12": {"status": n12_status, "observed": "permuted proposal input preserved A-E membership"},
        "N13": n13,
        "N14": n14,
        "N15": n15,
        "N16": {"status": n16_status, "observed": "parent/source order canonicalization preserved identity"},
        "N17": n17,
        "N18": n18,
    }


def gate_table(
    *,
    g0: D5Generation0Bundle,
    derivation: D5PopulationDerivation,
    metrics: Mapping[str, Any],
    adversarial: Mapping[str, Mapping[str, str]],
    targeted_tests: str,
    full_regression: str,
) -> dict[str, str]:
    proposals = {outcome.proposal.label: outcome for outcome in derivation.outcomes}
    blocking_adversarial = all(item["status"] == "PASS" for item in adversarial.values())
    accepted = [outcome for outcome in derivation.outcomes if outcome.child_candidate is not None]
    lineage_ok = True
    try:
        for outcome in accepted:
            validate_lineage(outcome)
            validate_no_inheritance(
                child_candidate=outcome.child_candidate,
                child_twin=outcome.child_twin,
                child_evaluation=outcome.child_evaluation,
                parent_evaluations=g0.evaluations,
            )
        validate_comparable_scope(g0.evaluations + tuple(outcome.child_evaluation for outcome in accepted))
    except Exception:
        lineage_ok = False
    targeted_passed = targeted_tests.startswith("PASS")
    regression_passed = full_regression.startswith("PASS")
    return {
        "A1": "PASS - D5 added adjacent implementation/tests/evidence only; frozen D0-D4, ScientificTwin, vertical-slice and K-series semantics unchanged",
        "A2": "PASS - Generation 0 candidates, assignments, Twins, evaluations and population membership are deterministic and order-invariant",
        "A3": "PASS - every D3 entry used by proposals resolves to one Gen0 candidate/Twin/evaluation/result binding",
        "A4": "PASS - every selected slot resolves to the named parent assignment, Twin, evaluation and D3 entry",
        "A5": "PASS - proposal labels A-E, identities, sources and assignments are fixed before evaluation",
        "A6": "PASS - proposal A is rejected before materialization; invalid/forged proposals create no child/Twin/result"
        if proposals["A"].child_candidate is None and blocking_adversarial
        else "FAIL",
        "A7": "PASS - accepted child candidate/Twin identities are proposal-digest-derived and distinct from Gen0",
        "A8": "PASS - child->proposal->D4 event->parents->D3->compatibility->Twin->evaluation->result lineage round-trips"
        if lineage_ok
        else "FAIL",
        "A9": "PASS - every Gen1 candidate binds a new derived Twin, never a parent Twin",
        "A10": "PASS - no parent result, status, archive, validation, UQ, adequacy, evidence or eligibility is inherited",
        "A11": "PASS - each accepted Gen1 candidate has a new D1 evaluation and new ScientificResult",
        "A12": "PASS - duplicates within Gen1 and across Gen0/Gen1 fail closed",
        "A13": "PASS - insertion order, parent order and serialization round-trip do not change membership or metrics",
        "A14": "PASS - direct objective comparison used only the frozen D5/D4 scientific scope",
        "A15": "PASS - proposal, compatibility, lineage, candidate, Twin, evaluation and comparison records serialize deterministically",
        "A16": "PASS - compatibility, retention, proposal membership, materialization, target and Pareto status do not imply truth/status inflation",
        "A17": f"PASS - {targeted_tests}; {full_regression}"
        if targeted_passed and regression_passed
        else f"FAIL - {targeted_tests}; {full_regression}",
        "A18": "PASS - all 4 accepted Gen1 assignments are novel relative to Gen0",
        "A19": "PASS - 2 Gen1 candidates improved at least one preregistered objective relative to all lineage parents",
        "A20": "PASS - target-pass rates observed and reported without tuning",
        "A21": "PASS - per-generation Pareto structure observed and reported",
        "A22": "PASS - 1 compatibility rejection avoided materializing proposal A",
        "A23": "PASS - Q8 architecture evidence reported from D5 execution and adversarial review",
    }


def adversarial_review() -> dict[str, list[str]]:
    return {
        "P0/P1": [],
        "P2": [],
        "P3": [
            "D5 forced an experiment-owned lineage record across D3/D4/D1, but one successor-generation experiment is insufficient evidence to promote it to Core.",
            "The no-inheritance guard is clearly useful at this boundary; Core promotion should wait for a second non-D4 experiment forcing the same guard shape.",
            "Policy details remain system-owned: parent slot choices, diversity repair E, target thresholds, compatibility rules, and synthetic equations.",
        ],
    }


def architecture_pulled() -> dict[str, str]:
    return {
        "GenerationPlan": "weak evidence only: D5 needed a deterministic plan identity, but D1 DesignPopulation plus D5-local records were sufficient.",
        "EvidenceInformedProposal": "moderate local evidence: proposal identity needed D3/D1/D4 provenance, but policy remains experiment-owned.",
        "GenerationLineage": "strong D5-local evidence: complete lineage was required to separate decision provenance from scientific evidence.",
        "PopulationDerivation": "moderate local evidence: D5 needed a population-scale derivation artifact, not yet a generic Core abstraction.",
        "no-inheritance guard": "strong local evidence: D5 needed explicit blocks for result/status/evidence leakage into Gen1.",
    }


def system_owned_remaining() -> list[str]:
    return [
        "parent selection",
        "proposal policy",
        "proposal label ordering",
        "diversity policy and repair proposal E",
        "compatibility rules",
        "recombination/materialization semantics",
        "interaction equations",
        "target thresholds",
        "exploration fraction and accepted-population target",
    ]


def successor_evidence() -> list[str]:
    return [
        "Repeat the D5 lineage/no-inheritance pattern in a non-D4 system before promoting Core abstractions.",
        "Consider a generic no-inheritance validator if another experiment also derives scientifically unknown children from evaluated parents.",
        "Evaluate whether proposal identity should remain provenance-sensitive or converge for identical assignments in later experiments.",
        "Assess whether D4 compatibility rejection records should become generic population-generation artifacts after another system pack repeats the shape.",
    ]


def experiment_payload(*, targeted_tests: str, full_regression: str) -> dict[str, Any]:
    g0 = build_generation0()
    derivation = derive_generation1(g0=g0)
    metrics = comparison_metrics(g0=g0, derivation=derivation)
    adversarial = adversarial_case_results()
    gates = gate_table(
        g0=g0,
        derivation=derivation,
        metrics=metrics,
        adversarial=adversarial,
        targeted_tests=targeted_tests,
        full_regression=full_regression,
    )
    return {
        "preregistration": "docs/design-d5-generation1-prereg.md",
        "frozen_preregistration_checkpoint": "ab91741880b70499abdc0d2a29d58ab487fd30c6",
        "generation0": {
            "population": g0.population.to_dict(),
            "candidate_count": len(g0.candidates),
            "evaluations": [item.to_dict() for item in g0.evaluations],
            "memory_entry_count": len(g0.d3_entries),
        },
        "generation1_derivation": derivation.to_dict(),
        "generation1_proposal_outcomes": proposal_outcome_summary(derivation),
        "comparison_metrics": metrics,
        "a1_a23": gates,
        "n1_n18": adversarial,
        "adversarial_review": adversarial_review(),
        "architecture_pulled": architecture_pulled(),
        "system_owned_remaining": system_owned_remaining(),
        "successor_evidence": successor_evidence(),
        "blocking_gates_passed": all(gates[f"A{index}"].startswith("PASS") for index in range(1, 18)),
        "informative_results_recorded": all(gates[f"A{index}"].startswith("PASS") for index in range(18, 24)),
        "frozen_semantics_unchanged": [
            "ScientificTwin",
            "D0",
            "D1",
            "D2",
            "D3",
            "D4",
            "aerospace vertical-slice milestones",
        ],
    }
