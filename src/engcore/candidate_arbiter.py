"""
Robust baseline-vs-adaptive candidate arbiter (V0.3.3).

identity_proposal:
  What stacked_v0301 search logic would propose from the CURRENT
  adaptive-run observations using baseline search settings.
  (Not a counterfactual of an alternate full stacked trajectory.)

Adaptive may replace identity only under model-consensus dominance.
No benchmark metadata, no objective lookahead, no extra f(x).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


# Floating-point comparison only — not a tuned policy threshold.
ACQ_TOL = 1e-12


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


def components_disagree(
    id_rbf: float,
    id_mat: float,
    ad_rbf: float,
    ad_mat: float,
    *,
    tol: float = ACQ_TOL,
) -> bool:
    """
    Strong disagreement: one component prefers adaptive, the other identity,
    beyond numerical tolerance.
    """
    dr = float(ad_rbf) - float(id_rbf)
    dm = float(ad_mat) - float(id_mat)
    return bool(
        (dr > tol and dm < -tol)
        or (dr < -tol and dm > tol)
    )


def arbitrate_proposals(
    identity: ProposalView,
    adaptive: ProposalView | None,
    *,
    adaptive_enabled: bool,
    tol: float = ACQ_TOL,
) -> tuple[ProposalView, ArbiterDecision]:
    """
    Conservative consensus rule:

    Accept adaptive only if ALL hold:
      1. adaptive proposal generation is enabled by policy evidence
      2. adaptive is not worse than identity on BOTH GP components (tol)
      3. adaptive is strictly better on at least one GP component
      4. stacked mixture also prefers adaptive
      5. GP components do not strongly disagree

    Rescue proposals use the same rule (no automatic priority).
    """
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
        atol=tol,
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
        tol=tol,
    )
    if disagree:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="component_disagreement",
            component_disagreement=True,
            executed_source="identity",
        )

    # (1)+(2 conceptually via enabled flag already): not worse on both
    if (
        adaptive.rbf_acq < identity.rbf_acq - tol
        or adaptive.matern_acq < identity.matern_acq - tol
    ):
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="not_pareto_nondominated",
            component_disagreement=False,
            executed_source="identity",
        )

    # Strictly better under at least one component
    strict = (
        adaptive.rbf_acq > identity.rbf_acq + tol
        or adaptive.matern_acq > identity.matern_acq + tol
    )
    if not strict:
        return identity, ArbiterDecision(
            choose_adaptive=False,
            reason="no_strict_component_gain",
            component_disagreement=False,
            executed_source="identity",
        )

    # Mixture must also prefer adaptive
    if adaptive.mixture_acq <= identity.mixture_acq + tol:
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
