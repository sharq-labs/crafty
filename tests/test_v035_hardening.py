from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.engcore.adaptive_stacked_engine_v035 import (
    AdaptiveStackedGPBOEngineV035,
)
from src.engcore.v035_ablation_analysis import (
    _strict_json_value,
    validate_journal_uniqueness,
)
from src.engcore.v035_ablation_arena import _guard_empty_output


def test_exploration_starts_enter_early_refinement_slots():
    engine = object.__new__(AdaptiveStackedGPBOEngineV035)
    engine.space = SimpleNamespace(dim=2)

    starts = np.array(
        [
            [0.01, 0.01],
            [0.10, 0.10],
            [0.20, 0.20],
            [0.30, 0.30],
            [0.40, 0.40],
            [0.50, 0.50],
        ],
        dtype=float,
    )
    scores = np.arange(6.0, 0.0, -1.0)

    mixed, mixed_scores = engine._mix_exploration_starts(
        starts,
        scores,
        mix=0.30,
        seed=123,
    )

    # Best acquisition candidate stays fixed.
    np.testing.assert_allclose(mixed[0], starts[0])
    assert mixed_scores[0] == scores[0]

    # top_k=6, mix=.30 => two explorers. They must be positions 1 and 2,
    # which are inside the registered fast-mode refinement slice [:3].
    assert not np.allclose(mixed[1], starts[1])
    assert not np.allclose(mixed[2], starts[2])
    assert mixed_scores[1] == -np.inf
    assert mixed_scores[2] == -np.inf

    # Non-replaced tail stays intact.
    np.testing.assert_allclose(mixed[3:], starts[3:])


def test_nonempty_campaign_output_is_rejected(tmp_path: Path):
    out = tmp_path / "campaign"
    out.mkdir()
    (out / "progress.jsonl").write_text("{}\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="output directory is not empty"):
        _guard_empty_output(out)


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
    }
    clean = _strict_json_value(data)
    assert clean == {
        "nan": None,
        "pos_inf": None,
        "neg_inf": None,
        "nested": [1.0, None],
    }
    json.dumps(clean, allow_nan=False)
