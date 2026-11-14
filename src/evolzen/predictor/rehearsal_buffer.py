"""Deployment-experience rehearsal buffer and continual-learning metrics (Phase 2.1).

Following CLaaS (arXiv:2606.05559) and CLEAR (Rolnick et al., NeurIPS 2019, arXiv:1811.11682):
mixing replayed real (situation -> outcome) pairs from actual deployment into every policy-gradient
update is the default continual-learning safeguard for the planner. Continual learning metrics
formalize backward transfer, forward transfer, and catastrophic forgetting following Wang et al.
(2024, IEEE TPAMI, DOI:10.1109/TPAMI.2024.3367329) and Kirkpatrick et al. (PNAS 2017,
DOI:10.1073/pnas.1611835114).

Empirical retention and transfer curves remain untested until Phase 2.1 benchmarks are
executed on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

import random
from collections import deque
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from evolzen.schemas.transition import Transition

if TYPE_CHECKING:
    from evolzen.storage.transition_log import TransitionLogStore


class RehearsalBuffer:
    """Fixed-capacity FIFO buffer of real transitions, sampled during training updates."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._buffer: deque[Transition] = deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def add(self, transition: Transition) -> None:
        """Add a single verified transition to the rehearsal buffer."""
        self._buffer.append(transition)

    def extend(self, transitions: Sequence[Transition]) -> None:
        """Add multiple verified transitions to the rehearsal buffer."""
        for t in transitions:
            self._buffer.append(t)

    def clear(self) -> None:
        """Clear all transitions from the rehearsal buffer."""
        self._buffer.clear()

    def sample(self, batch_size: int, rng: random.Random | None = None) -> list[Transition]:
        """Sample uniformly at random without replacement from the buffer."""
        if batch_size > len(self._buffer):
            raise ValueError(
                f"Requested batch_size={batch_size} exceeds buffer size={len(self._buffer)}"
            )
        buf_list = list(self._buffer)
        if rng is not None:
            return rng.sample(buf_list, batch_size)
        return random.sample(buf_list, batch_size)

    def load_from_store(
        self,
        store: TransitionLogStore,
        max_records: int | None = None,
        run_id: str | None = None,
        branch_id: str | None = None,
    ) -> int:
        """Stream historical transitions from DuckDB TransitionLogStore into the buffer.

        Returns the number of transitions actually added.
        """
        transitions = store.list_transitions(run_id=run_id, branch_id=branch_id)
        if max_records is not None and max_records > 0:
            transitions = transitions[-max_records:]
        self.extend(transitions)
        return len(transitions)

    def sample_clear_batch(
        self,
        new_transitions: Sequence[Transition],
        total_batch_size: int,
        replay_ratio: float = 0.5,
        rng: random.Random | None = None,
    ) -> list[Transition]:
        """CLEAR mixed on-policy / off-policy batch sampling (Rolnick et al., NeurIPS 2019).

        Mixes incoming on-policy transitions with historical off-policy replay according
        to `replay_ratio` in [0.0, 1.0].
        """
        if total_batch_size <= 0:
            return []
        if not new_transitions and not self._buffer:
            return []

        ratio = max(0.0, min(1.0, replay_ratio))
        n_replay_target = int(total_batch_size * ratio)
        n_new_target = total_batch_size - n_replay_target

        n_replay = min(n_replay_target, len(self._buffer))
        n_new = min(n_new_target, len(new_transitions))

        # Re-balance if one partition has insufficient records
        if n_replay < n_replay_target:
            n_new = min(len(new_transitions), total_batch_size - n_replay)
        elif n_new < n_new_target:
            n_replay = min(len(self._buffer), total_batch_size - n_new)

        sampled_replay: list[Transition] = []
        if n_replay > 0:
            sampled_replay = self.sample(n_replay, rng=rng)

        sampled_new: list[Transition] = []
        if n_new > 0:
            new_list = list(new_transitions)
            if rng is not None:
                sampled_new = rng.sample(new_list, n_new) if n_new <= len(new_list) else new_list
            else:
                sampled_new = random.sample(new_list, n_new) if n_new <= len(new_list) else new_list

        combined = sampled_replay + sampled_new
        if rng is not None:
            rng.shuffle(combined)
        else:
            random.shuffle(combined)
        return combined

    def __len__(self) -> int:
        return len(self._buffer)


class ContinualMetricsTracker:
    """Tracks longitudinal transfer, backward transfer, and catastrophic forgetting.

    Implements formal evaluation protocols from Wang et al. (IEEE TPAMI 2024,
    DOI:10.1109/TPAMI.2024.3367329).

    Matrix R[i, j] denotes the performance on task/context j after training on task i.
    Tasks are 1-indexed integers (1, 2, ..., T).
    """

    def __init__(self) -> None:
        # R[train_task][eval_task] -> float
        self._matrix: dict[int, dict[int, float]] = {}
        # Initial zero-shot baselines: baseline[eval_task] -> float
        self._baselines: dict[int, float] = {}

    def set_baseline(self, task_idx: int, score: float) -> None:
        """Set zero-shot performance on a task prior to any sequential training."""
        self._baselines[task_idx] = score

    def record_eval(self, train_task: int, eval_task: int, score: float) -> None:
        """Record the performance on eval_task after completing train_task."""
        if train_task not in self._matrix:
            self._matrix[train_task] = {}
        self._matrix[train_task][eval_task] = score

    def get_score(self, train_task: int, eval_task: int) -> float | None:
        """Retrieve R[train_task, eval_task] if recorded."""
        return self._matrix.get(train_task, {}).get(eval_task)

    def backward_transfer(self, up_to_task: int | None = None) -> float:
        """Compute Backward Transfer (BWT).

        BWT = 1 / (T - 1) * sum_{i=1}^{T-1} (R_{T, i} - R_{i, i})
        Negative values indicate catastrophic forgetting; >= 0 indicates retention or improvement.
        """
        tasks = sorted(self._matrix.keys())
        if len(tasks) < 2:
            return 0.0

        current_t = tasks[-1] if up_to_task is None else up_to_task
        eval_tasks = [t for t in tasks if t < current_t]
        if not eval_tasks:
            return 0.0

        diffs: list[float] = []
        for i in eval_tasks:
            r_t_i = self.get_score(current_t, i)
            r_i_i = self.get_score(i, i)
            if r_t_i is not None and r_i_i is not None:
                diffs.append(r_t_i - r_i_i)

        return sum(diffs) / len(diffs) if diffs else 0.0

    def forward_transfer(
        self,
        baseline_scores: dict[int, float] | None = None,
        up_to_task: int | None = None,
    ) -> float:
        """Compute Forward Transfer (FWT).

        FWT = 1 / (T - 1) * sum_{i=2}^{T} (R_{i-1, i} - b_i)
        where b_i is zero-shot baseline performance on task i.
        """
        baselines = baseline_scores if baseline_scores is not None else self._baselines
        tasks = sorted(self._matrix.keys())
        if len(tasks) < 2:
            return 0.0

        max_t = tasks[-1] if up_to_task is None else up_to_task
        target_tasks = [t for t in tasks if t >= 2 and t <= max_t]
        if not target_tasks:
            return 0.0

        diffs: list[float] = []
        for i in target_tasks:
            prev_t = i - 1
            r_prev_i = self.get_score(prev_t, i)
            b_i = baselines.get(i, 0.0)
            if r_prev_i is not None:
                diffs.append(r_prev_i - b_i)

        return sum(diffs) / len(diffs) if diffs else 0.0

    def forgetting(self, eval_task: int, current_task: int | None = None) -> float:
        """Compute catastrophic forgetting on a specific task j.

        F_j = max_{k in {1, ..., T-1}} R_{k, j} - R_{T, j}
        """
        tasks = sorted(self._matrix.keys())
        if not tasks:
            return 0.0

        current_t = tasks[-1] if current_task is None else current_task
        r_t_j = self.get_score(current_t, eval_task)
        if r_t_j is None:
            return 0.0

        prior_scores = [
            self.get_score(k, eval_task)
            for k in tasks
            if k < current_t and self.get_score(k, eval_task) is not None
        ]
        valid_priors = [s for s in prior_scores if s is not None]
        if not valid_priors:
            return 0.0

        return max(0.0, max(valid_priors) - r_t_j)

    def average_forgetting(self, up_to_task: int | None = None) -> float:
        """Compute average catastrophic forgetting across all previously learned tasks."""
        tasks = sorted(self._matrix.keys())
        if len(tasks) < 2:
            return 0.0

        current_t = tasks[-1] if up_to_task is None else up_to_task
        prior_tasks = [t for t in tasks if t < current_t]
        if not prior_tasks:
            return 0.0

        forgetting_vals = [self.forgetting(j, current_t) for j in prior_tasks]
        return sum(forgetting_vals) / len(forgetting_vals)

    def summary(self) -> dict[str, Any]:
        """Return a structured summary of continual learning evaluation metrics."""
        tasks = sorted(self._matrix.keys())
        return {
            "num_tasks": len(tasks),
            "backward_transfer": self.backward_transfer(),
            "forward_transfer": self.forward_transfer(),
            "average_forgetting": self.average_forgetting(),
            "matrix": {f"task_{i}": {f"eval_{j}": val for j, val in row.items()} for i, row in self._matrix.items()},
        }
