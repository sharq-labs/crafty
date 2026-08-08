from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.engcore.adaptive_policy import AdaptiveDecision
from src.engcore.adaptive_stacked_engine_v035 import (
    AdaptiveStackedGPBOEngineV035,
)
from src.engcore.candidate_arbiter import ProposalView, arbitrate_proposals
from src.engcore.models import ExperimentResult
from src.engcore.stacked_modes import get_stacked_mode
from src.engcore.validation.problem import Trace
from src.engcore.v035_ablation_analysis import (
    EXPECTED_ARMS,
    _strict_json_loads,
    _strict_json_value,
    strict_json_dumps,
    validate_campaign_integrity,
    validate_journal_uniqueness,
)
from src.engcore.v035_ablation_arena import (
    _claim_output,
    _finish_claim,
    _guard_empty_output,
    _make_progress_journal_class,
    _strict_write_results,
)


def _bare_mix_engine(dim=2):
    engine = object.__new__(AdaptiveStackedGPBOEngineV035)
    engine.space = SimpleNamespace(dim=dim)
    engine.fit_diagnostics = {}
    engine.events = []
    return engine


def _starts(n: int, dim: int = 2):
    rows = []
    for i in range(n):
        v = (i + 1) / (n + 2)
        rows.append([v] * dim)
    return np.asarray(rows, dtype=float)


def test_exploration_starts_enter_early_refinement_slots():
    engine = _bare_mix_engine()
    starts = _starts(6)
    scores = np.arange(6.0, 0.0, -1.0)

    mixed, mixed_scores = engine._mix_exploration_starts(
        starts,
        scores,
        mix=0.30,
        seed=123,
    )

    np.testing.assert_allclose(mixed[0], starts[0])
    assert mixed_scores[0] == scores[0]

    # top_k=6, mix=.30 => two explorers at positions 1 and 2.
    assert not np.allclose(mixed[1], starts[1])
    assert not np.allclose(mixed[2], starts[2])
    assert mixed_scores[1] == -np.inf
    assert mixed_scores[2] == -np.inf
    np.testing.assert_allclose(mixed[3:], starts[3:])


@pytest.mark.parametrize("mode", ["fast", "balanced", "quality"])
@pytest.mark.parametrize("mix", [0.15, 0.30])
def test_registered_modes_put_explorers_inside_refinement_slice(mode, mix):
    cfg = get_stacked_mode(mode)
    top_k = int(cfg["top_k"])
    refine_k = int(cfg["refinement_top_k"])
    engine = _bare_mix_engine()
    engine._v035_refinement_visible_slots = max(0, refine_k - 1)

    starts = _starts(top_k)
    scores = np.arange(float(top_k), 0.0, -1.0)
    mixed, mixed_scores = engine._mix_exploration_starts(
        starts, scores, mix=mix, seed=321
    )

    changed = [
        i for i in range(1, top_k)
        if not np.allclose(mixed[i], starts[i])
    ]
    assert changed, f"{mode=} {mix=} produced no effective exploration"
    assert all(i < refine_k for i in changed)
    assert all(mixed_scores[i] == -np.inf for i in changed)
    np.testing.assert_allclose(mixed[0], starts[0])


def test_custom_refinement_top_k_one_explicitly_disables_exploration():
    engine = _bare_mix_engine()
    engine._v035_refinement_visible_slots = 0
    starts = _starts(6)
    scores = np.arange(6.0, 0.0, -1.0)

    mixed, mixed_scores = engine._mix_exploration_starts(
        starts, scores, mix=0.30, seed=1
    )

    np.testing.assert_allclose(mixed, starts)
    np.testing.assert_allclose(mixed_scores, scores)
    assert engine.fit_diagnostics["adaptive_exploration_mix_disabled"] == 1
    assert engine.events[-1]["used_explorers"] == 0


def test_custom_small_refinement_slice_caps_exploration_to_visible_slots():
    engine = _bare_mix_engine()
    engine._v035_refinement_visible_slots = 1
    starts = _starts(6)
    scores = np.arange(6.0, 0.0, -1.0)

    mixed, mixed_scores = engine._mix_exploration_starts(
        starts, scores, mix=0.30, seed=1
    )

    changed = [
        i for i in range(1, len(starts))
        if not np.allclose(mixed[i], starts[i])
    ]
    assert changed == [1]
    assert mixed_scores[1] == -np.inf
    assert engine.fit_diagnostics["adaptive_exploration_starts_capped"] == 1


def test_nonempty_campaign_output_is_rejected(tmp_path: Path):
    out = tmp_path / "campaign"
    out.mkdir()
    (out / "progress.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="output directory is not empty"):
        _guard_empty_output(out)


def test_atomic_campaign_claim_allows_exactly_one_contender(tmp_path: Path):
    out = tmp_path / "campaign"

    def contender(i):
        try:
            fd, lock = _claim_output(out, f"campaign-{i}")
            return ("won", fd, lock, i)
        except SystemExit:
            return ("lost", None, None, i)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(contender, [1, 2]))

    winners = [r for r in results if r[0] == "won"]
    losers = [r for r in results if r[0] == "lost"]
    assert len(winners) == 1
    assert len(losers) == 1

    _, fd, lock, winner_id = winners[0]
    _finish_claim(fd, f"campaign-{winner_id}", status="complete")
    text = Path(lock).read_text(encoding="utf-8")
    assert "status=complete" in text


def test_strict_progress_journal_sanitizes_nested_nonfinite_values(tmp_path: Path):
    path = tmp_path / "progress.jsonl"
    Journal = _make_progress_journal_class("campaign-x")
    journal = Journal(path)
    try:
        journal.write({
            "kind": "run",
            "problem_id": "p",
            "metadata": {
                "nan": float("nan"),
                "nested": [float("inf"), -1.0],
            },
        })
    finally:
        journal.close()

    record = _strict_json_loads(path.read_text(encoding="utf-8"))
    assert record["campaign_id"] == "campaign-x"
    assert record["metadata"]["nan"] is None
    assert record["metadata"]["nested"][0] is None


def test_strict_write_results_publishes_standard_json_and_metadata(tmp_path: Path):
    trace = Trace(
        algorithm="stacked_v0301",
        problem_id="bbob_f001_i71_d02",
        dimension=2,
        budget=4,
        seed=1,
        best_f=1.0,
        evaluations=4,
        values=[4.0, 3.0, 2.0, 1.0],
        best_curve=[4.0, 3.0, 2.0, 1.0],
        final_target=None,
        metadata={"nested_nan": {"value": float("nan")}},
    )

    _strict_write_results([trace], tmp_path)

    summary = _strict_json_loads(
        (tmp_path / "summary.json").read_text(encoding="utf-8")
    )
    alg = summary["algorithms"]["stacked_v0301"]
    assert alg["final_target_hit_rate"] is None
    assert alg["mean_target_fraction"] is None

    with (tmp_path / "runs.csv").open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))
    metadata = _strict_json_loads(row["metadata_json"])
    assert metadata["nested_nan"]["value"] is None


def test_duplicate_journal_run_is_rejected(tmp_path: Path):
    path = tmp_path / "progress.jsonl"
    row = {
        "kind": "run",
        "problem_id": "bbob_f001_i71_d02",
        "algorithm": "adaptive_stacked_v035",
        "best_f": 1.0,
    }
    path.write_text(
        json.dumps(row) + "\n" + json.dumps(row) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate scientific run"):
        validate_journal_uniqueness(path)


def test_multiple_completion_records_are_rejected(tmp_path: Path):
    path = tmp_path / "progress.jsonl"
    done = {"kind": "campaign_complete"}
    path.write_text(
        json.dumps(done) + "\n" + json.dumps(done) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple campaign_complete"):
        validate_journal_uniqueness(path)


def test_strict_json_sanitizes_nonfinite_values():
    data = {
        "nan": float("nan"),
        "pos_inf": float("inf"),
        "neg_inf": float("-inf"),
        "nested": [1.0, float("nan")],
        "numpy": np.float64(float("inf")),
    }
    clean = _strict_json_value(data)
    assert clean == {
        "nan": None,
        "pos_inf": None,
        "neg_inf": None,
        "nested": [1.0, None],
        "numpy": None,
    }
    strict_json_dumps(clean)


def _manifest(campaign_id="cid"):
    return {
        "kind": "v035_ablation_manifest",
        "schema": "ablation-manifest/2",
        "campaign_id": campaign_id,
        "config": {
            "functions": [1],
            "dimensions": [2],
            "instances": [71],
            "budget_multiplier": 20,
            "base_seed": 123,
        },
        "arms": {
            "stacked": "stacked_v0301",
            "stacked_fresh_weights": "stacked_fresh_weights_v034",
            "adaptive_stacked": "adaptive_stacked_v035",
        },
        "expected_cases": 1,
        "expected_runs": 3,
    }


def _valid_campaign_records(campaign_id="cid"):
    pid = "bbob_f001_i71_d02"
    seed = 123 + 10000 * 71 + 100 * 1 + 2
    rows = []
    for arm in sorted(EXPECTED_ARMS):
        rows.append({
            "kind": "run",
            "campaign_id": campaign_id,
            "problem_id": pid,
            "algorithm": arm,
            "dimension": 2,
            "budget": 40,
            "seed": seed,
            "evaluations": 40,
            "best_f": 1.0,
            "metadata": {},
        })
    accounting = {
        arm: {
            "attempted": 1,
            "completed": 1,
            "failed": 0,
            "excluded_by_matching": 0,
            "failure_reasons": [],
        }
        for arm in EXPECTED_ARMS
    }
    rows.append({
        "kind": "campaign_complete",
        "campaign_id": campaign_id,
        "completed_runs": 3,
        "matched_runs": 3,
        "failed_cases": {},
        "per_arm_accounting": accounting,
        "setup_failures": [],
    })
    return rows


def _write_campaign(tmp_path: Path, manifest, records):
    (tmp_path / "manifest.json").write_text(
        strict_json_dumps(manifest), encoding="utf-8"
    )
    journal = tmp_path / "progress.jsonl"
    journal.write_text(
        "".join(strict_json_dumps(row) + "\n" for row in records),
        encoding="utf-8",
    )
    return journal


def test_campaign_integrity_accepts_bound_consistent_campaign(tmp_path: Path):
    journal = _write_campaign(tmp_path, _manifest(), _valid_campaign_records())
    result = validate_campaign_integrity(journal)
    assert result["campaign_id"] == "cid"
    assert result["run_records"] == 3


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda rows: rows[0].__setitem__("budget", 41), "budget"),
        (lambda rows: rows[0].__setitem__("seed", 999), "seed"),
        (lambda rows: rows[0].__setitem__("dimension", 3), "dimension"),
        (
            lambda rows: rows[0].__setitem__("campaign_id", "other"),
            "campaign_id",
        ),
        (
            lambda rows: rows[0].__setitem__("algorithm", "other_arm"),
            "unexpected algorithm",
        ),
    ],
)
def test_campaign_integrity_rejects_mixed_or_inconsistent_runs(
    tmp_path: Path, mutation, match
):
    rows = _valid_campaign_records()
    mutation(rows)
    journal = _write_campaign(tmp_path, _manifest(), rows)
    with pytest.raises(ValueError, match=match):
        validate_campaign_integrity(journal)


def test_campaign_integrity_rejects_disjoint_problem_from_other_campaign(
    tmp_path: Path,
):
    rows = _valid_campaign_records()
    foreign = dict(rows[0])
    foreign["problem_id"] = "bbob_f002_i71_d02"
    foreign["algorithm"] = "stacked_v0301"
    rows.insert(-1, foreign)
    rows[-1]["completed_runs"] = 4
    journal = _write_campaign(tmp_path, _manifest(), rows)

    with pytest.raises(ValueError, match="outside the manifest"):
        validate_campaign_integrity(journal)


def test_campaign_integrity_requires_single_final_completion(tmp_path: Path):
    rows = _valid_campaign_records()[:-1]
    journal = _write_campaign(tmp_path, _manifest(), rows)
    with pytest.raises(ValueError, match="exactly one campaign_complete"):
        validate_campaign_integrity(journal)


class _ForcedPolicy:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def reset(self):
        pass

    def update(self, diagnostics, **_kwargs):
        return AdaptiveDecision(
            enable_adaptive_proposal=self.enabled,
            enable_rescue_proposal=False,
            screen_pool_mult=1.0,
            diversity_radius_mult=1.0,
            refinement_top_k_delta=0,
            refinement_maxiter_delta=0,
            exploration_mix=0.15 if self.enabled else 0.0,
            evidence_score=1.0 if self.enabled else 0.0,
            consecutive_evidence=2 if self.enabled else 0,
            cooldown_remaining=0,
            recovering=False,
            proposal_level="mild" if self.enabled else "none",
            reason="test",
        )


class _StubV035Engine(AdaptiveStackedGPBOEngineV035):
    """Run-loop integration harness with model/acquisition work stubbed out."""

    def __init__(self, evaluator, *, adaptive_enabled=True, adaptive_mode="reject"):
        self.space = SimpleNamespace(dim=2)
        self.evaluator = evaluator
        self.seed = 7
        self.screen_device = SimpleNamespace(type="cpu")
        self.record_diagnostics = False
        self.history = []
        self.x01_history = []
        self.margin_history = []
        self.events = []
        self.diagnostic_history = []
        self.policy_history = []
        self.arbiter_history = []
        self.weight_history = []
        self.stacking_weight_rbf = 0.5
        self.policy_controller = _ForcedPolicy(adaptive_enabled)
        self.adaptive_mode = adaptive_mode
        self._rng_state = 0
        self.identity_rng_seen = []
        self.fit_diagnostics = {
            "adaptive_policy_updates": 0,
            "adaptive_proposals_generated": 0,
            "adaptive_proposals_accepted": 0,
            "adaptive_proposals_rejected": 0,
            "adaptive_rescue_search_attempts": 0,
            "adaptive_rescue_proposals": 0,
            "adaptive_rescue_accepted": 0,
            "adaptive_forced_refits": 0,
            "identity_proposals": 0,
            "adaptive_proposal_generation_failures": 0,
            "adaptive_exploration_starts_capped": 0,
            "adaptive_exploration_mix_disabled": 0,
            "severe_stagnation_pulses": 0,
            "stagnation_pulses": 0,
            "refinement_selected": 0,
            "discrete_selected": 0,
        }
        self.timings = {"total_iteration_s": 0.0}

    def _evaluate01(self, x01):
        x01 = np.asarray(x01, dtype=float).reshape(-1)
        score, feasible, metadata = self.evaluator(x01)
        result = ExperimentResult(
            x=x01.copy(),
            score=float(score),
            feasible=bool(feasible),
            metadata=dict(metadata),
        )
        self.history.append(result)
        self.x01_history.append(x01.copy())
        self.margin_history.append([])
        return result

    def _best_feasible_score(self):
        rows = [r.score for r in self.history if r.feasible]
        if not rows:
            rows = [r.score for r in self.history]
        return max(rows)

    def _fit_pair(self, optimize):
        return object(), object()

    def _update_stacking_weight(self, rbf_model, matern_model):
        return None

    def _build_acquisition(self, model):
        return object(), "LogEI"

    def _build_stacked_acquisition(self, rbf_model, matern_model):
        return object(), "StackedLogEI"

    def _torch_rng_snapshot(self):
        return int(self._rng_state)

    def _torch_rng_restore(self, snap):
        self._rng_state = int(snap)


def _fake_parent_proposal(self, *args, **kwargs):
    tag = kwargs["tag"]
    step = int(kwargs["step"])

    if tag == "identity":
        self.identity_rng_seen.append(int(self._rng_state))
        x = np.array([0.20 + 0.01 * step, 0.30], dtype=float)
        return ProposalView(
            x01=x,
            source="identity_discrete",
            mixture_acq=1.0,
            rbf_acq=1.0,
            matern_acq=1.0,
        )

    # Simulate RNG consumption inside an optional adaptive search.
    self._rng_state += 1000 + step
    if self.adaptive_mode == "fail":
        raise RuntimeError("injected adaptive generation failure")

    return ProposalView(
        x01=np.array([0.80, 0.80], dtype=float),
        source="adaptive_discrete",
        mixture_acq=0.0,  # rejected by consensus arbiter
        rbf_acq=0.0,
        matern_acq=0.0,
    )


def _run_stub(monkeypatch, *, enabled=True, mode="reject", stacked_mode="fast"):
    from src.engcore.adaptive_stacked_engine import AdaptiveStackedGPBOEngine

    monkeypatch.setattr(
        AdaptiveStackedGPBOEngine,
        "_generate_search_proposal",
        _fake_parent_proposal,
    )

    calls = {"n": 0}

    def evaluator(x):
        calls["n"] += 1
        score = -float(np.sum(np.asarray(x, dtype=float) ** 2))
        return score, True, {}

    engine = _StubV035Engine(
        evaluator,
        adaptive_enabled=enabled,
        adaptive_mode=mode,
    )
    result = engine.run(
        initial_trials=2,
        smart_trials=3,
        record_diagnostics=False,
        verbose=False,
        **get_stacked_mode(stacked_mode),
    )
    return engine, result, calls["n"]


@pytest.mark.parametrize("stacked_mode", ["fast", "balanced", "quality"])
def test_v035_run_loop_preserves_exact_budget(monkeypatch, stacked_mode):
    engine, result, calls = _run_stub(
        monkeypatch,
        enabled=True,
        mode="reject",
        stacked_mode=stacked_mode,
    )
    assert calls == 5
    assert result["trials_run"] == 5
    assert len(engine.history) == 5


def test_adaptive_generation_failure_falls_back_to_identity_one_eval_per_step(
    monkeypatch,
):
    engine, result, calls = _run_stub(
        monkeypatch, enabled=True, mode="fail"
    )

    assert calls == 5
    assert result["trials_run"] == 5
    assert engine.fit_diagnostics["adaptive_proposal_generation_failures"] == 3
    failures = [
        e for e in engine.events
        if e.get("event") == "adaptive_proposal_generation_failure"
    ]
    assert len(failures) == 3
    assert all(e["fallback"] == "identity" for e in failures)
    iterations = [e for e in engine.events if e.get("event") == "iteration"]
    assert len(iterations) == 3
    assert all(e["choose_adaptive"] is False for e in iterations)
    assert all(e["source"].startswith("identity") for e in iterations)


@pytest.mark.parametrize("adaptive_mode", ["reject", "fail"])
def test_optional_adaptive_path_does_not_contaminate_future_rng_state(
    monkeypatch,
    adaptive_mode,
):
    baseline, _result, _calls = _run_stub(
        monkeypatch, enabled=False, mode="reject"
    )
    baseline_seen = list(baseline.identity_rng_seen)
    baseline_final = baseline._rng_state

    treated, _result, _calls = _run_stub(
        monkeypatch, enabled=True, mode=adaptive_mode
    )

    assert treated.identity_rng_seen == baseline_seen
    assert treated._rng_state == baseline_final


def test_rescue_proposal_still_cannot_bypass_arbiter():
    identity = ProposalView(
        np.array([0.1, 0.2]), "identity", 1.0, 1.0, 1.0
    )
    weak_rescue = ProposalView(
        np.array([0.8, 0.8]),
        "adaptive_rescue",
        0.1,
        0.1,
        0.1,
        is_rescue=True,
    )
    chosen, decision = arbitrate_proposals(
        identity, weak_rescue, adaptive_enabled=True
    )
    assert decision.choose_adaptive is False
    np.testing.assert_allclose(chosen.x01, identity.x01)
