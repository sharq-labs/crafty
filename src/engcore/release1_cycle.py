"""Bounded Release 1 Lab-to-Mind reference-cycle integration.

This module is release-internal glue.  It deliberately does not promote the
frozen D7 policy, scope, decision, Study, or checkpoint records into Core.  A
caller must explicitly supply the read-only D7 reference module path.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence

from ._version import __version__
from .design.candidate import DesignCandidate, DesignCandidateReference
from .design.evaluation import (
    DesignEvaluation,
    ResultBinding,
    SelectionEligibility,
)
from .design.memory import (
    DesignMemoryEntry,
    DesignMemoryRecord,
    DesignMemoryScope,
    verify_layer_a_attribution,
)
from .release1_api import PUBLIC_V1_MANIFEST
from .scientific.errors import InvalidScientificProblem
from .scientific.results.result import ScientificResult
from .scientific.twins.definition import ScientificTwin, TwinReference


RELEASE1_CYCLE_SCHEMA = "engcore.release1_cycle/1"
RELEASE1_STUDY_SCHEMA = "engcore.release1_study_request/1"
RELEASE1_LAB_OBSERVATION_SCHEMA = "engcore.release1_lab_observation/1"
RELEASE1_MIND_DECISION_SCHEMA = "engcore.release1_mind_decision/1"
RELEASE1_CYCLE_RESULT_SCHEMA = "engcore.release1_cycle_result/1"
RELEASE1_REFERENCE_POLICY = "d7-information-per-compute-lexicographic@0.1"
RELEASE1_REFERENCE_SYSTEM = "d4-synthetic-objectives-v0.1"
RELEASE1_REFERENCE_MODEL = ("d4.synthetic.analytic", "0.1")
RELEASE1_REFERENCE_SOLVER = ("d4.closed-form.synthetic", "0.1")
RELEASE1_REFERENCE_EXECUTION = "d7.d4-closed-form-integrated-execution@0.1"
RELEASE1_INITIAL_CANDIDATE = "d4-parent-c"

_DEPENDENCIES = ("numpy", "scipy", "scikit-learn", "pint")
_REFERENCE_MODULE_NAME = "_engcore_release1_d7_reference"


def _canonical_bytes(payload: Any) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidScientificProblem(
            "Release 1 cycle payload is not canonical JSON"
        ) from exc


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _require_exact_keys(
    payload: Mapping[str, Any], expected: set[str], context: str
) -> None:
    if set(payload) != expected:
        raise InvalidScientificProblem(f"{context} fields do not match schema")


def _pair(value: Sequence[Any], context: str) -> tuple[str, str]:
    pair = tuple(str(item).strip() for item in value)
    if len(pair) != 2 or any(not item for item in pair):
        raise InvalidScientificProblem(f"{context} must be an identity pair")
    return pair[0], pair[1]


def _identity_text(value: Any, context: str) -> str:
    text = str(value).strip()
    if not text:
        raise InvalidScientificProblem(f"{context} must be non-empty")
    return text


def _reference_key(twin: ScientificTwin) -> str:
    return f"{twin.twin_id}@{twin.version}"


def _manifest_identity() -> str:
    return hashlib.sha256(_canonical_bytes(PUBLIC_V1_MANIFEST)).hexdigest()


def _environment_payload(release_commit: str) -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for name in _DEPENDENCIES:
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise InvalidScientificProblem(
                f"Release 1 dependency provenance is missing {name}"
            ) from exc
    return {
        "schema": "engcore.release1_environment/1",
        "distribution": {
            "name": "engineering-ai-core",
            "version": importlib.metadata.version("engineering-ai-core"),
        },
        "release_commit": _identity_text(release_commit, "release commit"),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "full_version": sys.version,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
        },
        "dependencies": dependencies,
    }


def _load_reference_module(reference_path: Path) -> tuple[ModuleType, str]:
    path = reference_path.resolve(strict=True)
    if path.name != "loop.py" or path.parent.name != "design_d7":
        raise InvalidScientificProblem(
            "Release 1 requires the explicit frozen design_d7/loop.py reference"
        )
    source = path.read_bytes()
    source_digest = hashlib.sha256(source).hexdigest()
    spec = importlib.util.spec_from_file_location(_REFERENCE_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise InvalidScientificProblem("Release 1 D7 reference cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(_REFERENCE_MODULE_NAME)
    sys.modules[_REFERENCE_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if previous is None:
            sys.modules.pop(_REFERENCE_MODULE_NAME, None)
        else:
            sys.modules[_REFERENCE_MODULE_NAME] = previous
        raise
    return module, source_digest


def _discard_reference_module() -> None:
    sys.modules.pop(_REFERENCE_MODULE_NAME, None)


@dataclass(frozen=True)
class Release1StudyRequest:
    """Release-internal typed Mind-to-Lab execution aggregate."""

    role: str
    candidate: DesignCandidate
    twin: ScientificTwin
    problem_id: str
    model_identity: tuple[str, str]
    solver_identity: tuple[str, str]
    physics_scope_identity: str
    execution_semantics_identity: str
    source_study_identity: str | None = None
    decision_identity: str | None = None
    selected_option_identity: str | None = None
    study_identity: str = field(init=False)

    def __post_init__(self) -> None:
        role = _identity_text(self.role, "Release 1 Study role")
        if role not in {"INITIAL_REFERENCE", "SELECTED_REFERENCE"}:
            raise InvalidScientificProblem("Release 1 Study role is unsupported")
        if not isinstance(self.candidate, DesignCandidate):
            raise InvalidScientificProblem("Release 1 Study requires DesignCandidate")
        if not isinstance(self.twin, ScientificTwin):
            raise InvalidScientificProblem("Release 1 Study requires ScientificTwin")
        if self.candidate.twin.key != self.twin.reference.key:
            raise InvalidScientificProblem("Release 1 Study Candidate/Twin mismatch")
        if self.candidate.design_space.key != ("d4-domain-neutral-synthetic", "0.1"):
            raise InvalidScientificProblem("Release 1 Study design-space mismatch")
        models = tuple(model.key for model in self.twin.models)
        model_identity = _pair(self.model_identity, "Release 1 Study model")
        solver_identity = _pair(self.solver_identity, "Release 1 Study solver")
        if model_identity not in models:
            raise InvalidScientificProblem("Release 1 Study Twin/model mismatch")
        if role == "INITIAL_REFERENCE" and self.candidate.generation != 0:
            raise InvalidScientificProblem("Release 1 initial Study must be Generation 0")
        if role == "SELECTED_REFERENCE" and self.candidate.generation != 1:
            raise InvalidScientificProblem(
                "Release 1 selected Study must remain Generation 1"
            )
        decision_fields = (
            self.source_study_identity,
            self.decision_identity,
            self.selected_option_identity,
        )
        if role == "INITIAL_REFERENCE" and any(item is not None for item in decision_fields):
            raise InvalidScientificProblem(
                "Release 1 initial Study cannot carry decision provenance"
            )
        if role == "SELECTED_REFERENCE" and any(item is None for item in decision_fields):
            raise InvalidScientificProblem(
                "Release 1 selected Study requires complete decision provenance"
            )
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "problem_id", _identity_text(self.problem_id, "problem"))
        object.__setattr__(self, "model_identity", model_identity)
        object.__setattr__(self, "solver_identity", solver_identity)
        object.__setattr__(
            self,
            "physics_scope_identity",
            _identity_text(self.physics_scope_identity, "physics scope"),
        )
        object.__setattr__(
            self,
            "execution_semantics_identity",
            _identity_text(self.execution_semantics_identity, "execution semantics"),
        )
        for name in decision_fields:
            if name is not None:
                _identity_text(name, "decision provenance")
        object.__setattr__(
            self, "study_identity", f"release1-study:sha256:{_digest(self.identity_payload())}"
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": RELEASE1_STUDY_SCHEMA,
            "role": self.role,
            "candidate": self.candidate.to_dict(),
            "twin": self.twin.to_dict(),
            "problem_id": self.problem_id,
            "model_identity": list(self.model_identity),
            "solver_identity": list(self.solver_identity),
            "physics_scope_identity": self.physics_scope_identity,
            "execution_semantics_identity": self.execution_semantics_identity,
            "source_study_identity": self.source_study_identity,
            "decision_identity": self.decision_identity,
            "selected_option_identity": self.selected_option_identity,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "study_identity": self.study_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Release1StudyRequest":
        _require_exact_keys(
            payload,
            {
                "schema", "role", "candidate", "twin", "problem_id",
                "model_identity", "solver_identity", "physics_scope_identity",
                "execution_semantics_identity", "source_study_identity",
                "decision_identity", "selected_option_identity", "study_identity",
            },
            "Release 1 Study",
        )
        if payload["schema"] != RELEASE1_STUDY_SCHEMA:
            raise InvalidScientificProblem("Release 1 Study schema mismatch")
        rebuilt = cls(
            role=payload["role"],
            candidate=DesignCandidate.from_dict(payload["candidate"]),
            twin=ScientificTwin.from_dict(payload["twin"]),
            problem_id=payload["problem_id"],
            model_identity=_pair(payload["model_identity"], "model"),
            solver_identity=_pair(payload["solver_identity"], "solver"),
            physics_scope_identity=payload["physics_scope_identity"],
            execution_semantics_identity=payload["execution_semantics_identity"],
            source_study_identity=payload["source_study_identity"],
            decision_identity=payload["decision_identity"],
            selected_option_identity=payload["selected_option_identity"],
        )
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("Release 1 Study identity mismatch")
        return rebuilt


@dataclass(frozen=True)
class Release1LabObservation:
    """Exact eligible and attributable Lab-to-Mind handoff."""

    study: Release1StudyRequest
    evaluation: DesignEvaluation
    result_binding: ResultBinding
    memory_scope: DesignMemoryScope
    memory_entry: DesignMemoryEntry

    def __post_init__(self) -> None:
        if not isinstance(self.study, Release1StudyRequest):
            raise InvalidScientificProblem("Release 1 Lab observation requires Study")
        if not isinstance(self.evaluation, DesignEvaluation):
            raise InvalidScientificProblem(
                "Release 1 Lab observation requires DesignEvaluation"
            )
        self.evaluation.validate_candidate(self.study.candidate)
        if self.evaluation.eligibility is not SelectionEligibility.ELIGIBLE:
            raise InvalidScientificProblem(
                "Release 1 Mind accepts only explicitly eligible evaluations"
            )
        if self.study.twin.reference.key != self.evaluation.twin.key:
            raise InvalidScientificProblem("Release 1 Lab observation Twin mismatch")
        if self.result_binding.to_dict() != self.evaluation.result_binding.to_dict():
            raise InvalidScientificProblem("Release 1 Lab ResultBinding mismatch")
        result = self.evaluation.result
        if result.problem_id != self.study.problem_id:
            raise InvalidScientificProblem("Release 1 Lab Study/problem mismatch")
        if tuple(result.models) != (self.study.model_identity,):
            raise InvalidScientificProblem("Release 1 Lab Study/model mismatch")
        if result.solver is None or result.solver.key != self.study.solver_identity:
            raise InvalidScientificProblem("Release 1 Lab Study/solver mismatch")
        if result.provenance.models != (self.study.model_identity,):
            raise InvalidScientificProblem("Release 1 Lab provenance model mismatch")
        if result.provenance.solvers != (self.study.solver_identity,):
            raise InvalidScientificProblem("Release 1 Lab provenance solver mismatch")
        metadata = result.provenance.metadata
        if metadata.get("d7_physics_scope_identity") != self.study.physics_scope_identity:
            raise InvalidScientificProblem("Release 1 Lab physics-scope mismatch")
        if (
            metadata.get("d7_execution_semantics_identity")
            != self.study.execution_semantics_identity
        ):
            raise InvalidScientificProblem("Release 1 Lab execution-semantics mismatch")
        if self.study.role == "SELECTED_REFERENCE":
            if metadata.get("d7_study_identity") != self.study.source_study_identity:
                raise InvalidScientificProblem("Release 1 selected Study mismatch")
            if metadata.get("d7_decision_identity") != self.study.decision_identity:
                raise InvalidScientificProblem("Release 1 selected decision mismatch")
            if metadata.get("d7_option_identity") != self.study.selected_option_identity:
                raise InvalidScientificProblem("Release 1 selected option mismatch")
            if metadata.get("decision_provenance_only") is not True:
                raise InvalidScientificProblem(
                    "Release 1 decision provenance is not marked non-evidence"
                )
        expected_entry = DesignMemoryEntry.from_evaluation(
            scope=self.memory_scope,
            candidate=self.study.candidate,
            evaluation=self.evaluation,
        )
        if self.memory_entry.to_dict() != expected_entry.to_dict():
            raise InvalidScientificProblem(
                "Release 1 Lab observation has unrelated memory entry"
            )
        non_evidence = {
            item
            for item in (
                self.study.decision_identity,
                self.study.selected_option_identity,
                self.study.source_study_identity,
            )
            if item is not None
        }
        declared_evidence = set(self.study.twin.evidence_refs) | set(
            self.study.twin.calibration_evidence_refs
        )
        if declared_evidence & non_evidence or any(
            "prediction" in item.lower() or "decision" in item.lower()
            for item in declared_evidence
        ):
            raise InvalidScientificProblem(
                "Release 1 prediction/decision provenance cannot be scientific evidence"
            )

    @property
    def candidate(self) -> DesignCandidate:
        return self.study.candidate

    @property
    def twin(self) -> ScientificTwin:
        return self.study.twin

    @property
    def result(self) -> ScientificResult:
        return self.evaluation.result

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RELEASE1_LAB_OBSERVATION_SCHEMA,
            "study": self.study.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "result_binding": self.result_binding.to_dict(),
            "memory_scope": self.memory_scope.to_dict(),
            "memory_entry": self.memory_entry.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Release1LabObservation":
        _require_exact_keys(
            payload,
            {
                "schema", "study", "evaluation", "result_binding",
                "memory_scope", "memory_entry",
            },
            "Release 1 Lab observation",
        )
        if payload["schema"] != RELEASE1_LAB_OBSERVATION_SCHEMA:
            raise InvalidScientificProblem("Release 1 Lab observation schema mismatch")
        return cls(
            study=Release1StudyRequest.from_dict(payload["study"]),
            evaluation=DesignEvaluation.from_dict(payload["evaluation"]),
            result_binding=ResultBinding.from_dict(payload["result_binding"]),
            memory_scope=DesignMemoryScope.from_dict(payload["memory_scope"]),
            memory_entry=DesignMemoryEntry.from_dict(payload["memory_entry"]),
        )


@dataclass(frozen=True)
class Release1MindDecision:
    """Reference-only decision summary; it is provenance, never evidence."""

    policy_identity: str
    decision_identity: str
    selected_option_identity: str
    selected_option_label: str
    source_evidence: tuple[Mapping[str, str], ...]
    selected_study: Release1StudyRequest

    def __post_init__(self) -> None:
        if self.policy_identity != RELEASE1_REFERENCE_POLICY:
            raise InvalidScientificProblem("Release 1 Mind policy mismatch")
        if self.selected_option_label != "B":
            raise InvalidScientificProblem("Release 1 Mind selected option mismatch")
        if self.selected_study.role != "SELECTED_REFERENCE":
            raise InvalidScientificProblem("Release 1 Mind did not produce selected Study")
        if self.selected_study.decision_identity != self.decision_identity:
            raise InvalidScientificProblem("Release 1 Mind decision/Study mismatch")
        if self.selected_study.selected_option_identity != self.selected_option_identity:
            raise InvalidScientificProblem("Release 1 Mind option/Study mismatch")
        sources = tuple(
            sorted(
                (dict(item) for item in self.source_evidence),
                key=lambda item: item.get("binding_identity", ""),
            )
        )
        expected_keys = {
            "binding_identity", "binding_digest", "candidate_id",
            "evaluation_id", "result_id",
        }
        if not sources:
            raise InvalidScientificProblem("Release 1 Mind requires attributable evidence")
        for source in sources:
            if set(source) != expected_keys or any(not str(value).strip() for value in source.values()):
                raise InvalidScientificProblem(
                    "Release 1 Mind evidence reference is incomplete"
                )
        if len({item["binding_identity"] for item in sources}) != len(sources):
            raise InvalidScientificProblem("Release 1 Mind evidence is duplicated")
        object.__setattr__(self, "source_evidence", sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RELEASE1_MIND_DECISION_SCHEMA,
            "policy_identity": self.policy_identity,
            "decision_identity": self.decision_identity,
            "selected_option_identity": self.selected_option_identity,
            "selected_option_label": self.selected_option_label,
            "source_evidence": [dict(item) for item in self.source_evidence],
            "selected_study": self.selected_study.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Release1MindDecision":
        _require_exact_keys(
            payload,
            {
                "schema", "policy_identity", "decision_identity",
                "selected_option_identity", "selected_option_label",
                "source_evidence", "selected_study",
            },
            "Release 1 Mind decision",
        )
        if payload["schema"] != RELEASE1_MIND_DECISION_SCHEMA:
            raise InvalidScientificProblem("Release 1 Mind decision schema mismatch")
        return cls(
            policy_identity=payload["policy_identity"],
            decision_identity=payload["decision_identity"],
            selected_option_identity=payload["selected_option_identity"],
            selected_option_label=payload["selected_option_label"],
            source_evidence=tuple(dict(item) for item in payload["source_evidence"]),
            selected_study=Release1StudyRequest.from_dict(payload["selected_study"]),
        )


@dataclass(frozen=True)
class Release1CycleResult:
    initial_observation: Release1LabObservation
    mind_decision: Release1MindDecision
    selected_observation: Release1LabObservation
    final_memory: DesignMemoryRecord
    next_cycle_source_identity: str
    generation_2_executed: bool = False
    cycle_identity: str = field(init=False)

    def __post_init__(self) -> None:
        if self.generation_2_executed is not False:
            raise InvalidScientificProblem("Release 1 must stop before Generation 2")
        if self.initial_observation.study.role != "INITIAL_REFERENCE":
            raise InvalidScientificProblem("Release 1 cycle initial handoff mismatch")
        if self.mind_decision.selected_study.to_dict() != self.selected_observation.study.to_dict():
            raise InvalidScientificProblem("Release 1 selected Study substitution")
        if self.selected_observation.candidate.generation != 1:
            raise InvalidScientificProblem("Release 1 selected candidate is not Generation 1")
        entries = self.final_memory.layer_a.entry_by_identity()
        returned = self.selected_observation.memory_entry
        if returned.identity not in entries or entries[returned.identity].to_dict() != returned.to_dict():
            raise InvalidScientificProblem("Release 1 final memory lost returned evidence")
        if self.final_memory.layer_a.scope.to_dict() != self.selected_observation.memory_scope.to_dict():
            raise InvalidScientificProblem("Release 1 final memory scope mismatch")
        _identity_text(self.next_cycle_source_identity, "next-cycle source")
        object.__setattr__(
            self,
            "cycle_identity",
            f"release1-cycle:sha256:{_digest(self.identity_payload())}",
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": RELEASE1_CYCLE_RESULT_SCHEMA,
            "initial_observation": self.initial_observation.to_dict(),
            "mind_decision": self.mind_decision.to_dict(),
            "selected_observation": self.selected_observation.to_dict(),
            "final_memory": self.final_memory.to_dict(),
            "next_cycle_source_identity": self.next_cycle_source_identity,
            "generation_2_executed": self.generation_2_executed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "cycle_identity": self.cycle_identity}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Release1CycleResult":
        _require_exact_keys(
            payload,
            {
                "schema", "initial_observation", "mind_decision",
                "selected_observation", "final_memory",
                "next_cycle_source_identity", "generation_2_executed",
                "cycle_identity",
            },
            "Release 1 cycle result",
        )
        if payload["schema"] != RELEASE1_CYCLE_RESULT_SCHEMA:
            raise InvalidScientificProblem("Release 1 cycle result schema mismatch")
        rebuilt = cls(
            initial_observation=Release1LabObservation.from_dict(
                payload["initial_observation"]
            ),
            mind_decision=Release1MindDecision.from_dict(payload["mind_decision"]),
            selected_observation=Release1LabObservation.from_dict(
                payload["selected_observation"]
            ),
            final_memory=DesignMemoryRecord.from_dict(payload["final_memory"]),
            next_cycle_source_identity=payload["next_cycle_source_identity"],
            generation_2_executed=payload["generation_2_executed"],
        )
        if rebuilt.to_dict() != dict(payload):
            raise InvalidScientificProblem("Release 1 cycle identity mismatch")
        return rebuilt


def _study_request(
    *,
    role: str,
    candidate: DesignCandidate,
    twin: ScientificTwin,
    state: Any,
    selected: Any | None = None,
) -> Release1StudyRequest:
    kwargs: dict[str, Any] = {}
    if selected is not None:
        kwargs = {
            "source_study_identity": selected.study.study_identity,
            "decision_identity": state.decision.decision_identity,
            "selected_option_identity": state.decision.selected_option_identity,
        }
    return Release1StudyRequest(
        role=role,
        candidate=candidate,
        twin=twin,
        problem_id=state.physics_scope.problem_system_identity,
        model_identity=tuple(state.physics_scope.execution_model_reference),
        solver_identity=tuple(state.physics_scope.solver_identity),
        physics_scope_identity=state.physics_scope.physics_scope_identity,
        execution_semantics_identity=state.physics_scope.execution_semantics_identity,
        **kwargs,
    )


def _memory_entry(memory: DesignMemoryRecord, evaluation_id: str) -> DesignMemoryEntry:
    matches = tuple(
        entry
        for entry in memory.layer_a.entries
        if entry.evaluation.evaluation_id == evaluation_id
    )
    if len(matches) != 1:
        raise InvalidScientificProblem("Release 1 memory entry is not unique")
    return matches[0]


def _mind_sources(state: Any) -> tuple[dict[str, str], ...]:
    sources: list[dict[str, str]] = []
    for binding in state.evidence_bindings:
        evaluation = binding.evaluation
        if evaluation.eligibility is not SelectionEligibility.ELIGIBLE:
            raise InvalidScientificProblem("Release 1 Mind saw ineligible evaluation")
        evaluation.validate_candidate(binding.candidate)
        if evaluation.result_binding.to_dict() != binding.result_binding.to_dict():
            raise InvalidScientificProblem("Release 1 Mind evidence binding mismatch")
        if evaluation.design_space.key != state.memory.layer_a.scope.design_space.key:
            raise InvalidScientificProblem("Release 1 Mind evidence scope mismatch")
        sources.append(
            {
                "binding_identity": binding.binding_identity,
                "binding_digest": binding.binding_digest,
                "candidate_id": binding.candidate.candidate_id,
                "evaluation_id": evaluation.evaluation_id,
                "result_id": evaluation.result.result_id,
            }
        )
    return tuple(sources)


def _build_cycle(reference: ModuleType) -> Release1CycleResult:
    state = reference.build_pre_execution_state()
    initial_evaluation = state.generation_zero.evaluation(
        RELEASE1_INITIAL_CANDIDATE, "primary"
    )
    initial_candidate = state.generation_zero.candidate(RELEASE1_INITIAL_CANDIDATE)
    initial_twin = state.generation_zero.twin(RELEASE1_INITIAL_CANDIDATE)
    initial_study = _study_request(
        role="INITIAL_REFERENCE",
        candidate=initial_candidate,
        twin=initial_twin,
        state=state,
    )
    initial_observation = Release1LabObservation(
        study=initial_study,
        evaluation=initial_evaluation,
        result_binding=initial_evaluation.result_binding,
        memory_scope=state.memory.layer_a.scope,
        memory_entry=_memory_entry(state.memory, initial_evaluation.evaluation_id),
    )

    selected_execution = reference.execute_selected(state)
    selected = selected_execution.request.selected
    selected_study = _study_request(
        role="SELECTED_REFERENCE",
        candidate=selected.candidate,
        twin=selected.twin,
        state=state,
        selected=selected,
    )
    mind_decision = Release1MindDecision(
        policy_identity=RELEASE1_REFERENCE_POLICY,
        decision_identity=state.decision.decision_identity,
        selected_option_identity=state.decision.selected_option_identity,
        selected_option_label=state.decision.selected_option.option_label,
        source_evidence=_mind_sources(state),
        selected_study=selected_study,
    )
    admission = reference.admit_return(state, selected_execution)
    selected_observation = Release1LabObservation(
        study=selected_study,
        evaluation=selected_execution.evaluation,
        result_binding=selected_execution.result_binding,
        memory_scope=admission.returned_memory.layer_a.scope,
        memory_entry=admission.returned_entry,
    )
    all_candidates = state.generation_zero.candidates + (selected.candidate,)
    all_evaluations = state.generation_zero.evaluations + (
        selected_execution.evaluation,
    )
    verify_layer_a_attribution(
        layer_a=admission.returned_memory.layer_a,
        candidates=all_candidates,
        evaluations=all_evaluations,
    )
    return Release1CycleResult(
        initial_observation=initial_observation,
        mind_decision=mind_decision,
        selected_observation=selected_observation,
        final_memory=admission.returned_memory,
        next_cycle_source_identity=admission.next_cycle_source.source_identity,
        generation_2_executed=False,
    )


def _record_payload(
    *,
    cycle: Release1CycleResult,
    reference_digest: str,
    release_commit: str,
) -> dict[str, Any]:
    return {
        "schema": RELEASE1_CYCLE_SCHEMA,
        "release": {
            "distribution_name": "engineering-ai-core",
            "distribution_version": __version__,
            "public_api_manifest_schema": PUBLIC_V1_MANIFEST["schema"],
            "public_api_manifest_identity": _manifest_identity(),
            "reference_policy": RELEASE1_REFERENCE_POLICY,
            "reference_system": RELEASE1_REFERENCE_SYSTEM,
            "reference_module_sha256": reference_digest,
        },
        "environment": _environment_payload(release_commit),
        "scientific_configuration": {
            "model_identity": list(RELEASE1_REFERENCE_MODEL),
            "solver_identity": list(RELEASE1_REFERENCE_SOLVER),
            "problem_id": RELEASE1_REFERENCE_SYSTEM,
            "execution_semantics_identity": RELEASE1_REFERENCE_EXECUTION,
            "inputs": cycle.initial_observation.candidate.to_dict()["assignments"],
            "tolerances": {},
            "serialized_schemas": {
                "release_cycle": RELEASE1_CYCLE_SCHEMA,
                "release_study": RELEASE1_STUDY_SCHEMA,
                "scientific_result": "scientific_result/1",
                "result_binding": "design_result_binding/1",
                "design_evaluation": "design_evaluation/1",
                "design_memory": "design_memory_record/1",
            },
        },
        "cycle": cycle.to_dict(),
    }


def _write_atomic(path: Path, data: bytes) -> None:
    destination = path.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, destination)


def revalidate_release1_cycle(
    record_path: Path | str,
    *,
    reference_path: Path | str,
) -> Release1CycleResult:
    """Reload typed records, rederive the reference graph, and compare exactly."""

    path = Path(record_path).resolve(strict=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidScientificProblem("Release 1 record cannot be decoded") from exc
    _require_exact_keys(
        payload,
        {"schema", "release", "environment", "scientific_configuration", "cycle"},
        "Release 1 record",
    )
    if payload["schema"] != RELEASE1_CYCLE_SCHEMA:
        raise InvalidScientificProblem("Release 1 record schema mismatch")
    cycle = Release1CycleResult.from_dict(payload["cycle"])
    reference, reference_digest = _load_reference_module(Path(reference_path))
    try:
        if payload["release"]["reference_module_sha256"] != reference_digest:
            raise InvalidScientificProblem("Release 1 reference module changed")
        if payload["release"]["public_api_manifest_identity"] != _manifest_identity():
            raise InvalidScientificProblem("Release 1 Public V1 manifest changed")
        if payload["release"]["distribution_version"] != __version__:
            raise InvalidScientificProblem("Release 1 distribution version changed")
        rederived = _build_cycle(reference)
        if rederived.to_dict() != cycle.to_dict():
            raise InvalidScientificProblem(
                "Release 1 rederived scientific graph does not match record"
            )
        return cycle
    finally:
        del reference
        _discard_reference_module()
        gc.collect()


def run_release1_cycle(
    *,
    output_path: Path | str,
    reference_path: Path | str,
    release_commit: str,
) -> Release1CycleResult:
    """Execute exactly one D7-derived Release 1 cycle, persist, discard, reload."""

    reference, reference_digest = _load_reference_module(Path(reference_path))
    try:
        cycle = _build_cycle(reference)
        payload = _record_payload(
            cycle=cycle,
            reference_digest=reference_digest,
            release_commit=release_commit,
        )
        data = _canonical_bytes(payload) + b"\n"
        _write_atomic(Path(output_path), data)
    finally:
        if "cycle" in locals():
            del cycle
        del reference
        _discard_reference_module()
        gc.collect()
    return revalidate_release1_cycle(
        output_path,
        reference_path=reference_path,
    )


def _summary(cycle: Release1CycleResult, output_path: Path) -> dict[str, Any]:
    return {
        "schema": RELEASE1_CYCLE_SCHEMA,
        "artifact": str(output_path.resolve()),
        "cycle_identity": cycle.cycle_identity,
        "initial_study": cycle.initial_observation.study.study_identity,
        "initial_candidate": cycle.initial_observation.candidate.candidate_id,
        "initial_result": cycle.initial_observation.result.result_id,
        "mind_decision": cycle.mind_decision.decision_identity,
        "selected_study": cycle.selected_observation.study.study_identity,
        "selected_candidate": cycle.selected_observation.candidate.candidate_id,
        "selected_result": cycle.selected_observation.result.result_id,
        "returned_memory_entry": cycle.selected_observation.memory_entry.identity,
        "generation_2_executed": cycle.generation_2_executed,
        "revalidated": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--revalidate-only", action="store_true")
    args = parser.parse_args()
    if args.revalidate_only:
        cycle = revalidate_release1_cycle(
            args.output,
            reference_path=args.reference,
        )
    else:
        cycle = run_release1_cycle(
            output_path=args.output,
            reference_path=args.reference,
            release_commit=args.release_commit,
        )
    print(json.dumps(_summary(cycle, args.output), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()


__all__: list[str] = []
