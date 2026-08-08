"""Core V0.3 runner integration for incremental campaign persistence.

The decision/evidence loop is inherited unchanged from :class:`CampaignRunner`.
Only the checkpoint seam is replaced so persistence no longer constructs and
retains a full-history ``CampaignCheckpoint`` on every durable transition.
"""

from __future__ import annotations

from typing import Any

from .persistence import IncrementalCheckpointStore
from .runner import CampaignRunner


class IncrementalCampaignRunner(CampaignRunner):
    """CampaignRunner with V0.3 incremental checkpoint persistence.

    All scientific, decision, liveness, stopping, execution, assurance and
    budget behavior remains in the existing runner.  The override is purposely
    narrow: when the runner asks for a durable checkpoint, current state is
    handed directly to :class:`IncrementalCheckpointStore.save_state` so only
    journal deltas and one compact checkpoint are persisted.
    """

    def __init__(self, *args: Any, checkpoints=None, **kwargs: Any) -> None:
        super().__init__(
            *args,
            checkpoints=checkpoints or IncrementalCheckpointStore(),
            **kwargs,
        )
        if not isinstance(self._checkpoints, IncrementalCheckpointStore):
            raise TypeError(
                "IncrementalCampaignRunner requires IncrementalCheckpointStore"
            )

    def _checkpoint(self):
        return self._checkpoints.save_state(
            run=self._run,
            events=self._events,
            budget=self._budget,
            effects=self._effects,
            plan=self._plan,
            obligation_state=dict(self._obligation_state),
        )

    def restore_latest(self):
        """Adopt the latest committed checkpoint and replay nothing."""
        checkpoint = self._checkpoints.latest()
        if checkpoint is None:
            raise ValueError("incremental checkpoint store is empty")
        return super().restore(checkpoint)
