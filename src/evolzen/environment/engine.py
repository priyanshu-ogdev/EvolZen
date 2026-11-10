"""Phase 1.1 — Environment Engine.

A concrete environment is any class implementing this protocol. Which of the three candidate
domains (resource-negotiation game, market simulation against historical data, or
code-with-tests) gets built is a Phase 1.1 decision for the research team, not a scaffolding
decision — see docs/phases/1.1-environment.md. This module defines the interface every
candidate domain must satisfy, plus the one property that isn't optional: verifiability.

Non-negotiable property (Phase 1.1 success metric): every emission this environment produces
must be independently re-derivable from the (state, action) pair that produced it. If a domain
implementation can't guarantee that, it is not a valid Phase 1.1 environment, regardless of how
interesting it is.
"""
from __future__ import annotations

from typing import Protocol

from evolzen.schemas.transition import Action, State, Transition


class Environment(Protocol):
    """Protocol every Phase 1.1 domain implementation must satisfy."""

    def reset(self) -> State:
        """Reset to an initial state and return it."""
        ...

    def step(self, state: State, action: Action) -> Transition:
        """Apply `action` to `state`, returning the full logged transition.

        Implementations must be deterministic given (state, action), or must expose whatever
        randomness they use in a way that makes replay exact (e.g., a seeded RNG captured in
        `Emission.data`) — `evolzen.exploration.verifier` depends on exact reproducibility.
        """
        ...

    def is_terminal(self, state: State) -> bool:
        """Whether `state` ends an episode."""
        ...
