from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engcore.design import d4_recombination as d4
from engcore.design import d6_next_experiment as d6
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.twins.definition import ScientificTwin, TwinKind


def _options():
    return d6.build_option_set()


def test_exact_option_set_signal_table_and_identities() -> None:
    options = _options()
    assert [option.option_label for option in options] == list("ABCDEF")
    assert {option.option_label: option.option_identity for option in options} == d6.EXPECTED_OPTION_IDENTITIES
    assert d6.signal_table(options) == {
        "A": {
            "alpha_predicted_yield": 88.0,
            "alpha_predicted_loss": 18.0,
            "alpha_predicted_stability": 66.0,
            "alpha_target_pass": True,
            "beta_predicted_yield": 84.0,
            "beta_predicted_loss": 20.0,
            "beta_predicted_stability": 64.0,
            "beta_target_pass": True,
            "predicted_target_pass": True,
            "predicted_yield": 88.0,
            "predicted_loss": 18.0,
            "predicted_stability": 66.0,
            "uncertainty": 0.08,
            "model_disagreement": 0.04,
            "novelty_distance": 0.2,
            "contradiction": False,
            "partial_success": True,
            "useful_failure": False,
            "information_units": 1,
            "compute_cost": 1,
            "information_per_compute": "1/1",
        },
        "B": {
            "alpha_predicted_yield": 52.0,
            "alpha_predicted_loss": 22.0,
            "alpha_predicted_stability": 54.0,
            "alpha_target_pass": False,
            "beta_predicted_yield": 72.0,
            "beta_predicted_loss": 32.0,
            "beta_predicted_stability": 38.0,
            "beta_target_pass": False,
            "predicted_target_pass": False,
            "predicted_yield": 52.0,
            "predicted_loss": 22.0,
            "predicted_stability": 54.0,
            "uncertainty": 0.31,
            "model_disagreement": 0.2,
            "novelty_distance": 0.4,
            "contradiction": False,
            "partial_success": False,
            "useful_failure": True,
            "information_units": 3,
            "compute_cost": 2,
            "information_per_compute": "3/2",
        },
        "C": {
            "alpha_predicted_yield": 60.0,
            "alpha_predicted_loss": 24.0,
            "alpha_predicted_stability": 62.0,
            "alpha_target_pass": False,
            "beta_predicted_yield": 50.0,
            "beta_predicted_loss": 29.0,
            "beta_predicted_stability": 72.0,
            "beta_target_pass": False,
            "predicted_target_pass": False,
            "predicted_yield": 60.0,
            "predicted_loss": 24.0,
            "predicted_stability": 62.0,
            "uncertainty": 0.18,
            "model_disagreement": 0.1,
            "novelty_distance": 0.6,
            "contradiction": False,
            "partial_success": False,
            "useful_failure": False,
            "information_units": 1,
            "compute_cost": 5,
            "information_per_compute": "1/5",
        },
        "D": {
            "alpha_predicted_yield": 64.0,
            "alpha_predicted_loss": 30.0,
            "alpha_predicted_stability": 9.0,
            "alpha_target_pass": False,
            "beta_predicted_yield": 64.0,
            "beta_predicted_loss": 30.0,
            "beta_predicted_stability": 9.0,
            "beta_target_pass": False,
            "predicted_target_pass": False,
            "predicted_yield": 64.0,
            "predicted_loss": 30.0,
            "predicted_stability": 9.0,
            "uncertainty": 0.03,
            "model_disagreement": 0.0,
            "novelty_distance": 0.0,
            "contradiction": False,
            "partial_success": False,
            "useful_failure": False,
            "information_units": 0,
            "compute_cost": 1,
            "information_per_compute": "0/1",
        },
        "E": {
            "alpha_predicted_yield": 82.0,
            "alpha_predicted_loss": 22.0,
            "alpha_predicted_stability": 52.0,
            "alpha_target_pass": True,
            "beta_predicted_yield": 48.0,
            "beta_predicted_loss": 38.0,
            "beta_predicted_stability": 18.0,
            "beta_target_pass": False,
            "predicted_target_pass": True,
            "predicted_yield": 82.0,
            "predicted_loss": 22.0,
            "predicted_stability": 52.0,
            "uncertainty": 0.29,
            "model_disagreement": 0.34,
            "novelty_distance": 0.4,
            "contradiction": True,
            "partial_success": False,
            "useful_failure": True,
            "information_units": 4,
            "compute_cost": 4,
            "information_per_compute": "4/4",
        },
        "F": {
            "alpha_predicted_yield": 50.0,
            "alpha_predicted_loss": 8.0,
            "alpha_predicted_stability": 82.0,
            "alpha_target_pass": False,
            "beta_predicted_yield": 46.0,
            "beta_predicted_loss": 5.0,
            "beta_predicted_stability": 76.0,
            "beta_target_pass": False,
            "predicted_target_pass": False,
            "predicted_yield": 50.0,
            "predicted_loss": 8.0,
            "predicted_stability": 82.0,
            "uncertainty": 0.16,
            "model_disagreement": 0.06,
            "novelty_distance": 0.4,
            "contradiction": False,
            "partial_success": True,
            "useful_failure": False,
            "information_units": 1,
            "compute_cost": 2,
            "information_per_compute": "1/2",
        },
    }


def test_selection_ordering_best_predicted_raw_info_and_decision_identity() -> None:
    options = _options()
    assert [option.option_label for option in d6.rank_options(options)] == ["B", "E", "A", "F", "C", "D"]
    assert d6.best_predicted_performance_option(options).option_label == "A"
    assert d6.raw_information_units_winner(options).option_label == "E"
    decision = d6.select_next_experiment(options)
    assert decision.selected_option.option_label == "B"
    assert decision.selected_option.option_identity == d6.EXPECTED_OPTION_IDENTITIES["B"]
    assert decision.decision_identity == d6.EXPECTED_DECISION_IDENTITY
    assert d6.validate_decision_round_trip(decision) is True
    assert d6.select_next_experiment(tuple(reversed(options))).decision_identity == decision.decision_identity


def test_selected_execution_creates_new_twin_and_scientific_result_after_decision() -> None:
    decision = d6.select_next_experiment()
    assert "result_id" not in decision.identity_payload()
    execution = d6.execute_selected_experiment(decision)
    assert isinstance(execution.twin, ScientificTwin)
    assert execution.twin.kind is TwinKind.CANDIDATE
    assert isinstance(execution.result, ScientificResult)
    assert execution.selected_option.option_label == "B"
    assert execution.to_dict()["assignment"] == {
        "adapter": "buffered",
        "component_a": "A_peak",
        "component_b": "B_filter",
        "control_level": 1,
        "guard_enabled": False,
    }
    assert execution.to_dict()["scientific_result"] == {
        "loss_score": 33.0,
        "stability_score": -12.0,
        "yield_score": 35.0,
    }
    assert execution.to_dict()["target_pass"] is False
    assert execution.to_dict()["pre_execution_uncertainty"] == 0.31
    assert execution.to_dict()["pre_execution_disagreement"] == 0.2
    assert execution.to_dict()["post_execution_uncertainty"] == 0.0
    assert execution.to_dict()["post_execution_disagreement"] == 0.0
    assert execution.result.provenance.metadata["decision_provenance_only"] is True
    assert d6.validate_execution_round_trip(execution) is True


def test_signal_recompute_scope_cost_evidence_and_no_future_guards_fail_closed() -> None:
    option = next(item for item in _options() if item.option_label == "B")
    with pytest.raises(InvalidScientificProblem, match="disagreement"):
        replace(
            option,
            decision_signals=replace(option.decision_signals, model_disagreement=0.99),
        )
    with pytest.raises(InvalidScientificProblem, match="uncertainty"):
        replace(option, uncertainty_source_id="stale")
    with pytest.raises(InvalidScientificProblem, match="source evidence"):
        replace(option, source_evidence_refs=())
    with pytest.raises(InvalidScientificProblem, match="compute cost"):
        replace(
            option,
            decision_signals=replace(
                option.decision_signals,
                compute_cost=0,
                information_per_compute="3/0",
            ),
        )
    with pytest.raises(InvalidScientificProblem, match="future ScientificResult"):
        d6.D6NextExperimentDecision(
            options=_options(),
            selected_option=option,
            future_result_id="future",
        )
    with pytest.raises(InvalidScientificProblem, match="assignment mismatch"):
        d6.execute_selected_experiment(
            d6.select_next_experiment(),
            attempted_assignment=d4.typed_assignments("A_peak", "B_filter", "buffered", 2, False),
        )


def test_option_identity_sensitive_to_cost_and_evidence() -> None:
    option = next(item for item in _options() if item.option_label == "B")
    altered_cost = replace(
        option,
        decision_signals=replace(
            option.decision_signals,
            compute_cost=3,
            information_per_compute="3/3",
        ),
    )
    assert altered_cost.option_identity != option.option_identity
    altered_evidence = replace(
        option,
        source_evidence_refs=option.source_evidence_refs + ("d5-g0-baseline-population-v0.1",),
    )
    assert altered_evidence.option_identity != option.option_identity


def test_n1_through_n18_and_a1_through_a23_pass() -> None:
    adversarial = d6.adversarial_case_results()
    assert list(adversarial) == [f"N{index}" for index in range(1, 19)]
    assert all(result["status"] == "PASS" for result in adversarial.values())
    payload = d6.experiment_payload(
        targeted_tests="PASS - tests/test_design_d6_next_experiment.py",
        full_regression="PASS - full repository regression",
    )
    assert list(payload["a1_a23"]) == [f"A{index}" for index in range(1, 24)]
    assert all(payload["a1_a23"][f"A{index}"].startswith("PASS") for index in range(1, 24))
    assert payload["blocking_gates_passed"] is True
    assert payload["informative_results_recorded"] is True
    assert payload["adversarial_review"]["P0/P1"] == []
    assert set(payload["architecture_pulled"]) == {
        "ComputeCostEstimate",
        "DecisionSignal",
        "ExperimentDecisionProvenance",
        "ExperimentOption",
        "NextExperimentDecision",
        "no-future-result guard",
    }


def test_d6_deterministic_json_payload_and_source_boundaries() -> None:
    payload = d6.experiment_payload(
        targeted_tests="PASS - tests/test_design_d6_next_experiment.py",
        full_regression="PASS - full repository regression",
    )
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
    source = d6.__loader__.get_source(d6.__name__).lower()
    forbidden = (
        "botorch",
        "bayesian",
        "surrogate",
        "acquisition",
        "active learning",
        "reinforcement",
        "llm",
        "multirotor",
    )
    for token in forbidden:
        assert token not in source
