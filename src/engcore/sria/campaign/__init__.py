"""SRIA V0.1 M5 — the bounded sequential campaign loop.

Connects the frozen M1–M4 components into a research campaign that can take a
step, learn from it, and take a different next step *through the formal
pipeline* rather than around it.

    snapshot -> generate -> feasibility -> M4 score -> recommend ONE action
             -> execute (simulation only) -> ScientificResult
             -> candidate Evidence -> Critics -> Arbiter -> AdmissionAuthority
             -> Gateway -> belief
             -> calibration memory (computational telemetry only)
             -> NEW snapshot -> repeat

What this is not, stated plainly because the words are easy to over-claim:

* **Not an autonomous agent.** Bounded iterations, deterministic, no background
  execution, no self-modification, no automated hypothesis generation.
* **Not a research-mode state machine.** :class:`ExecutionState` describes what
  the runner is doing — ``EXECUTING``, ``ASSESSING`` — never what the campaign
  is scientifically about. The six M4 action families remain peer generators;
  there is no ``current_mode`` and no family that follows another.
* **Not an owner of scientific truth.** The runner orchestrates the path from
  result to belief; it never writes belief. Only the Arbiter ->
  AdmissionAuthority -> Gateway chain does, exactly as M1/M3 froze it.
* **Not a certifier.** ``STOP_PROPOSAL`` remains an economic statement — "no
  scored candidate looks worth its cost". Whether a campaign is scientifically
  finished is the Arbiter's to say, and :class:`StopReviewOutcome` returns
  ``STOP_NOT_ASSESSED`` rather than inventing an answer.

Module layout is deliberately several small pieces rather than one
``CampaignBrain``: :mod:`state`, :mod:`events`, :mod:`budget`,
:mod:`checkpoint`, :mod:`executor`, :mod:`liveness`, :mod:`stopping`,
:mod:`runner`.
"""

from __future__ import annotations

from .budget import BudgetCharge, BudgetExhausted, BudgetLedger
from .checkpoint import (
    CampaignCheckpoint,
    CheckpointStore,
    EffectLedger,
    IterationPlan,
    ResumeViolation,
)
from .events import (
    CampaignEvent,
    CampaignEventLog,
    CampaignEventType,
    ChainBroken,
)
from .executor import (
    ExecutionRecord,
    MemberExecution,
    SimulationExecutor,
    aggregate_member_cost,
    require_simulation,
)
from .liveness import (
    LIVENESS_POLICY_ID,
    LivenessRuling,
    LivenessStatus,
    ValidationLivenessPolicy,
    ValidationTarget,
    validation_targets,
)
from .runner import (
    AssessmentBundle,
    CampaignHarness,
    CampaignRunner,
    deterministic_clock,
)
from .state import (
    RESEARCH_MODE_VOCABULARY,
    TERMINAL_STATES,
    CampaignRun,
    ExecutionState,
    IterationRecord,
    PauseReason,
)
from .stopping import (
    STOPPING_REVIEW_VERSION,
    ArbiterStoppingReview,
    StopProposal,
    StopReview,
    StopReviewOutcome,
    StoppingCriterion,
    StoppingCriterionEvaluator,
)

SRIA_CAMPAIGN_VERSION = "0.1.0-m5-campaign-loop"

__all__ = [
    "SRIA_CAMPAIGN_VERSION",
    # state
    "CampaignRun",
    "ExecutionState",
    "IterationRecord",
    "PauseReason",
    "TERMINAL_STATES",
    "RESEARCH_MODE_VOCABULARY",
    # events
    "CampaignEvent",
    "CampaignEventLog",
    "CampaignEventType",
    "ChainBroken",
    # budget
    "BudgetLedger",
    "BudgetCharge",
    "BudgetExhausted",
    # checkpoint
    "CampaignCheckpoint",
    "CheckpointStore",
    "EffectLedger",
    "IterationPlan",
    "ResumeViolation",
    # executor
    "SimulationExecutor",
    "ExecutionRecord",
    "MemberExecution",
    "require_simulation",
    "aggregate_member_cost",
    # validation liveness
    "ValidationLivenessPolicy",
    "LivenessRuling",
    "LivenessStatus",
    "ValidationTarget",
    "validation_targets",
    "LIVENESS_POLICY_ID",
    # stopping
    "StopProposal",
    "StopReview",
    "StopReviewOutcome",
    "ArbiterStoppingReview",
    "StoppingCriterion",
    "StoppingCriterionEvaluator",
    "STOPPING_REVIEW_VERSION",
    # runner
    "CampaignRunner",
    "CampaignHarness",
    "AssessmentBundle",
    "deterministic_clock",
]
