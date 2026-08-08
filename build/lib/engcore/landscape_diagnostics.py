"""
Online landscape / search diagnostics.

Black-box safe: uses only evaluated X, objective/score values, bounds/dim,
budget state, and already-computed model stacking diagnostics.

Never uses benchmark identity, known optima, or COCO metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class LandscapeDiagnostics:
    n_obs: int
    dimension: int
    remaining_budget_fraction: float
    best_score: float
    evaluations_since_improve: int
    recent_improvement_rate: float
    normalized_improvement_velocity: float
    stagnation_score: float
    sample_diversity: float
    incumbent_locality: float
    exploration_coverage: float
    model_agreement: float
    model_error_proxy: float
    model_reliability: float
    weight_rbf: float
    weight_matern: float

    def as_dict(self) -> dict:
        return asdict(self)


def _finite_or(value: float, default: float) -> float:
    value = float(value)
    if not np.isfinite(value):
        return float(default)
    return value


def _clip01(value: float) -> float:
    return float(np.clip(_finite_or(value, 0.0), 0.0, 1.0))


def compute_landscape_diagnostics(
    *,
    x01_history,
    scores,
    best_score,
    evaluations_since_improve,
    total_budget,
    dimension,
    weight_rbf=0.5,
    weight_history=None,
    recent_window=8,
    locality_radius=0.08,
) -> LandscapeDiagnostics:
    """
    Derive inexpensive online features from observations.

    scores: higher-is-better internal scores (Validation Lab uses -f).
    Conservative defaults are returned when N is tiny.
    """
    X = np.asarray(x01_history, dtype=np.float64)
    y = np.asarray(scores, dtype=np.float64).reshape(-1)
    n = int(y.size)
    dim = int(dimension)
    budget = max(int(total_budget), 1)
    window = max(2, int(recent_window))

    if X.ndim != 2:
        X = np.zeros((0, dim), dtype=np.float64)
    if n == 0:
        return LandscapeDiagnostics(
            n_obs=0,
            dimension=dim,
            remaining_budget_fraction=1.0,
            best_score=float("-inf"),
            evaluations_since_improve=0,
            recent_improvement_rate=0.0,
            normalized_improvement_velocity=0.0,
            stagnation_score=0.0,
            sample_diversity=0.0,
            incumbent_locality=0.0,
            exploration_coverage=0.0,
            model_agreement=0.5,
            model_error_proxy=0.5,
            model_reliability=0.0,
            weight_rbf=0.5,
            weight_matern=0.5,
        )

    remaining = max(budget - n, 0) / float(budget)
    since = int(max(0, evaluations_since_improve))

    # Recent improvement rate: fraction of last-window steps that improved best.
    if n >= 2:
        best_curve = np.maximum.accumulate(y)
        tail = best_curve[-(window + 1) :]
        if len(tail) >= 2:
            improves = np.diff(tail) > 1e-12
            recent_improvement_rate = float(np.mean(improves))
            span = float(abs(tail[-1] - tail[0]))
            y_scale = float(
                max(
                    np.std(y),
                    abs(tail[-1]),
                    1e-12,
                )
            )
            normalized_improvement_velocity = (
                span / (y_scale * max(len(tail) - 1, 1))
            )
        else:
            recent_improvement_rate = 0.0
            normalized_improvement_velocity = 0.0
    else:
        recent_improvement_rate = 0.0
        normalized_improvement_velocity = 0.0

    # Stagnation in [0,1], budget-aware.
    stag_den = max(6.0, 0.15 * budget)
    stagnation_score = _clip01(since / stag_den)

    # Geometry: diversity of recent points and locality around incumbent.
    if n >= 2:
        recent_X = X[-min(n, window) :]
        diffs = recent_X[:, None, :] - recent_X[None, :, :]
        dists = np.sqrt(np.sum(diffs * diffs, axis=-1))
        iu = np.triu_indices(len(recent_X), k=1)
        mean_dist = float(np.mean(dists[iu])) if iu[0].size else 0.0
        sample_diversity = _clip01(
            mean_dist / max(np.sqrt(dim), 1e-12)
        )

        best_idx = int(np.argmax(y))
        incumbent = X[best_idx]
        recent_to_inc = np.linalg.norm(
            recent_X - incumbent[None, :],
            axis=1,
        )
        incumbent_locality = _clip01(
            float(
                np.mean(
                    recent_to_inc <= float(locality_radius)
                )
            )
        )

        span = np.ptp(recent_X, axis=0)
        exploration_coverage = _clip01(float(np.mean(span)))
    else:
        sample_diversity = 0.0
        incumbent_locality = 1.0
        exploration_coverage = 0.0

    w_rbf = _clip01(float(weight_rbf))
    w_mat = _clip01(1.0 - w_rbf)

    # Reliability proxy from scale-robust inter-model consistency rather than
    # absolute predictive log density. Multiplying the objective by a constant
    # can shift both mean log densities by a common offset; their difference
    # remains the safer signal.
    model_agreement = 0.5
    model_error_proxy = 0.5
    model_reliability = 0.0

    if weight_history:
        last = weight_history[-1]
        lp_a = float(last.get("mean_logp_rbf", np.nan))
        lp_b = float(last.get("mean_logp_matern", np.nan))
        if np.isfinite(lp_a) and np.isfinite(lp_b):
            gap = abs(lp_a - lp_b)
            model_agreement = _clip01(1.0 / (1.0 + gap))

            recent_weights = [
                float(row.get("weight_rbf", np.nan))
                for row in weight_history[-5:]
            ]
            recent_weights = [
                value for value in recent_weights
                if np.isfinite(value)
            ]
            weight_volatility = (
                float(np.std(recent_weights)) * 2.0
                if len(recent_weights) >= 2
                else 0.0
            )
            disagreement = 1.0 - model_agreement
            model_error_proxy = _clip01(
                max(disagreement, weight_volatility)
            )
            model_reliability = _clip01(
                1.0 - model_error_proxy
            )

        # Near-floor stacking weights indicate effective member collapse and
        # reduce trust in model-consensus adaptation.
        floor_dist = min(w_rbf, w_mat)
        if floor_dist <= 0.11:
            model_reliability *= 0.7
            model_error_proxy = _clip01(
                max(model_error_proxy, 0.5)
            )

    return LandscapeDiagnostics(
        n_obs=n,
        dimension=dim,
        remaining_budget_fraction=_clip01(remaining),
        best_score=_finite_or(best_score, float("-inf")),
        evaluations_since_improve=since,
        recent_improvement_rate=_clip01(recent_improvement_rate),
        normalized_improvement_velocity=_finite_or(
            normalized_improvement_velocity,
            0.0,
        ),
        stagnation_score=stagnation_score,
        sample_diversity=sample_diversity,
        incumbent_locality=incumbent_locality,
        exploration_coverage=exploration_coverage,
        model_agreement=model_agreement,
        model_error_proxy=model_error_proxy,
        model_reliability=model_reliability,
        weight_rbf=w_rbf,
        weight_matern=w_mat,
    )
