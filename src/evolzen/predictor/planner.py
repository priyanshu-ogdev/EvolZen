"""PPO/GRPO-style grounded predictor (Phase 2.1).

Reward = accuracy of predicted agent intent/outcome against the environment's real, verifiable
result. Deliberately no pre-committed accuracy target — the original blueprint's arbitrary
">90% accuracy 10 steps out" target is dropped in favor of reporting whatever accuracy is
actually measured (RL convergence guarantees are asymptotic statements about a single, fixed,
bounded MDP and say nothing about generalizing across an open-ended social domain).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.schemas.transition import Transition


@dataclass
class PredictionResult:
    predicted_emission: dict[str, Any]
    confidence: float


class Planner:
    """Trains via policy-gradient RL against the environment's verifiable outcomes."""

    def __init__(self, rehearsal_buffer: RehearsalBuffer) -> None:
        self._rehearsal_buffer = rehearsal_buffer

    def predict(self, transition_context: list[Transition]) -> PredictionResult:
        """Predict the next agent intent/outcome given recent context.

        Phase 0 stub. Real implementation loads the current planner policy and produces a
        structured prediction, scored against the real `Transition.emission` that actually
        occurs — that comparison *is* the reward signal for the PPO/GRPO update.
        """
        raise NotImplementedError("Implement alongside the environment domain and reward wiring.")

    def train_step(self, batch: list[Transition]) -> dict[str, float]:
        """One PPO/GRPO update, with rehearsal-buffer replay mixed in against forgetting."""
        raise NotImplementedError("See docs/phases/2.1-predictor.md (CLaaS rehearsal).")
