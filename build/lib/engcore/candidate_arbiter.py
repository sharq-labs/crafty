"""
Robust baseline-vs-adaptive candidate arbiter.

identity_proposal:
  What stacked search logic would propose from the CURRENT adaptive-run
  observations using baseline search settings. This is not a counterfactual
  of an alternate full stacked trajectory.

Adaptive may replace identity only under model-consensus dominance.
No benchmark metadata, no objective lookahead, no extra f(x).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


# Acquisition comparisons need a tolerance larger than raw floating epsilon.
# Log-acquisition values can vary substantially in magnitude, so use both an
# absolute floor and a relative component. These are numerical safety margins,
# not benchmark-specific policy thresholds.
ACQ_ABS_TOL = 1e-10
ACQ_REL_TOL = 1e-7
X_ATOL = 1e-12


@dataclass(frozen=True)
class ProposalView:
    """One unevaluated candidate proposal."""

    x01: np.ndarray
    source: str
    mixture_acq: float
    rbf_acq: float
    matern_acq: float
    is_rescue: bool = False

    def as_dict(self) -> dict:
        d = asdict(self)
        d["x01"] = np.asarray(self.x01, dtype=float).tolist()
        return d


@dataclass(frozen=True)
class ArbiterDecision:
    choose_adaptive: bool
    reason: str
    component_disagreement: bool
    executed_source: str  # "identity" | "adaptive"

    def as_dict(self) -> dict:
        return asdict(self)


def _finite(v: float) -> bool:
    return bool(np.isfinite(v))


def _comparison_tol(
    a: float,
    b: float,
    *,
    abs_tol: float = ACQ_ABS_TOL,
    rel_tol: float = ACQ_REL_TOL,
) -> float:
    scale = max(1.0, abs(float(a)), abs(float(b)))
    return float(max(float(abs_tol), float(rel_tol) * scale))


def components_disagree(
    id_rbf: float,
    id_mat: float,
    ad_rbf: float,
    ad_mat: float,
    *,
    tol: float | None = None,
    abs_tol: float = ACQ_ABS_TOL,
    rel_tol: float = ACQ_REL_TOL,
) -> bool:
    """
    Strong disagreement: one component prefers adaptive, the other identity,
    beyond scale-aware numerical tolerance.

    ``tol`` remains as a compatibility override for older tests/callers. When
    supplied it is treated as an absolute-only tolerance.
    """
    if tol is not None:
        abs_tol = float(tol)
        rel_tol = 0.0

    dr = float(ad_rbf) - float(id_rbf)
    dm = float(ad_mat) - float(id_mat)
    tr = _comparison_tol(
        ad_rbf, id_rbf, abs_tol=abs_tol, rel_tol=rel_tol
    )
    tm = _comparison_tol(
        ad_mat, id_mat, abs_tol=abs_tol, rel_tol=rel_tol
    )
    return bool(
        (dr > tr and dm < -tm)
        or (dr < -tr and dm > tm)
    )


def arbitrate_proposals(
    identity: ProposalView,
    adaptive: ProposalView | None,
    *,
    adaptive_enabled: bool,
    tol: float | None = None,
    abs_tol: float = ACQ_ABS_TOL,
    rel_tol: float = ACQ_REL_TOL,
) -> tuple[ProposalView, ArbiterDecision]:
    """
    Conservative consensus rule.

    Accept adaptive only if ALL hold:
      1. adaptive proposal generation is enabled by policy evidence;
      2. adaptive is not materially worse than identity on BOTH GP members;
      3. adaptive is materially better on at least one GP member;
      4. stacked mixture also materially prefers adaptive;
      5. GP components do not strongly disagree.

    Rescue proposals use the same rule and receive no automatic priority.
    """
    if tol is not None:
        abs_tol = float(tol)
        rel_tol = 0.0

    if adaptive is None or not adaptive_enabled:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="identity_default",
            component_disagreement=False,
            executed_source="identity",
        )

    if np.allclose(
        np.asarray(identity.x01, dtype=float),
        np.asarray(adaptive.x01, dtype=float),
        rtol=0.0,
        atol=X_ATOL,
    ):
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="identical_proposals",
            component_disagreement=False,
            executed_source="identity",
        )

    scores = (
        identity.mixture_acq,
        identity.rbf_acq,
        identity.matern_acq,
        adaptive.mixture_acq,
        adaptive.rbf_acq,
        adaptive.matern_acq,
    )
    if not all(_finite(v) for v in scores):
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="non_finite_acquisition",
            component_disagreement=False,
            executed_source="identity",
        )

    disagree = components_disagree(
        identity.rbf_acq,
        identity.matern_acq,
        adaptive.rbf_acq,
        adaptive.matern_acq,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    if disagree:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="component_disagreement",
            component_disagreement=True,
            executed_source="identity",
        )

    rbf_tol = _comparison_tol(
        adaptive.rbf_acq,
        identity.rbf_acq,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    mat_tol = _comparison_tol(
        adaptive.matern_acq,
        identity.matern_acq,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    mix_tol = _comparison_tol(
        adaptive.mixture_acq,
        identity.mixture_acq,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )

    if (
        adaptive.rbf_acq < identity.rbf_acq - rbf_tol
        or adaptive.matern_acq < identity.matern_acq - mat_tol
    ):
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="not_pareto_nondominated",
            component_disagreement=False,
            executed_source="identity",
        )

    strict = (
        adaptive.rbf_acq > identity.rbf_acq + rbf_tol
        or adaptive.matern_acq > identity.matern_acq + mat_tol
    )
    if not strict:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="no_material_component_gain",
            component_disagreement=False,
            executed_source="identity",
        )

    if adaptive.mixture_acq <= identity.mixture_acq + mix_tol:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="mixture_not_prefer_adaptive",
            component_disagreement=False,
            executed_source="identity",
        )

    reason = (
        "consensus_accept_rescue"
        if adaptive.is_rescue
        else "consensus_accept"
    )
    return adaptive, ArbiterDecision(
        choose_adaptive=True,
        reason=reason,
        component_disagreement=False,
        executed_source="adaptive",
    )
