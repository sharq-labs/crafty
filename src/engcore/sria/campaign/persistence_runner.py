"""Core V0.3 runner integration for incremental campaign persistence.

The decision/evidence loop is inherited unchanged from :class:`CampaignRunner`.
Only the checkpoint seam is replaced so persistence no longer constructs and
retains a full-history ``CampaignCheckpoint`` on every durable transition.
"""

from __future__ import annotations

from typing import Any

from .budget import BudgetLedger
from .checkpoint import EffectLedger
from .events import CampaignEventLog
from .persistence import IncrementalCheckpointStore
from .runner import CampaignRunner


class IncrementalCampaignRunner(CampaignRunner):
    """CampaignRunner with V0.3 incremental checkpoint persistence.

    All scientific, decision, liveness, stopping, execution, assurance and
    budget behavior remains in the existing runner. The override is purposely
    narrow: when the runner asks for a durable checkpoint, current state is
    handed directly to :class:`IncrementalCheckpointStore.save_state` so only
    journal deltas and one compact checkpoint are persisted.
    """

    def __init__(self, *args: Any, checkpoints=None, **kwargs: Any) -> None:
        store = checkpoints if checkpoints is not None else IncrementalCheckpointStore()
        if not isinstance(store, IncrementalCheckpointStore):
            raise TypeError(
                "IncrementalCampaignRunner requires IncrementalCheckpointStore"
            )
        super().__init__(*args, checkpoints=store, **kwargs)

    def _checkpoint(self):
        return self._checkpoints.save_state(
            run=self._run,
            events=self._events,
            budget=self._budget,
            effects=self._effects,
            plan=self._plan,
            obligation_state=dict(self._obligation_state),
        )

    def restore(self, checkpoint):
        """Adopt materialized V0.3 state without replay or re-derivation.

        This mirrors the frozen runner restore seam, while also preserving the
        executor-enforced budget-cap declaration that V0.3 persists explicitly.
        """
        self._run = checkpoint.run
        self._events = CampaignEventLog(
            checkpoint.run.run_id, checkpoint.events.events
        )
        self._budget = BudgetLedger(
            total_budget=checkpoint.budget.total_budget,
            reserved_validation_budget=checkpoint.budget.reserved_validation_budget,
            charges=checkpoint.budget.charges,
            cost_unit=checkpoint.budget.cost_unit,
            enforced_cap=checkpoint.budget.enforced_cap,
            enforced_cap_source=checkpoint.budget.enforced_cap_source,
        )
        self._effects = EffectLedger(applied=dict(checkpoint.effects.applied))
        self._plan = checkpoint.plan
        self._obligation_state = dict(checkpoint.obligation_state)
        if self._plan is not None:
            self._recommendations[self._plan.recommendation.recommendation_id] = (
                self._plan.recommendation
            )
            self._snapshots[self._plan.iteration] = self._plan.snapshot
        return self._run

    def restore_latest(self):
        """Adopt the latest committed checkpoint and replay nothing."""
        checkpoint = self._checkpoints.latest()
        if checkpoint is None:
            raise ValueError("incremental checkpoint store is empty")
        return self.restore(checkpoint)
