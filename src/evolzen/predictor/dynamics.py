"""Supervised world dynamics predictor (Phase 2.1).

Provides a grounded supervised transition model baseline predicting observable emissions
and next world states from (state, action, exogenous_input, seed) records. Cites Wang et al.
(2024, IEEE TPAMI, DOI:10.1109/TPAMI.2024.3367329) for continual-learning representation
principles, Rolnick et al. (CLEAR, NeurIPS 2019, arXiv:1811.11682) for experience replay
grounding, and Tycho (arXiv:2607.28287) for transition verification.

Empirical prediction accuracy curves and transfer rates remain untested until Phase 2.1
benchmarks are executed on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import numpy as np

from evolzen.schemas.transition import Action, Emission, ExogenousInput, State, Transition

REWARD_DIMENSIONS: tuple[str, ...] = (
    "health",
    "energy",
    "comfort",
    "resource",
    "wealth",
    "social",
    "safety",
    "novelty",
)


@dataclass
class ActionDynamicsStats:
    """Empirical transition statistics for a specific action type."""

    action_type: str
    total_count: int = 0
    accepted_count: int = 0
    reason_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    reward_sums: list[float] = field(default_factory=lambda: [0.0] * 8)
    # Average deltas for agent numeric properties: (energy, fatigue, currency, health)
    agent_delta_sums: dict[str, float] = field(
        default_factory=lambda: {
            "energy": 0.0,
            "fatigue": 0.0,
            "currency": 0.0,
            "health": 0.0,
        }
    )

    @property
    def acceptance_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.accepted_count / self.total_count

    @property
    def dominant_reason(self) -> str:
        if not self.reason_counts:
            return "accepted" if self.acceptance_rate >= 0.5 else "rejected"
        return max(self.reason_counts.items(), key=lambda kv: kv[1])[0]

    @property
    def mean_rewards(self) -> list[float]:
        if self.total_count == 0:
            return [0.0] * 8
        return [r / self.total_count for r in self.reward_sums]

    @property
    def mean_agent_deltas(self) -> dict[str, float]:
        if self.total_count == 0:
            return {"energy": 0.0, "fatigue": 0.0, "currency": 0.0, "health": 0.0}
        return {k: v / self.total_count for k, v in self.agent_delta_sums.items()}


class WorldDynamicsPredictor:
    """Supervised baseline predicting `(predicted_emission, predicted_next_state)`.

    Learns parametric outcome statistics and delta dynamics across action types from
    verifiable historical `Transition` records.
    """

    def __init__(self) -> None:
        self._stats: dict[str, ActionDynamicsStats] = {}
        self._total_transitions_seen: int = 0

    @property
    def total_transitions_seen(self) -> int:
        return self._total_transitions_seen

    def get_stats(self, action_type: str) -> ActionDynamicsStats:
        """Return learned empirical statistics for an action type."""
        if action_type not in self._stats:
            self._stats[action_type] = ActionDynamicsStats(action_type=action_type)
        return self._stats[action_type]

    def fit(self, transitions: Sequence[Transition]) -> dict[str, float]:
        """Fit the predictor over a batch of historical transitions."""
        self._stats.clear()
        self._total_transitions_seen = 0
        return self.train_batch(transitions)

    def train_batch(self, transitions: Sequence[Transition]) -> dict[str, float]:
        """Incrementally update empirical transition statistics from a transition batch."""
        if not transitions:
            return {"loss": 0.0, "batch_size": 0.0}

        losses: list[float] = []
        for t in transitions:
            action_type = t.action.action_type
            stats = self.get_stats(action_type)

            accepted = bool(t.emission.data.get("accepted", True))
            reason = str(t.emission.data.get("reason", "ok"))
            rewards_raw = t.emission.data.get("rewards", [0.0] * 8)
            rewards = [float(r) for r in rewards_raw] if isinstance(rewards_raw, (list, tuple)) else [0.0] * 8
            if len(rewards) < 8:
                rewards.extend([0.0] * (8 - len(rewards)))

            stats.total_count += 1
            if accepted:
                stats.accepted_count += 1
            stats.reason_counts[reason] += 1
            for i in range(8):
                stats.reward_sums[i] += rewards[i]

            # Measure agent state deltas if present
            s_data = t.state.data
            ns_data = t.next_state.data
            if (
                isinstance(s_data, dict)
                and isinstance(ns_data, dict)
                and "agents" in s_data
                and "agents" in ns_data
                and isinstance(s_data["agents"], dict)
                and isinstance(ns_data["agents"], dict)
                and t.action.agent_id in s_data["agents"]
                and t.action.agent_id in ns_data["agents"]
            ):
                a_prev = s_data["agents"][t.action.agent_id]
                a_next = ns_data["agents"][t.action.agent_id]
                if isinstance(a_prev, dict) and isinstance(a_next, dict):
                    for prop in ("energy", "fatigue", "currency", "health"):
                        v_prev = float(a_prev.get(prop, 0.0))
                        v_next = float(a_next.get(prop, 0.0))
                        stats.agent_delta_sums[prop] += (v_next - v_prev)

            self._total_transitions_seen += 1

            # Immediate supervised cross-entropy / MAE error for logging
            pred_rewards = stats.mean_rewards
            step_loss = float(np.mean([abs(p - r) for p, r in zip(pred_rewards, rewards, strict=False)]))
            losses.append(step_loss)

        avg_loss = float(np.mean(losses)) if losses else 0.0
        return {"loss": avg_loss, "batch_size": float(len(transitions))}

    def predict(
        self,
        state: State,
        action: Action,
        exogenous_input: ExogenousInput | None = None,
        seed: int = 0,
    ) -> tuple[Emission, State]:
        """Predict (predicted_emission, predicted_next_state) deterministically."""
        stats = self.get_stats(action.action_type)
        accepted = stats.acceptance_rate >= 0.5
        reason = stats.dominant_reason
        pred_rewards = [round(r, 6) for r in stats.mean_rewards]

        s_data = state.data
        next_data: dict[str, Any] = deepcopy(s_data) if isinstance(s_data, dict) else {}

        # Advance tick and step_index
        cur_tick = int(next_data.get("tick", 0))
        exog_tick = exogenous_input.tick if exogenous_input is not None else cur_tick
        next_tick = max(cur_tick + 1, exog_tick)
        next_data["tick"] = next_tick

        cur_step = int(next_data.get("step_index", 0))
        next_data["step_index"] = cur_step + 1
        next_data["seed"] = seed

        # Adjust agent state if agents map is present
        if (
            isinstance(next_data.get("agents"), dict)
            and action.agent_id in next_data["agents"]
            and isinstance(next_data["agents"][action.agent_id], dict)
        ):
            agent_dict = next_data["agents"][action.agent_id]
            deltas = stats.mean_agent_deltas
            for prop in ("energy", "fatigue", "currency", "health"):
                if prop in agent_dict:
                    val = float(agent_dict[prop]) + deltas[prop]
                    if prop in ("energy", "fatigue", "health"):
                        val = max(0.0, min(1.0, val))
                    elif prop == "currency":
                        val = max(0.0, val)
                    agent_dict[prop] = round(val, 6)
            agent_dict["last_action_tick"] = next_tick

        emission_data: dict[str, Any] = {
            "accepted": accepted,
            "reason": reason,
            "tick": next_tick,
            "step_index": cur_step + 1,
            "actor_id": action.agent_id,
            "action_type": action.action_type,
            "rewards": pred_rewards,
            "confidence": 1.0 if stats.total_count >= 10 else max(0.1, stats.total_count / 10.0),
        }

        pred_emission = Emission(data=emission_data)
        pred_next_state = State(state_id=uuid4(), data=next_data)
        return pred_emission, pred_next_state

    def evaluate(self, test_transitions: Sequence[Transition]) -> dict[str, float]:
        """Compute empirical accuracy and error decomposition across test transitions."""
        if not test_transitions:
            return {
                "acceptance_accuracy": 0.0,
                "reward_mae": 0.0,
                "reward_mse": 0.0,
                "sample_count": 0.0,
            }

        correct_accepted = 0
        reward_aes: list[list[float]] = [[] for _ in range(8)]
        agent_state_aes: list[float] = []

        for t in test_transitions:
            pred_emission, pred_next_state = self.predict(
                t.state, t.action, t.exogenous_input, t.seed
            )
            actual_accepted = bool(t.emission.data.get("accepted", True))
            pred_accepted = bool(pred_emission.data.get("accepted", True))
            if actual_accepted == pred_accepted:
                correct_accepted += 1

            actual_rewards_raw = t.emission.data.get("rewards", [0.0] * 8)
            actual_rewards = (
                [float(r) for r in actual_rewards_raw]
                if isinstance(actual_rewards_raw, (list, tuple))
                else [0.0] * 8
            )
            if len(actual_rewards) < 8:
                actual_rewards.extend([0.0] * (8 - len(actual_rewards)))

            pred_rewards = [float(r) for r in pred_emission.data.get("rewards", [0.0] * 8)]
            for i in range(8):
                reward_aes[i].append(abs(pred_rewards[i] - actual_rewards[i]))

            # Compare agent state deltas if present
            s_actual = t.next_state.data
            s_pred = pred_next_state.data
            if (
                isinstance(s_actual, dict)
                and isinstance(s_pred, dict)
                and "agents" in s_actual
                and "agents" in s_pred
                and isinstance(s_actual["agents"], dict)
                and isinstance(s_pred["agents"], dict)
                and t.action.agent_id in s_actual["agents"]
                and t.action.agent_id in s_pred["agents"]
            ):
                act_a = s_actual["agents"][t.action.agent_id]
                prd_a = s_pred["agents"][t.action.agent_id]
                if isinstance(act_a, dict) and isinstance(prd_a, dict):
                    for prop in ("energy", "fatigue", "currency", "health"):
                        agent_state_aes.append(abs(float(prd_a.get(prop, 0.0)) - float(act_a.get(prop, 0.0))))

        n = len(test_transitions)
        dim_maes = [float(np.mean(aes)) if aes else 0.0 for aes in reward_aes]
        overall_reward_mae = float(np.mean(dim_maes))
        overall_reward_mse = float(np.mean([d**2 for d in dim_maes]))

        results: dict[str, float] = {
            "acceptance_accuracy": correct_accepted / n,
            "reward_mae": overall_reward_mae,
            "reward_mse": overall_reward_mse,
            "agent_state_mae": float(np.mean(agent_state_aes)) if agent_state_aes else 0.0,
            "sample_count": float(n),
        }

        # Detailed reward decomposition
        for i, name in enumerate(REWARD_DIMENSIONS):
            results[f"reward_mae_{name}"] = dim_maes[i]

        return results
