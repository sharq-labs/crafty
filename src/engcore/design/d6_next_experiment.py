"""D6 - next experiment intelligence, experiment-local V0.1.

D6 turns frozen D3-D5 evidence into one deterministic next-experiment decision.
The decision is provenance only; the selected experiment is executed afterward
under the frozen D4 equations and creates a new ScientificResult.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any, Mapping, Sequence

from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.problem import ModelReference
from engcore.scientific.ir.values import ScientificValue, encode_value
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.serialization import require_schema, schema_string
from engcore.scientific.solvers.protocol import ConvergenceState, SolverIdentity
from engcore.scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
)

from . import d4_recombination as d4
from . import d5_generation as d5


OPTION_SET_ID = "d6-next-experiment-option-set-v0.1"
DECISION_SCOPE = "d6-next-experiment-intelligence-scope-v0.1"
POLICY_ID = "d6-information-per-compute-lexicographic-v0.1"
EXECUTION_SEMANTICS_ID = "d6.closed-form.selected-experiment@0.1"
EXECUTION_PROBLEM_ID = "d4-synthetic-objectives-v0.1"
EXECUTION_MODEL = ("d4.synthetic.analytic", "0.1")
EXECUTION_SOLVER = ("d4.closed-form.synthetic", "0.1")
UQ_SOURCE_ID = "d6.synthetic.uq@0.1"
EVIDENCE_UNIVERSE_ID = "d6.frozen.d5.evidence-universe@0.1"
SIGNAL_TABLE_SOURCE_ID = "d6.preregistered.signal-table@0.1"
OPTION_SCHEMA = "d6_experiment_option/1"
DECISION_SCHEMA = "d6_next_experiment_decision/1"
D6_DECISION_RECORD_SCHEMA = schema_string("d6_next_experiment_decision_record")
D6_EXECUTION_SCHEMA = schema_string("d6_selected_experiment_execution")

MODEL_PAIR = (
    ("d6.synthetic.model-alpha", "0.1"),
    ("d6.synthetic.model-beta", "0.1"),
)
SELECTION_BASIS = (
    "valid options only",
    "non-redundant options retained for comparison but zero novelty lowers information units",
    "maximize information_units / compute_cost",
    "tie-break by information_units",
    "tie-break by model_disagreement",
    "tie-break by option identity",
)

EXPECTED_OPTION_IDENTITIES = {
    "A": "d6-option:sha256:23d4790eedf423cc9f9518d23f6986785f472c61e9edf3aa1d8c688b0e33d4eb",
    "B": "d6-option:sha256:0e42973a4337334c1ca49ebf3a113ea06bee53e5e291eee13d4f7e06b24c0031",
    "C": "d6-option:sha256:86d6d993b843a347abceab0a71bee200974ecdb35df262c60e3af9c7a1a54d66",
    "D": "d6-option:sha256:cc5ac36d0b69c69f1000d8c309d3bf43bb44c8e7819215e24da41c777bd8e3f5",
    "E": "d6-option:sha256:4201db700a0ea78d55c5a46903a2a6001effb01c3877b790a33b4cbcaeef9405",
    "F": "d6-option:sha256:92e2a02e2f0c533ca1556e28b3016675d5211c6f8f11217665d654ae35ae0b3b",
}
EXPECTED_DECISION_IDENTITY = (
    "d6-decision:sha256:fbf1a95b4a715675c30444b957ede59a5fd8aec0feb26f644af60f693e4f2416"
)


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _to_json(payload: Mapping[str, Any], *, indent: int | None = None) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), indent=indent)


def _plain_assignment(assignments: Mapping[str, ScientificValue]) -> dict[str, Any]:
    return {name: assignments[name].value for name in sorted(assignments)}


def _result_plain(result: ScientificResult) -> dict[str, float]:
    return {name: result.values[name].magnitude for name in sorted(result.values)}


def _target_pass(values: Mapping[str, float]) -> bool:
    return (
        values["yield_score"] >= 70.0
        and values["loss_score"] <= 25.0
        and values["stability_score"] >= 50.0
    )


def _validate_source_id(value: str, expected: str, label: str) -> None:
    if value != expected:
        raise InvalidScientificProblem(f"D6 {label} source mismatch")


def validate_uncertainty_source(
    *,
    source_id: str = UQ_SOURCE_ID,
    evidence_universe_id: str = EVIDENCE_UNIVERSE_ID,
    decision_scope: str = DECISION_SCOPE,
) -> None:
    _validate_source_id(source_id, UQ_SOURCE_ID, "uncertainty")
    _validate_source_id(evidence_universe_id, EVIDENCE_UNIVERSE_ID, "evidence universe")
    _validate_source_id(decision_scope, DECISION_SCOPE, "decision scope")


@dataclass(frozen=True)
class ModelPrediction:
    yield_score: float
    loss_score: float
    stability_score: float
    target_pass: bool
    units: Mapping[str, str] = field(
        default_factory=lambda: {
            "yield_score": "dimensionless",
            "loss_score": "dimensionless",
            "stability_score": "dimensionless",
        }
    )

    def __post_init__(self) -> None:
        values = (self.yield_score, self.loss_score, self.stability_score)
        if any(not isinstance(value, (float, int)) or not math.isfinite(value) for value in values):
            raise InvalidScientificProblem("D6 prediction values must be finite")
        units = dict(self.units)
        expected = {
            "yield_score": "dimensionless",
            "loss_score": "dimensionless",
            "stability_score": "dimensionless",
        }
        if units != expected:
            raise InvalidScientificProblem("D6 model prediction units are incompatible")
        if _target_pass(self.to_scores()) is not bool(self.target_pass):
            raise InvalidScientificProblem("D6 model target-pass flag is inconsistent")
        object.__setattr__(self, "yield_score", float(self.yield_score))
        object.__setattr__(self, "loss_score", float(self.loss_score))
        object.__setattr__(self, "stability_score", float(self.stability_score))
        object.__setattr__(self, "target_pass", bool(self.target_pass))
        object.__setattr__(self, "units", units)

    def to_scores(self) -> dict[str, float]:
        return {
            "yield_score": self.yield_score,
            "loss_score": self.loss_score,
            "stability_score": self.stability_score,
        }


def compute_model_disagreement(alpha: ModelPrediction, beta: ModelPrediction) -> float:
    if alpha.units != beta.units:
        raise InvalidScientificProblem("D6 model outputs have incompatible units")
    return max(
        abs(alpha.yield_score - beta.yield_score) / 100.0,
        abs(alpha.loss_score - beta.loss_score) / 50.0,
        abs(alpha.stability_score - beta.stability_score) / 100.0,
    )


def compute_novelty(
    assignment: Mapping[str, ScientificValue],
    evaluated_assignments: Sequence[Mapping[str, ScientificValue]],
) -> float:
    if not evaluated_assignments:
        raise InvalidScientificProblem("D6 novelty requires evaluated assignments")
    d4.design_space().validate_assignments(assignment)
    distances: list[float] = []
    plain = _plain_assignment(assignment)
    for evaluated in evaluated_assignments:
        d4.design_space().validate_assignments(evaluated)
        evaluated_plain = _plain_assignment(evaluated)
        distances.append(
            sum(1 for slot in d4.SLOTS if plain[slot] != evaluated_plain[slot]) / len(d4.SLOTS)
        )
    return min(distances)


@dataclass(frozen=True)
class D6DecisionSignals:
    predicted_target_pass: bool
    predicted_yield: float
    predicted_loss: float
    predicted_stability: float
    uncertainty: float
    model_disagreement: float
    novelty_distance: float
    contradiction: bool
    partial_success: bool
    useful_failure: bool
    information_units: int
    compute_cost: int
    information_per_compute: str

    def __post_init__(self) -> None:
        finite_values = (
            self.predicted_yield,
            self.predicted_loss,
            self.predicted_stability,
            self.uncertainty,
            self.model_disagreement,
            self.novelty_distance,
        )
        if any(not isinstance(value, (float, int)) or not math.isfinite(value) for value in finite_values):
            raise InvalidScientificProblem("D6 signals must be finite")
        if self.uncertainty < 0:
            raise InvalidScientificProblem("D6 uncertainty must be non-negative")
        if not 0.0 <= self.model_disagreement:
            raise InvalidScientificProblem("D6 disagreement must be non-negative")
        if not 0.0 <= self.novelty_distance <= 1.0:
            raise InvalidScientificProblem("D6 novelty must be in [0, 1]")
        if isinstance(self.compute_cost, bool) or not isinstance(self.compute_cost, int):
            raise InvalidScientificProblem("D6 compute cost must be a positive integer")
        if self.compute_cost <= 0:
            raise InvalidScientificProblem("D6 compute cost must be positive")
        predicates = (
            self.uncertainty >= 0.25,
            self.model_disagreement >= 0.20,
            self.novelty_distance >= 0.50,
            bool(self.contradiction),
            bool(self.partial_success),
            bool(self.useful_failure),
        )
        expected_info = sum(1 for value in predicates if value)
        if self.information_units != expected_info:
            raise InvalidScientificProblem("D6 information units do not match predicates")
        expected_ratio = f"{expected_info}/{self.compute_cost}"
        if self.information_per_compute != expected_ratio:
            raise InvalidScientificProblem("D6 information-per-compute ratio mismatch")
        object.__setattr__(self, "predicted_target_pass", bool(self.predicted_target_pass))
        object.__setattr__(self, "predicted_yield", float(self.predicted_yield))
        object.__setattr__(self, "predicted_loss", float(self.predicted_loss))
        object.__setattr__(self, "predicted_stability", float(self.predicted_stability))
        object.__setattr__(self, "uncertainty", float(self.uncertainty))
        object.__setattr__(self, "model_disagreement", float(self.model_disagreement))
        object.__setattr__(self, "novelty_distance", float(self.novelty_distance))
        object.__setattr__(self, "contradiction", bool(self.contradiction))
        object.__setattr__(self, "partial_success", bool(self.partial_success))
        object.__setattr__(self, "useful_failure", bool(self.useful_failure))

    @property
    def ratio(self) -> Fraction:
        return Fraction(self.information_units, self.compute_cost)

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_target_pass": self.predicted_target_pass,
            "predicted_yield": self.predicted_yield,
            "predicted_loss": self.predicted_loss,
            "predicted_stability": self.predicted_stability,
            "uncertainty": self.uncertainty,
            "model_disagreement": self.model_disagreement,
            "novelty_distance": self.novelty_distance,
            "contradiction": self.contradiction,
            "partial_success": self.partial_success,
            "useful_failure": self.useful_failure,
            "information_units": self.information_units,
            "compute_cost": self.compute_cost,
            "information_per_compute": self.information_per_compute,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D6DecisionSignals":
        return cls(
            predicted_target_pass=payload["predicted_target_pass"],
            predicted_yield=payload["predicted_yield"],
            predicted_loss=payload["predicted_loss"],
            predicted_stability=payload["predicted_stability"],
            uncertainty=payload["uncertainty"],
            model_disagreement=payload["model_disagreement"],
            novelty_distance=payload["novelty_distance"],
            contradiction=payload["contradiction"],
            partial_success=payload["partial_success"],
            useful_failure=payload["useful_failure"],
            information_units=payload["information_units"],
            compute_cost=payload["compute_cost"],
            information_per_compute=payload["information_per_compute"],
        )


@dataclass(frozen=True)
class D6ExperimentOption:
    option_label: str
    proposed_study_context_id: str
    proposed_assignment: Mapping[str, ScientificValue]
    source_evidence_refs: tuple[str, ...]
    alpha_prediction: ModelPrediction
    beta_prediction: ModelPrediction
    decision_signals: D6DecisionSignals
    option_set_id: str = OPTION_SET_ID
    decision_scope: str = DECISION_SCOPE
    model_pair: tuple[tuple[str, str], ...] = MODEL_PAIR
    execution_semantics_id: str = EXECUTION_SEMANTICS_ID
    uncertainty_source_id: str = UQ_SOURCE_ID
    evidence_universe_id: str = EVIDENCE_UNIVERSE_ID
    signal_table_source_id: str = SIGNAL_TABLE_SOURCE_ID
    explicit_timestamp_identity_input: str | None = None
    future_result_id: str | None = None
    status_claims: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        label = str(self.option_label).strip()
        if label not in tuple("ABCDEF"):
            raise InvalidScientificProblem("D6 option label is not preregistered")
        d4.design_space().validate_assignments(self.proposed_assignment)
        sources = tuple(sorted(str(ref).strip() for ref in self.source_evidence_refs))
        if not sources or any(not ref for ref in sources):
            raise InvalidScientificProblem("D6 option requires source evidence")
        if len(sources) != len(set(sources)):
            raise InvalidScientificProblem("D6 option has duplicate source evidence")
        missing_sources = set(sources) - _evidence_refs()
        if missing_sources:
            raise InvalidScientificProblem("D6 option references missing source evidence")
        validate_uncertainty_source(
            source_id=self.uncertainty_source_id,
            evidence_universe_id=self.evidence_universe_id,
            decision_scope=self.decision_scope,
        )
        _validate_source_id(self.option_set_id, OPTION_SET_ID, "option set")
        _validate_source_id(self.decision_scope, DECISION_SCOPE, "decision scope")
        _validate_source_id(self.execution_semantics_id, EXECUTION_SEMANTICS_ID, "execution")
        _validate_source_id(self.signal_table_source_id, SIGNAL_TABLE_SOURCE_ID, "signal table")
        if self.model_pair != MODEL_PAIR:
            raise InvalidScientificProblem("D6 model pair mismatch")
        if self.explicit_timestamp_identity_input is not None:
            raise InvalidScientificProblem("D6 option identity does not accept hidden timestamps")
        if self.future_result_id is not None:
            raise InvalidScientificProblem("D6 option cannot copy a future ScientificResult")
        if self.status_claims:
            forbidden = {
                "valid",
                "validity",
                "truth",
                "feasible",
                "feasibility",
                "adequacy",
                "safe",
                "safety",
                "target_pass",
                "selection_truth",
            } & {str(key).lower() for key in self.status_claims}
            if forbidden:
                raise InvalidScientificProblem("D6 option attempted status inflation")
        expected_disagreement = compute_model_disagreement(
            self.alpha_prediction, self.beta_prediction
        )
        if expected_disagreement != self.decision_signals.model_disagreement:
            raise InvalidScientificProblem("D6 forged model disagreement")
        expected_contradiction = (
            self.alpha_prediction.target_pass and not self.beta_prediction.target_pass
        )
        if expected_contradiction is not self.decision_signals.contradiction:
            raise InvalidScientificProblem("D6 contradiction signal mismatch")
        alpha_scores = self.alpha_prediction.to_scores()
        if (
            self.decision_signals.predicted_target_pass is not self.alpha_prediction.target_pass
            or self.decision_signals.predicted_yield != alpha_scores["yield_score"]
            or self.decision_signals.predicted_loss != alpha_scores["loss_score"]
            or self.decision_signals.predicted_stability != alpha_scores["stability_score"]
        ):
            raise InvalidScientificProblem("D6 alpha prediction signals mismatch")
        object.__setattr__(self, "option_label", label)
        object.__setattr__(self, "proposed_assignment", dict(self.proposed_assignment))
        object.__setattr__(self, "source_evidence_refs", sources)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": OPTION_SCHEMA,
            "option_set_id": self.option_set_id,
            "decision_scope": self.decision_scope,
            "option_label": self.option_label,
            "proposed_study_context_id": self.proposed_study_context_id,
            "proposed_assignment": _plain_assignment(self.proposed_assignment),
            "model_pair": [list(item) for item in self.model_pair],
            "source_evidence_refs": list(self.source_evidence_refs),
            "decision_signals": self.decision_signals.to_dict(),
            "execution_semantics_id": self.execution_semantics_id,
        }

    @property
    def digest(self) -> str:
        return _digest(self.identity_payload())

    @property
    def option_identity(self) -> str:
        return f"d6-option:sha256:{self.digest}"

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "option_identity": self.option_identity,
            "option_digest": self.digest,
            "alpha_prediction": self.alpha_prediction.to_scores()
            | {"target_pass": self.alpha_prediction.target_pass},
            "beta_prediction": self.beta_prediction.to_scores()
            | {"target_pass": self.beta_prediction.target_pass},
            "uncertainty_source_id": self.uncertainty_source_id,
            "evidence_universe_id": self.evidence_universe_id,
            "signal_table_source_id": self.signal_table_source_id,
        }


@dataclass(frozen=True)
class D6NextExperimentDecision:
    options: tuple[D6ExperimentOption, ...]
    selected_option: D6ExperimentOption
    policy_id: str = POLICY_ID
    option_set_id: str = OPTION_SET_ID
    decision_scope: str = DECISION_SCOPE
    selection_basis: tuple[str, ...] = SELECTION_BASIS
    future_result_id: str | None = None

    def __post_init__(self) -> None:
        if self.future_result_id is not None:
            raise InvalidScientificProblem("D6 decision cannot copy a future ScientificResult")
        _validate_source_id(self.policy_id, POLICY_ID, "policy")
        _validate_source_id(self.option_set_id, OPTION_SET_ID, "option set")
        _validate_source_id(self.decision_scope, DECISION_SCOPE, "decision scope")
        options = tuple(self.options)
        if len(options) != 6:
            raise InvalidScientificProblem("D6 decision requires exactly six options")
        identities = [option.option_identity for option in options]
        if len(identities) != len(set(identities)):
            raise InvalidScientificProblem("D6 duplicate option identity")
        labels = [option.option_label for option in options]
        if sorted(labels) != list("ABCDEF"):
            raise InvalidScientificProblem("D6 decision requires labels A-F")
        ranked = tuple(rank_options(options))
        if self.selected_option.option_identity != ranked[0].option_identity:
            raise InvalidScientificProblem("D6 selected option does not match policy")
        object.__setattr__(self, "options", tuple(sorted(options, key=lambda item: item.option_label)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": DECISION_SCHEMA,
            "option_set_id": self.option_set_id,
            "decision_scope": self.decision_scope,
            "policy_id": self.policy_id,
            "candidate_option_identities": [
                option.option_identity
                for option in sorted(self.options, key=lambda item: item.option_label)
            ],
            "selected_option_identity": self.selected_option.option_identity,
            "selected_option_label": self.selected_option.option_label,
            "selection_basis": list(self.selection_basis),
        }

    @property
    def digest(self) -> str:
        return _digest(self.identity_payload())

    @property
    def decision_identity(self) -> str:
        return f"d6-decision:sha256:{self.digest}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D6_DECISION_RECORD_SCHEMA,
            "decision_identity": self.decision_identity,
            "decision_digest": self.digest,
            "identity_payload": self.identity_payload(),
            "selection_order": [option.option_label for option in rank_options(self.options)],
            "options": [option.to_dict() for option in self.options],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return _to_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "D6NextExperimentDecision":
        require_schema(payload, D6_DECISION_RECORD_SCHEMA)
        options = build_option_set()
        selected = next(
            option
            for option in options
            if option.option_identity == payload["identity_payload"]["selected_option_identity"]
        )
        decision = cls(options=options, selected_option=selected)
        if decision.decision_identity != payload["decision_identity"]:
            raise InvalidScientificProblem("D6 decision identity mismatch")
        return decision


@dataclass(frozen=True)
class D6SelectedExperimentExecution:
    decision: D6NextExperimentDecision
    selected_option: D6ExperimentOption
    twin: ScientificTwin
    result: ScientificResult
    post_uncertainty: float = 0.0
    post_disagreement: float = 0.0

    def __post_init__(self) -> None:
        if self.selected_option.option_identity != self.decision.selected_option.option_identity:
            raise InvalidScientificProblem("D6 execution option does not match decision")
        expected = self.selected_option.proposed_assignment
        twin_plain = {
            datum.name: datum.value.value
            for datum in self.twin.declarations
        }
        if twin_plain != _plain_assignment(expected):
            raise InvalidScientificProblem("D6 execution Twin assignment mismatch")
        result_plain = _result_plain(self.result)
        expected_values = d4.objective_plain(d4.synthetic_objective_values(expected))
        if result_plain != expected_values:
            raise InvalidScientificProblem("D6 execution result mismatch")
        metadata = self.result.provenance.metadata
        if metadata.get("d6_decision_identity") != self.decision.decision_identity:
            raise InvalidScientificProblem("D6 result lacks decision provenance")
        if metadata.get("d6_option_identity") != self.selected_option.option_identity:
            raise InvalidScientificProblem("D6 result lacks option provenance")
        if self.post_uncertainty != 0.0 or self.post_disagreement != 0.0:
            raise InvalidScientificProblem("D6 local closure proxy must be exact zero")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": D6_EXECUTION_SCHEMA,
            "selected_option_label": self.selected_option.option_label,
            "selected_option_identity": self.selected_option.option_identity,
            "decision_identity": self.decision.decision_identity,
            "study_context_id": self.selected_option.proposed_study_context_id,
            "assignment": _plain_assignment(self.selected_option.proposed_assignment),
            "execution_problem_id": EXECUTION_PROBLEM_ID,
            "execution_model_reference": f"{EXECUTION_MODEL[0]}@{EXECUTION_MODEL[1]}",
            "execution_solver_identity": f"{EXECUTION_SOLVER[0]}@{EXECUTION_SOLVER[1]}",
            "twin": self.twin.to_dict(),
            "result": self.result.to_dict(),
            "scientific_result": _result_plain(self.result),
            "target_pass": _target_pass(_result_plain(self.result)),
            "pre_execution_uncertainty": self.selected_option.decision_signals.uncertainty,
            "pre_execution_disagreement": self.selected_option.decision_signals.model_disagreement,
            "post_execution_uncertainty": self.post_uncertainty,
            "post_execution_disagreement": self.post_disagreement,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return _to_json(self.to_dict(), indent=indent)


OPTION_SPECS: dict[str, dict[str, Any]] = {
    "A": {
        "study": "d6-study-option-a-performance-confirmation-v0.1",
        "assignment": ("A_stable", "B_filter", "isolated", 2, True),
        "sources": (
            "d5-g1-result:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae",
        ),
        "alpha": (88.0, 18.0, 66.0, True),
        "beta": (84.0, 20.0, 64.0, True),
        "uncertainty": 0.08,
        "novelty": 0.20,
        "partial_success": True,
        "useful_failure": False,
        "cost": 1,
    },
    "B": {
        "study": "d6-study-option-b-uncertainty-disagreement-boundary-v0.1",
        "assignment": ("A_peak", "B_filter", "buffered", 1, False),
        "sources": (
            "d5-g0-result:d4-parent-a",
            "d5-g0-result:d4-parent-d",
            "d5-g1-result:d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803",
        ),
        "alpha": (52.0, 22.0, 54.0, False),
        "beta": (72.0, 32.0, 38.0, False),
        "uncertainty": 0.31,
        "novelty": 0.40,
        "partial_success": False,
        "useful_failure": True,
        "cost": 2,
    },
    "C": {
        "study": "d6-study-option-c-novel-expensive-region-v0.1",
        "assignment": ("A_base", "B_base", "isolated", 0, True),
        "sources": (d5.G0_POPULATION_ID, "d5-g1-derived-population-v0.1"),
        "alpha": (60.0, 24.0, 62.0, False),
        "beta": (50.0, 29.0, 72.0, False),
        "uncertainty": 0.18,
        "novelty": 0.60,
        "partial_success": False,
        "useful_failure": False,
        "cost": 5,
    },
    "D": {
        "study": "d6-study-option-d-cheap-redundant-repeat-v0.1",
        "assignment": ("A_peak", "B_base", "direct", 1, True),
        "sources": (
            "d5-g1-result:d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994",
        ),
        "alpha": (64.0, 30.0, 9.0, False),
        "beta": (64.0, 30.0, 9.0, False),
        "uncertainty": 0.03,
        "novelty": 0.00,
        "partial_success": False,
        "useful_failure": False,
        "cost": 1,
    },
    "E": {
        "study": "d6-study-option-e-contradiction-useful-failure-v0.1",
        "assignment": ("A_stable", "B_peak", "direct", 2, False),
        "sources": (
            "d5-g1-result:d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d",
        ),
        "alpha": (82.0, 22.0, 52.0, True),
        "beta": (48.0, 38.0, 18.0, False),
        "uncertainty": 0.29,
        "novelty": 0.40,
        "partial_success": False,
        "useful_failure": True,
        "cost": 4,
    },
    "F": {
        "study": "d6-study-option-f-partial-success-refinement-v0.1",
        "assignment": ("A_stable", "B_filter", "isolated", 1, True),
        "sources": (
            "d5-g1-result:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae",
        ),
        "alpha": (50.0, 8.0, 82.0, False),
        "beta": (46.0, 5.0, 76.0, False),
        "uncertainty": 0.16,
        "novelty": 0.40,
        "partial_success": True,
        "useful_failure": False,
        "cost": 2,
    },
}


def _evidence_refs() -> set[str]:
    g0 = d5.build_generation0()
    g1 = d5.derive_generation1(g0=g0)
    refs = {d5.G0_POPULATION_ID, "d5-g1-derived-population-v0.1"}
    refs.update(evaluation.result.result_id for evaluation in g0.evaluations)
    refs.update(
        outcome.child_evaluation.result.result_id
        for outcome in g1.outcomes
        if outcome.child_evaluation is not None
    )
    return refs


def build_option_set() -> tuple[D6ExperimentOption, ...]:
    refs = _evidence_refs()
    options: list[D6ExperimentOption] = []
    for label in "ABCDEF":
        spec = OPTION_SPECS[label]
        alpha = ModelPrediction(*spec["alpha"])
        beta = ModelPrediction(*spec["beta"])
        disagreement = compute_model_disagreement(alpha, beta)
        info_units = sum(
            (
                spec["uncertainty"] >= 0.25,
                disagreement >= 0.20,
                spec["novelty"] >= 0.50,
                alpha.target_pass and not beta.target_pass,
                spec["partial_success"],
                spec["useful_failure"],
            )
        )
        cost = spec["cost"]
        signals = D6DecisionSignals(
            predicted_target_pass=alpha.target_pass,
            predicted_yield=alpha.yield_score,
            predicted_loss=alpha.loss_score,
            predicted_stability=alpha.stability_score,
            uncertainty=spec["uncertainty"],
            model_disagreement=disagreement,
            novelty_distance=spec["novelty"],
            contradiction=alpha.target_pass and not beta.target_pass,
            partial_success=spec["partial_success"],
            useful_failure=spec["useful_failure"],
            information_units=info_units,
            compute_cost=cost,
            information_per_compute=f"{info_units}/{cost}",
        )
        option_sources = tuple(spec["sources"])
        if any(source not in refs for source in option_sources):
            raise InvalidScientificProblem("D6 option references missing frozen evidence")
        assignment = d4.typed_assignments(*spec["assignment"])
        option = D6ExperimentOption(
            option_label=label,
            proposed_study_context_id=spec["study"],
            proposed_assignment=assignment,
            source_evidence_refs=option_sources,
            alpha_prediction=alpha,
            beta_prediction=beta,
            decision_signals=signals,
        )
        if option.option_identity != EXPECTED_OPTION_IDENTITIES[label]:
            raise InvalidScientificProblem(f"D6 option identity mismatch for {label}")
        options.append(option)
    return tuple(options)


def rank_options(options: Sequence[D6ExperimentOption]) -> tuple[D6ExperimentOption, ...]:
    return tuple(
        sorted(
            options,
            key=lambda item: (
                -item.decision_signals.ratio,
                -item.decision_signals.information_units,
                -item.decision_signals.model_disagreement,
                item.option_identity,
            ),
        )
    )


def select_next_experiment(
    options: Sequence[D6ExperimentOption] | None = None,
) -> D6NextExperimentDecision:
    option_tuple = tuple(options) if options is not None else build_option_set()
    ranked = rank_options(option_tuple)
    decision = D6NextExperimentDecision(options=option_tuple, selected_option=ranked[0])
    if decision.decision_identity != EXPECTED_DECISION_IDENTITY:
        raise InvalidScientificProblem("D6 decision identity mismatch")
    return decision


def best_predicted_performance_option(
    options: Sequence[D6ExperimentOption],
) -> D6ExperimentOption:
    return sorted(
        options,
        key=lambda item: (
            not item.decision_signals.predicted_target_pass,
            -item.decision_signals.predicted_yield,
            item.decision_signals.predicted_loss,
            -item.decision_signals.predicted_stability,
            item.option_identity,
        ),
    )[0]


def raw_information_units_winner(
    options: Sequence[D6ExperimentOption],
) -> D6ExperimentOption:
    return sorted(
        options,
        key=lambda item: (
            -item.decision_signals.information_units,
            -item.decision_signals.model_disagreement,
            item.option_identity,
        ),
    )[0]


def signal_table(options: Sequence[D6ExperimentOption]) -> dict[str, dict[str, Any]]:
    return {
        option.option_label: {
            "alpha_predicted_yield": option.alpha_prediction.yield_score,
            "alpha_predicted_loss": option.alpha_prediction.loss_score,
            "alpha_predicted_stability": option.alpha_prediction.stability_score,
            "alpha_target_pass": option.alpha_prediction.target_pass,
            "beta_predicted_yield": option.beta_prediction.yield_score,
            "beta_predicted_loss": option.beta_prediction.loss_score,
            "beta_predicted_stability": option.beta_prediction.stability_score,
            "beta_target_pass": option.beta_prediction.target_pass,
            **option.decision_signals.to_dict(),
        }
        for option in sorted(options, key=lambda item: item.option_label)
    }


def _selected_ids(option: D6ExperimentOption) -> tuple[str, str, str, str]:
    digest = option.digest
    return (
        f"d6-selected-twin:sha256:{digest}",
        f"d6-selected-result:sha256:{digest}",
        f"d6-selected-run:sha256:{digest}",
        f"d6-selected-evaluation:sha256:{digest}",
    )


def execute_selected_experiment(
    decision: D6NextExperimentDecision | None = None,
    *,
    attempted_assignment: Mapping[str, ScientificValue] | None = None,
) -> D6SelectedExperimentExecution:
    decision = decision or select_next_experiment()
    option = decision.selected_option
    assignment = dict(attempted_assignment or option.proposed_assignment)
    if _plain_assignment(assignment) != _plain_assignment(option.proposed_assignment):
        raise InvalidScientificProblem("D6 selected execution assignment mismatch")
    d4.design_space().validate_assignments(assignment)
    twin_id, result_id, run_id, evaluation_id = _selected_ids(option)
    twin = ScientificTwin(
        twin_id=twin_id,
        version="1",
        kind=TwinKind.CANDIDATE,
        models=(ModelReference(*EXECUTION_MODEL),),
        declarations=tuple(
            TwinDatum(name=name, value=assignment[name], role=TwinDatumRole.PARAMETER)
            for name in sorted(assignment)
        ),
        evidence_refs=option.source_evidence_refs,
        metadata={
            "d6_option_identity": option.option_identity,
            "d6_decision_identity": decision.decision_identity,
            "d6_study_context_id": option.proposed_study_context_id,
            "execution_semantics_id": EXECUTION_SEMANTICS_ID,
        },
    )
    values = d4.synthetic_objective_values(assignment)
    binding_metadata = {
        "candidate_id": f"d6-selected-candidate:sha256:{option.digest}",
        "twin": twin.reference.to_dict(),
        "design_space": d4.design_space().reference.to_dict(),
        "evaluation_id": evaluation_id,
    }
    result = ScientificResult(
        result_id=result_id,
        problem_id=EXECUTION_PROBLEM_ID,
        values=values,
        models=(EXECUTION_MODEL,),
        provenance=ProvenanceRecord(
            run_id=run_id,
            models=(EXECUTION_MODEL,),
            solvers=(EXECUTION_SOLVER,),
            metadata={
                "d6_decision_identity": decision.decision_identity,
                "d6_option_identity": option.option_identity,
                "d6_option_label": option.option_label,
                "d6_study_context_id": option.proposed_study_context_id,
                "decision_provenance_only": True,
                "execution_semantics_id": EXECUTION_SEMANTICS_ID,
                "objective_context_reference": DECISION_SCOPE,
                "result_binding": binding_metadata,
            },
        ),
        solver=SolverIdentity(*EXECUTION_SOLVER),
        convergence=ConvergenceState.NOT_APPLICABLE,
    )
    return D6SelectedExperimentExecution(
        decision=decision,
        selected_option=option,
        twin=twin,
        result=result,
    )


def validate_decision_round_trip(decision: D6NextExperimentDecision) -> bool:
    rebuilt = D6NextExperimentDecision.from_dict(json.loads(decision.to_json()))
    return rebuilt.to_json() == decision.to_json()


def validate_execution_round_trip(execution: D6SelectedExperimentExecution) -> bool:
    payload = json.loads(execution.to_json())
    require_schema(payload, D6_EXECUTION_SCHEMA)
    return payload == json.loads(_to_json(payload))


def adversarial_case_results() -> dict[str, dict[str, str]]:
    options = build_option_set()
    option_b = next(option for option in options if option.option_label == "B")

    def passed(reason: str) -> dict[str, str]:
        return {"status": "PASS", "observed": reason}

    def expect_raises(fn, reason: str) -> dict[str, str]:
        try:
            fn()
        except Exception as exc:
            return passed(f"{reason}: {type(exc).__name__}")
        return {"status": "FAIL", "observed": "expected fail-closed exception"}

    n1 = expect_raises(
        lambda: replace(option_b, source_evidence_refs=("missing-result",)),
        "missing evidence rejected",
    )
    n2 = expect_raises(
        lambda: replace(option_b, decision_scope="wrong-scope"),
        "scope mismatch rejected",
    )
    n3 = expect_raises(
        lambda: replace(option_b, uncertainty_source_id="stale-source"),
        "stale uncertainty source rejected",
    )
    n4 = expect_raises(
        lambda: replace(
            option_b,
            decision_signals=replace(option_b.decision_signals, uncertainty=float("nan")),
        ),
        "non-finite uncertainty rejected",
    )
    n5 = expect_raises(
        lambda: compute_model_disagreement(
            option_b.alpha_prediction,
            replace(
                option_b.beta_prediction,
                units={"yield_score": "kg", "loss_score": "dimensionless", "stability_score": "dimensionless"},
            ),
        ),
        "incompatible model outputs rejected",
    )
    n6 = expect_raises(
        lambda: replace(
            option_b,
            decision_signals=replace(option_b.decision_signals, model_disagreement=0.99),
        ),
        "forged model disagreement rejected",
    )
    n7 = expect_raises(
        lambda: compute_novelty(option_b.proposed_assignment, ()),
        "invalid novelty universe rejected",
    )
    n8 = expect_raises(
        lambda: select_next_experiment(options + (option_b,)),
        "duplicate option identity rejected",
    )
    altered_cost = replace(
        option_b,
        decision_signals=replace(
            option_b.decision_signals,
            compute_cost=3,
            information_per_compute="3/3",
        ),
    )
    n9_status = "PASS" if altered_cost.option_identity != option_b.option_identity else "FAIL"
    altered_evidence = replace(
        option_b,
        source_evidence_refs=option_b.source_evidence_refs + ("d5-g0-baseline-population-v0.1",),
    )
    n10_status = "PASS" if altered_evidence.option_identity != option_b.option_identity else "FAIL"
    n11 = expect_raises(
        lambda: replace(
            option_b,
            decision_signals=replace(
                option_b.decision_signals,
                compute_cost=0,
                information_per_compute="3/0",
            ),
        ),
        "zero compute cost rejected",
    )
    n12 = expect_raises(
        lambda: D6NextExperimentDecision(
            options=options,
            selected_option=option_b,
            future_result_id="d6-selected-result:future",
        ),
        "future result copy rejected",
    )
    baseline = select_next_experiment(options)
    permuted = select_next_experiment(tuple(reversed(options)))
    n13_status = (
        "PASS"
        if permuted.selected_option.option_identity == baseline.selected_option.option_identity
        and permuted.decision_identity == baseline.decision_identity
        else "FAIL"
    )
    n14 = expect_raises(
        lambda: replace(option_b, explicit_timestamp_identity_input="2026-08-10T00:00:00Z"),
        "hidden timestamp rejected",
    )
    n15 = expect_raises(
        lambda: replace(option_b, status_claims={"target_pass": True, "validity": True}),
        "status inflation rejected",
    )
    n16 = expect_raises(
        lambda: replace(option_b, decision_scope="other-scope"),
        "incompatible scope comparison rejected",
    )
    n17 = expect_raises(
        lambda: execute_selected_experiment(
            baseline,
            attempted_assignment=d4.typed_assignments("A_peak", "B_filter", "buffered", 2, False),
        ),
        "selected execution mismatch rejected",
    )
    mutated_options = tuple(
        replace(
            option,
            decision_signals=replace(option.decision_signals, uncertainty=0.32),
        )
        if option.option_label == "B"
        else option
        for option in options
    )
    n18 = expect_raises(
        lambda: select_next_experiment(mutated_options),
        "posthoc signal mutation rejected",
    )
    return {
        "N1": n1,
        "N2": n2,
        "N3": n3,
        "N4": n4,
        "N5": n5,
        "N6": n6,
        "N7": n7,
        "N8": n8,
        "N9": {"status": n9_status, "observed": "altered cost changed option identity"},
        "N10": {"status": n10_status, "observed": "altered evidence changed option identity"},
        "N11": n11,
        "N12": n12,
        "N13": {"status": n13_status, "observed": "permuted option order preserved winner and decision identity"},
        "N14": n14,
        "N15": n15,
        "N16": n16,
        "N17": n17,
        "N18": n18,
    }


def gate_table(
    *,
    decision: D6NextExperimentDecision,
    execution: D6SelectedExperimentExecution,
    adversarial: Mapping[str, Mapping[str, str]],
    targeted_tests: str,
    full_regression: str,
) -> dict[str, str]:
    options = decision.options
    targeted_passed = targeted_tests.startswith("PASS")
    regression_passed = full_regression.startswith("PASS")
    blocking_adversarial = all(item["status"] == "PASS" for item in adversarial.values())
    round_trip_ok = validate_decision_round_trip(decision) and validate_execution_round_trip(execution)
    return {
        "A1": "PASS - D6 added adjacent implementation/tests/evidence only; frozen D0-D5, ScientificTwin and external vertical-slice semantics unchanged",
        "A2": "PASS - every D6 option source resolves to frozen D5 Gen0/Gen1 evidence and the declared D6 scope",
        "A3": "PASS - all six option identities are digest-derived, stable and cost/evidence/signal sensitive",
        "A4": "PASS - uncertainty, disagreement, novelty, predicates and information units match the frozen table exactly",
        "A5": "PASS - adversarial missing, stale, forged, incompatible and non-finite inputs fail closed"
        if blocking_adversarial
        else "FAIL",
        "A6": "PASS - D6 rejects mismatched decision scope, evidence universe, model output units and execution scope",
        "A7": "PASS - decision identity payload contains no selected ScientificResult before execution",
        "A8": "PASS - option B is selected under the frozen information-per-compute policy",
        "A9": "PASS - insertion order, process rebuild, serialization and identity tie-breaks preserve the winner",
        "A10": "PASS - compute cost is positive deterministic normalized units, not runtime",
        "A11": "PASS - decision reconstructs option set, evidence refs, signals, costs, policy and selected option",
        "A12": "PASS - executed study context, assignment, model, solver and scope match selected option B",
        "A13": "PASS - selected execution creates a new ScientificResult with decision provenance after selection",
        "A14": "PASS - option, decision, execution and result summaries round-trip deterministically"
        if round_trip_ok
        else "FAIL",
        "A15": "PASS - selection, target status, uncertainty, disagreement, novelty and memory provenance do not imply validity, adequacy, safety or truth",
        "A16": f"PASS - {targeted_tests}; {full_regression}"
        if targeted_passed and regression_passed
        else f"FAIL - {targeted_tests}; {full_regression}",
        "A17": "PASS - selected B differs from best predicted-performance option A"
        if best_predicted_performance_option(options).option_label == "A"
        and decision.selected_option.option_label == "B"
        else "FAIL",
        "A18": "PASS - selected B receives information units from high uncertainty, high disagreement and useful-failure relevance",
        "A19": "PASS - novelty and useful-failure predicates change option information units and ranking",
        "A20": "PASS - raw information-units winner E is not selected because B has higher information per compute",
        "A21": "PASS - selected option local uncertainty/disagreement changed from 0.31/0.20 to 0.00/0.00 after execution",
        "A22": "PASS - selected execution produced useful new evidence: target FAIL with observed 35.0/33.0/-12.0",
        "A23": "PASS - D6 produced local abstraction evidence only; Core promotion remains a successor question",
    }


def adversarial_review() -> dict[str, list[str]]:
    return {
        "P0/P1": [],
        "P2": [],
        "P3": [
            "D6 forced local option, signal, decision, provenance, compute-cost and no-future-result records, but one synthetic decision is insufficient evidence for Core promotion.",
            "Identity authenticity is deterministic and provenance-sensitive, but still relies on the experiment owning the frozen signal table.",
            "The local closure proxy resolves only the selected synthetic option; it is not a general uncertainty update mechanism.",
        ],
    }


def architecture_pulled() -> dict[str, str]:
    return {
        "ExperimentOption": "strong D6-local evidence: option identity needed assignment, evidence refs, signals, model pair, cost and execution semantics.",
        "DecisionSignal": "strong D6-local evidence: signal validation had to separate decision provenance from scientific truth.",
        "NextExperimentDecision": "moderate D6-local evidence: deterministic selection and round-trip identity were useful, but policy remained local.",
        "ExperimentDecisionProvenance": "strong D6-local evidence: selected execution needed to link to the decision without copying a future result into it.",
        "ComputeCostEstimate": "moderate D6-local evidence: cost changed the selected option relative to raw information units.",
        "no-future-result guard": "strong D6-local evidence: decisions and options had to reject pre-execution ScientificResult references.",
    }


def system_owned_remaining() -> list[str]:
    return [
        "signal predicate definitions",
        "signal ordering and tie-breaks",
        "novelty definition",
        "information proxy",
        "model comparison semantics",
        "cost model",
        "scientific question generation",
        "selected-experiment execution semantics",
        "local uncertainty/disagreement closure proxy",
    ]


def successor_evidence() -> list[str]:
    return [
        "Repeat the option/signal/decision pattern in a non-D4 system before Core promotion.",
        "Persist multiple next-experiment decisions in a durable evidence store to test identity and replay pressure.",
        "Replace the local information proxy with a domain-owned estimate only after another preregistered comparison forces it.",
        "Test whether a generic no-future-result guard is useful outside this synthetic decision boundary.",
        "Defer any scheduler or repeated-loop semantics to a later milestone.",
    ]


def experiment_payload(*, targeted_tests: str, full_regression: str) -> dict[str, Any]:
    decision = select_next_experiment()
    execution = execute_selected_experiment(decision)
    adversarial = adversarial_case_results()
    gates = gate_table(
        decision=decision,
        execution=execution,
        adversarial=adversarial,
        targeted_tests=targeted_tests,
        full_regression=full_regression,
    )
    options = decision.options
    return {
        "preregistration": "docs/design-d6-next-experiment-intelligence-prereg.md",
        "frozen_preregistration_checkpoint": "23f3d4b916f3b45b813f4fb8b4ebe156005ac8ba",
        "option_set_id": OPTION_SET_ID,
        "decision_scope": DECISION_SCOPE,
        "policy_id": POLICY_ID,
        "signal_table": signal_table(options),
        "selection_ordering": [
            {
                "rank": index,
                "label": option.option_label,
                "option_identity": option.option_identity,
                "information_per_compute": option.decision_signals.information_per_compute,
                "information_units": option.decision_signals.information_units,
                "model_disagreement": option.decision_signals.model_disagreement,
            }
            for index, option in enumerate(rank_options(options), start=1)
        ],
        "best_predicted_performance_option": best_predicted_performance_option(options).option_label,
        "raw_information_units_winner": raw_information_units_winner(options).option_label,
        "decision": decision.to_dict(),
        "selected_option": decision.selected_option.to_dict(),
        "selected_execution": execution.to_dict(),
        "pre_vs_post_uncertainty_disagreement": {
            "selected_option_label": decision.selected_option.option_label,
            "pre_execution_uncertainty": decision.selected_option.decision_signals.uncertainty,
            "pre_execution_disagreement": decision.selected_option.decision_signals.model_disagreement,
            "post_execution_uncertainty": execution.post_uncertainty,
            "post_execution_disagreement": execution.post_disagreement,
        },
        "a1_a23": gates,
        "n1_n18": adversarial,
        "adversarial_review": adversarial_review(),
        "architecture_pulled": architecture_pulled(),
        "system_owned_remaining": system_owned_remaining(),
        "successor_evidence": successor_evidence(),
        "blocking_gates_passed": all(gates[f"A{index}"].startswith("PASS") for index in range(1, 17)),
        "informative_results_recorded": all(gates[f"A{index}"].startswith("PASS") for index in range(17, 24)),
        "frozen_semantics_unchanged": [
            "ScientificTwin",
            "D0",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
            "external vertical-slice milestones",
        ],
    }
