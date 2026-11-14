"""PPO/GRPO-style grounded predictor and planner (Phase 2.1).

Reward = accuracy of predicted agent intent/outcome against the environment's real, verifiable
result. Deliberately no pre-committed accuracy target — reporting whatever accuracy is actually
measured on target hardware (AGENTS.md Rules #4 and #5).

Cites:
- DeepSeekMath / GRPO (Shao et al., arXiv:2402.03300) for critic-free group-relative policy optimization;
- CLEAR (Rolnick et al., NeurIPS 2019, arXiv:1811.11682) for mixed on-policy / off-policy rehearsal;
- Wang et al. (2024, IEEE TPAMI, DOI:10.1109/TPAMI.2024.3367329) for continual learning transfer metrics;
- CLaaS (arXiv:2606.05559) for continual learning as an infrastructure service.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from evolzen.predictor.dynamics import REWARD_DIMENSIONS, WorldDynamicsPredictor
from evolzen.predictor.rehearsal_buffer import ContinualMetricsTracker, RehearsalBuffer
from evolzen.schemas.transition import Action, Emission, State, Transition


@dataclass
class PredictionResult:
    """Structured prediction outcome from the grounded predictor/planner."""

    predicted_emission: dict[str, Any]
    confidence: float
    predicted_next_state: State | None = None
    action: Action | None = None
    reward_decomposition: dict[str, float] = field(default_factory=dict)
    emission: Emission | None = None

    def __post_init__(self) -> None:
        if self.emission is None and isinstance(self.predicted_emission, dict):
            self.emission = Emission(data=self.predicted_emission)


class Planner:
    """Trains via policy-gradient RL (GRPO) against verifiable environment outcomes."""

    def __init__(
        self,
        rehearsal_buffer: RehearsalBuffer,
        dynamics: WorldDynamicsPredictor | None = None,
        *,
        lr: float = 0.05,
        grpo_clip_eps: float = 0.2,
        grpo_beta_kl: float = 0.01,
    ) -> None:
        self._rehearsal_buffer = rehearsal_buffer
        self._dynamics = dynamics if dynamics is not None else WorldDynamicsPredictor()
        self._lr = lr
        self._grpo_clip_eps = grpo_clip_eps
        self._grpo_beta_kl = grpo_beta_kl
        # Parametric action logits for GRPO policy
        self._policy_logits: dict[str, float] = defaultdict(float)
        self._update_count: int = 0
        self._metrics_tracker = ContinualMetricsTracker()

    @property
    def dynamics(self) -> WorldDynamicsPredictor:
        return self._dynamics

    @property
    def rehearsal_buffer(self) -> RehearsalBuffer:
        return self._rehearsal_buffer

    @property
    def metrics_tracker(self) -> ContinualMetricsTracker:
        return self._metrics_tracker

    @property
    def update_count(self) -> int:
        return self._update_count

    def policy_probabilities(self, candidate_actions: Sequence[str]) -> dict[str, float]:
        """Compute softmax policy probabilities over candidate action types."""
        if not candidate_actions:
            return {}
        logits = [self._policy_logits[a] for a in candidate_actions]
        max_l = max(logits)
        exp_logits = [math.exp(val - max_l) for val in logits]
        total_exp = sum(exp_logits)
        if total_exp <= 0.0:
            prob = 1.0 / len(candidate_actions)
            return {a: prob for a in candidate_actions}
        return {a: e / total_exp for a, e in zip(candidate_actions, exp_logits, strict=False)}

    def predict(self, transition_context: list[Transition]) -> PredictionResult:
        """Predict the next agent intent/outcome given recent context.

        Loads current transition dynamics and policy preference, scored against the
        real `Transition.emission` that actually occurs in the environment.
        """
        if not transition_context:
            return PredictionResult(
                predicted_emission={"accepted": True, "reason": "default_context", "rewards": [0.0] * 8},
                confidence=0.1,
                reward_decomposition={dim: 0.0 for dim in REWARD_DIMENSIONS},
            )

        last_t = transition_context[-1]
        actor_id = last_t.action.agent_id
        current_state = last_t.next_state

        # Known candidate action types
        known_actions = list(self._policy_logits.keys())
        if not known_actions:
            known_actions = ["wait", "gather", "move", "craft", "trade", "share"]

        probs = self.policy_probabilities(known_actions)
        best_action_type = max(probs.items(), key=lambda kv: kv[1])[0] if probs else "wait"

        candidate_action = Action(agent_id=actor_id, action_type=best_action_type)
        pred_emission, pred_next_state = self._dynamics.predict(
            state=current_state,
            action=candidate_action,
            seed=last_t.seed,
        )

        pred_rewards = pred_emission.data.get("rewards", [0.0] * 8)
        reward_decomp = {
            name: float(pred_rewards[i]) if i < len(pred_rewards) else 0.0
            for i, name in enumerate(REWARD_DIMENSIONS)
        }

        confidence = float(pred_emission.data.get("confidence", 0.5))

        return PredictionResult(
            predicted_emission=pred_emission.data,
            confidence=confidence,
            predicted_next_state=pred_next_state,
            action=candidate_action,
            reward_decomposition=reward_decomp,
            emission=pred_emission,
        )

    def plan_action(
        self,
        state: State,
        agent_id: str,
        candidate_actions: list[Action],
    ) -> tuple[Action, PredictionResult]:
        """Evaluate candidate actions and select the action optimizing predicted outcome."""
        if not candidate_actions:
            fallback_action = Action(agent_id=agent_id, action_type="wait")
            res = PredictionResult(
                predicted_emission={"accepted": True, "reason": "wait", "rewards": [0.0] * 8},
                confidence=0.5,
            )
            return fallback_action, res

        action_types = [a.action_type for a in candidate_actions]
        probs = self.policy_probabilities(action_types)

        best_score = -float("inf")
        best_action = candidate_actions[0]
        best_result = PredictionResult(
            predicted_emission={},
            confidence=0.0,
        )

        for act in candidate_actions:
            pred_emission, pred_next = self._dynamics.predict(state=state, action=act)
            rewards = pred_emission.data.get("rewards", [0.0] * 8)
            reward_sum = sum(float(r) for r in rewards)
            policy_bias = probs.get(act.action_type, 0.0)

            # Combined score = predicted reward + policy prior
            composite_score = reward_sum + 0.1 * policy_bias
            if composite_score > best_score:
                best_score = composite_score
                best_action = act
                decomp = {
                    name: float(rewards[i]) if i < len(rewards) else 0.0
                    for i, name in enumerate(REWARD_DIMENSIONS)
                }
                best_result = PredictionResult(
                    predicted_emission=pred_emission.data,
                    confidence=float(pred_emission.data.get("confidence", 0.5)),
                    predicted_next_state=pred_next,
                    action=act,
                    reward_decomposition=decomp,
                    emission=pred_emission,
                )

        return best_action, best_result

    def train_step(
        self,
        batch: list[Transition],
        replay_ratio: float = 0.5,
    ) -> dict[str, float]:
        """One GRPO update with CLEAR mixed rehearsal against catastrophic forgetting.

        Cites DeepSeekMath (Shao et al., arXiv:2402.03300) for critic-free group-relative
        policy optimization and Rolnick et al. (CLEAR, NeurIPS 2019) for replay mixing.
        """
        if not batch and len(self._rehearsal_buffer) == 0:
            return {"loss": 0.0, "sample_count": 0.0}

        # CLEAR mixed on-policy / off-policy batching
        total_batch_size = max(len(batch), 1)
        mixed_batch = self._rehearsal_buffer.sample_clear_batch(
            new_transitions=batch,
            total_batch_size=total_batch_size,
            replay_ratio=replay_ratio,
        )
        if not mixed_batch:
            mixed_batch = list(batch)

        # 1. Update supervised world dynamics baseline
        dyn_metrics = self._dynamics.train_batch(mixed_batch)

        # 2. Extract empirical outcomes / verifiable rewards
        rewards: list[float] = []
        action_types: list[str] = []
        for t in mixed_batch:
            r_raw = t.emission.data.get("rewards", [0.0] * 8)
            r_val = sum(float(x) for x in r_raw) if isinstance(r_raw, (list, tuple)) else 0.0
            rewards.append(r_val)
            action_types.append(t.action.action_type)

        # 3. GRPO Group-Relative Advantage Normalization
        mean_r = float(np.mean(rewards)) if rewards else 0.0
        std_r = float(np.std(rewards)) if len(rewards) > 1 else 1.0
        if std_r < 1e-6:
            std_r = 1.0

        advantages = [(r - mean_r) / std_r for r in rewards]

        # 4. Policy gradient update on action logits
        grad_norms: list[float] = []
        for act_type, adv in zip(action_types, advantages, strict=False):
            clipped_adv = max(-self._grpo_clip_eps, min(self._grpo_clip_eps, adv))
            delta = self._lr * clipped_adv
            # KL regularization towards 0.0 (uniform prior)
            self._policy_logits[act_type] = (
                (1.0 - self._grpo_beta_kl) * self._policy_logits[act_type] + delta
            )
            grad_norms.append(abs(delta))

        # 5. Populate rehearsal buffer with the new transitions
        for t in batch:
            self._rehearsal_buffer.add(t)

        self._update_count += 1

        # Calculate policy entropy for monitoring
        distinct_actions = list(self._policy_logits.keys())
        probs = self.policy_probabilities(distinct_actions)
        entropy = -sum(p * math.log(max(1e-9, p)) for p in probs.values()) if probs else 0.0

        return {
            "loss": dyn_metrics.get("loss", 0.0),
            "grpo_advantage_mean": mean_r,
            "grpo_advantage_std": std_r,
            "policy_entropy": entropy,
            "avg_gradient_step": float(np.mean(grad_norms)) if grad_norms else 0.0,
            "sample_count": float(len(mixed_batch)),
            "rehearsal_buffer_size": float(len(self._rehearsal_buffer)),
            "update_count": float(self._update_count),
        }
