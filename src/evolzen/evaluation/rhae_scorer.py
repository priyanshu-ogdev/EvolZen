"""RHAE-style (Relative Human Action Efficiency) scoring (Phase 2.4).

Modeled on ARC-AGI-3's own metric: penalizes wasted exploratory actions, not just eventual
correctness, since the field's benchmark treats *how much interaction it takes to learn
something new* as the actual measure of intelligence, not raw eventual accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RHAEResult:
    system_actions: int
    human_reference_actions: int
    solved: bool

    @property
    def score(self) -> float:
        """RHAE score in [0, 1+]. 1.0 means the system matched the human reference exactly;
        > 1.0 means the system was *more* action-efficient than the human reference."""
        if not self.solved or self.system_actions == 0:
            return 0.0
        return self.human_reference_actions / self.system_actions


class RHAEScorer:
    """Aggregates RHAEResults across an evaluation round into a single reportable score."""

    def __init__(self) -> None:
        self._results: list[RHAEResult] = []

    def record(self, result: RHAEResult) -> None:
        self._results.append(result)

    def mean_rhae(self) -> float:
        if not self._results:
            return 0.0
        return sum(r.score for r in self._results) / len(self._results)

    def solve_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if r.solved) / len(self._results)
