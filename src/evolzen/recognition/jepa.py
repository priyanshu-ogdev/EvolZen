"""JEPA component of the recognition model (Phase 2.3) — "what states are".

A continuous, differentiable, grounded encoder learning latent representations of environment
states — the half of the recognition model meant to handle the noisy, partially-observed,
language-mediated social domain this project actually cares about, where clean discrete-domain
techniques alone tend to struggle. Follows LeJEPA's provable, heuristic-free training objective
(arXiv:2511.08544). See also arXiv:2605.26379 ("When Does LeJEPA Learn a World Model?") before
assuming this component has learned a genuine world model rather than a shortcut.
"""
from __future__ import annotations

from typing import Protocol

from evolzen.schemas.transition import State


class JEPAEncoder(Protocol):
    """Protocol satisfied by a concrete JEPA-style encoder (e.g. a small transformer trained
    with a LeJEPA-style self-supervised objective over environment State representations)."""

    def encode(self, state: State) -> list[float]:
        """Return a latent embedding for `state`."""
        ...

    def train_step(self, batch: list[State]) -> dict[str, float]:
        """One self-supervised training step. Returns metrics for logging."""
        ...
