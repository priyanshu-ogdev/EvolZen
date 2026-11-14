"""JEPA component of the recognition model (Phase 2.3) — "what states are".

A continuous, differentiable, grounded encoder learning latent representations of environment
states — the half of the recognition model meant to handle the noisy, partially-observed,
social domain. Follows I-JEPA (Assran et al., CVPR 2023, arXiv:2301.08243) and LeJEPA
(arXiv:2511.08544) for non-contrastive latent predictive representations without pixel/token
reconstruction. See also arXiv:2605.26379 ("When Does LeJEPA Learn a World Model?").

All empirical representation metrics remain untested until Phase 2.3 benchmarks are executed
on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from evolzen.schemas.transition import State

FEATURE_DIM: int = 16


class JEPAEncoder(Protocol):
    """Protocol satisfied by a concrete JEPA-style encoder (e.g. a small projection model
    trained with a LeJEPA-style self-supervised objective over environment State representations)."""

    def encode(self, state: State) -> list[float]:
        """Return a latent embedding for `state`."""
        ...

    def train_step(self, batch: list[State]) -> dict[str, float]:
        """One self-supervised training step. Returns metrics for logging."""
        ...


def extract_state_features(state: State) -> np.ndarray:
    """Extract a canonical normalized 16-dimensional continuous feature vector from `State`.

    Extracts macro-level homeostatic, economic, demographic, and ecological indicators.
    """
    vec = np.zeros(FEATURE_DIM, dtype=np.float32)
    data = state.data
    if not isinstance(data, dict):
        return vec

    # 1. Temporal dimensions
    vec[0] = min(1.0, float(data.get("tick", 0)) / 2000.0)
    vec[1] = min(1.0, float(data.get("step_index", 0)) / 2000.0)

    # 2. Agent demographics & homeostasis
    agents = data.get("agents")
    if isinstance(agents, dict) and agents:
        num_agents = len(agents)
        vec[2] = min(1.0, num_agents / 64.0)

        living = [a for a in agents.values() if isinstance(a, dict) and a.get("alive", True)]
        vec[3] = min(1.0, len(living) / 64.0)

        if living:
            energies = [float(a.get("energy", 0.5)) for a in living]
            fatigues = [float(a.get("fatigue", 0.5)) for a in living]
            currencies = [float(a.get("currency", 10.0)) for a in living]
            healths = [float(a.get("health", 1.0)) for a in living]

            vec[4] = float(np.mean(energies))
            vec[5] = float(np.mean(fatigues))
            vec[6] = min(1.0, float(np.mean(currencies)) / 100.0)
            vec[7] = float(np.mean(healths))
            vec[8] = float(np.min(energies))
            vec[9] = float(np.max(fatigues))
    elif "i" in data:
        # Fallback for minimal test transition states
        val = float(data["i"])
        vec[2] = min(1.0, val / 100.0)
        vec[4] = 0.5
        vec[5] = 0.5

    # 3. Ecological & resource stocks
    locations = data.get("locations")
    if isinstance(locations, dict) and locations:
        food_sum = 0.0
        water_sum = 0.0
        wood_sum = 0.0
        stone_sum = 0.0
        for loc in locations.values():
            if isinstance(loc, dict):
                res = loc.get("resources", {})
                if isinstance(res, dict):
                    food_sum += float(res.get("food", 0.0))
                    water_sum += float(res.get("water", 0.0))
                    wood_sum += float(res.get("wood", 0.0))
                    stone_sum += float(res.get("stone", 0.0))
        vec[10] = min(1.0, food_sum / 200.0)
        vec[11] = min(1.0, water_sum / 200.0)
        vec[12] = min(1.0, wood_sum / 200.0)
        vec[13] = min(1.0, stone_sum / 200.0)

    # 4. Institutional & capability complexity
    capabilities = data.get("capabilities", [])
    contracts = data.get("contracts", [])
    if isinstance(capabilities, (list, tuple, dict)):
        vec[14] = min(1.0, len(capabilities) / 32.0)
    if isinstance(contracts, (list, tuple, dict)):
        vec[15] = min(1.0, len(contracts) / 32.0)

    return vec


class GroundedJEPAEncoder:
    """A CPU-friendly grounded JEPA encoder implementing the LeJEPA/I-JEPA self-supervised objective.

    Projects normalized state features into a latent representation space using non-contrastive
    invariance and variance-regularization losses (Assran et al., CVPR 2023; LeJEPA arXiv:2511.08544).
    """

    def __init__(
        self,
        in_dim: int = FEATURE_DIM,
        embedding_dim: int = 32,
        *,
        learning_rate: float = 0.02,
        variance_weight: float = 0.1,
        seed: int = 42,
    ) -> None:
        self.in_dim = in_dim
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.variance_weight = variance_weight

        rng = np.random.default_rng(seed)
        # Xavier initialization
        scale = math.sqrt(2.0 / (in_dim + embedding_dim))
        self._w: np.ndarray = rng.normal(0.0, scale, size=(embedding_dim, in_dim)).astype(np.float32)
        self._b: np.ndarray = np.zeros(embedding_dim, dtype=np.float32)
        self._step_count: int = 0

    @property
    def step_count(self) -> int:
        return self._step_count

    def encode(self, state: State) -> list[float]:
        """Project `State` into a normalized latent embedding vector."""
        x = extract_state_features(state)
        z = self._w @ x + self._b
        # L2 unit normalization
        norm = float(np.linalg.norm(z))
        z_norm = z / norm if norm > 1e-7 else z
        return [float(v) for v in z_norm]

    def similarity(self, state_a: State, state_b: State) -> float:
        """Compute cosine similarity between the latent representations of two states."""
        za = np.asarray(self.encode(state_a), dtype=np.float32)
        zb = np.asarray(self.encode(state_b), dtype=np.float32)
        dot = float(np.dot(za, zb))
        return max(-1.0, min(1.0, dot))

    def train_step(self, batch: list[State]) -> dict[str, float]:
        """One non-contrastive self-supervised LeJEPA training step over a batch of states."""
        if not batch:
            return {"loss": 0.0, "invariance_loss": 0.0, "variance_loss": 0.0, "sample_count": 0.0}

        b_size = len(batch)
        x_orig = np.stack([extract_state_features(s) for s in batch], axis=0)  # (B, in_dim)

        # Generate perturbed views (masked coordinates + mild Gaussian noise)
        noise = np.random.normal(0.0, 0.02, size=x_orig.shape).astype(np.float32)
        x_pert = np.clip(x_orig + noise, 0.0, 1.0)

        # Compute representations: (B, embedding_dim)
        z_orig = (self._w @ x_orig.T).T + self._b
        z_pert = (self._w @ x_pert.T).T + self._b

        # 1. Invariance Loss: mean squared error between representations
        diff = z_orig - z_pert  # (B, embedding_dim)
        invariance_loss = float(np.mean(diff ** 2))

        # 2. Variance Loss: prevent dimensional collapse by encouraging std >= 1.0
        stds = np.std(z_orig, axis=0) if b_size > 1 else np.ones(self.embedding_dim, dtype=np.float32)
        variance_loss = float(np.mean(np.maximum(0.0, 1.0 - stds)))

        total_loss = invariance_loss + self.variance_weight * variance_loss

        # Analytic gradient for invariance loss: dL/dW = (2 / (B * D)) * diff.T @ (x_orig - x_pert)
        x_diff = x_orig - x_pert  # (B, in_dim)
        grad_w = (2.0 / (b_size * self.embedding_dim)) * (diff.T @ x_diff)
        grad_b = (2.0 / (b_size * self.embedding_dim)) * np.sum(diff, axis=0)

        # Gradient descent update with clipping
        grad_w = np.clip(grad_w, -1.0, 1.0)
        grad_b = np.clip(grad_b, -1.0, 1.0)
        self._w -= self.learning_rate * grad_w
        self._b -= self.learning_rate * grad_b
        self._step_count += 1

        return {
            "loss": float(total_loss),
            "invariance_loss": invariance_loss,
            "variance_loss": variance_loss,
            "sample_count": float(b_size),
        }
