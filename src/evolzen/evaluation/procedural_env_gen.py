"""Procedural generator for held-out novel mini-environments (Phase 2.4).

Never reuse a small, fixed set of held-out environments across evaluation rounds — this is a
direct, actionable lesson from the field's own ARC-AGI-3 public/private gap (a harness went
from 30.2% cold to 96.4% purely through repeated exposure to the *same* 25 games). Every
evaluation round must use genuinely fresh instances.
"""
from __future__ import annotations

from evolzen.environment.engine import Environment


class ProceduralEnvironmentGenerator:
    """Generates a fresh, never-before-seen environment instance within the Phase 1.1 domain
    family, for each evaluation round."""

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._round = 0

    def next_environment(self) -> Environment:
        """Generate the next fresh environment instance.

        Phase 0 stub. Real implementation must guarantee: (a) genuinely novel parameters each
        call (not a reshuffled fixed pool), and (b) that "novel" is tracked and enforced — the
        final report depends on being able to state, with evidence, that no evaluation
        environment was reused.
        """
        self._round += 1
        raise NotImplementedError(
            "Implement alongside the Phase 1.1 domain choice. See docs/phases/2.4-2.5-evaluation.md."
        )
