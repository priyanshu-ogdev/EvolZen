"""Deployment-experience rehearsal buffer (Phase 2.1).

Following CLaaS (arXiv:2606.05559): mixing replayed real (situation -> outcome) pairs from
actual deployment into every policy-gradient update is the default continual-learning safeguard
for the planner. Evaluate this against task-free/replay-free continual pretraining (TFGN,
arXiv:2605.15053) as an explicit ablation rather than assuming either wins.
"""
from __future__ import annotations

import random
from collections import deque

from evolzen.schemas.transition import Transition


class RehearsalBuffer:
    """Fixed-capacity FIFO buffer of real transitions, sampled during training updates."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._buffer: deque[Transition] = deque(maxlen=capacity)

    def add(self, transition: Transition) -> None:
        self._buffer.append(transition)

    def sample(self, batch_size: int) -> list[Transition]:
        if batch_size > len(self._buffer):
            raise ValueError(
                f"Requested batch_size={batch_size} exceeds buffer size={len(self._buffer)}"
            )
        return random.sample(list(self._buffer), batch_size)

    def __len__(self) -> int:
        return len(self._buffer)
