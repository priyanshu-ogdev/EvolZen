"""The actor half of the actor/synthesizer/verifier loop (Phase 1.4).

Steers exploration by *ontology error* — actively probing whichever agent-type or mechanic the
current rule library explains worst, rather than passively waiting for the population to
stumble onto something interesting.
"""
from __future__ import annotations

from collections.abc import Callable

from evolzen.schemas.transition import State

OntologyErrorFn = Callable[[State], float]


class Actor:
    """Chooses what to probe next, prioritizing high ontology-error regions of the environment."""

    def __init__(self, ontology_error_fn: OntologyErrorFn) -> None:
        self._ontology_error_fn = ontology_error_fn

    def choose_probe(self, candidate_states: list[State]) -> State:
        """Pick the candidate state the current rule library explains worst."""
        return max(candidate_states, key=self._ontology_error_fn)
