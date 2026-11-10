"""Wake-sleep component of the recognition model (Phase 2.3) — "how states transform".

A discrete, DreamCoder-style (PLDI 2021) library-learning loop: "wake" proposes hypotheses for
the current task using the existing verified-rule library; "sleep" refactors solved tasks into
new reusable abstractions and retrains the recognition prior on both real solved cases and
self-generated "fantasy" cases. Following arXiv:2603.25975, this component is meant to be
fused with `evolzen.recognition.jepa.JEPAEncoder` — neither half hand-coded — rather than used
alone.

Evaluate with the full ablation matrix from docs/phases/2.3-recognition.md: with/without
recognition model x with/without manual layer x JEPA-only / wake-sleep-only / combined.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.rule_library import RuleLibrary


@dataclass(frozen=True)
class FantasyCase:
    """A self-generated training case used during the "sleep" phase (not a real Transition)."""

    synthetic_context: dict[str, Any]
    target_rule_id: str


class WakeSleepLearner:
    """Alternates wake (propose using the library) and sleep (refactor + retrain the prior)."""

    def __init__(self, rule_library: RuleLibrary) -> None:
        self._rule_library = rule_library

    def wake_propose(self, observation: dict[str, Any]) -> CandidateRule:
        """Propose a hypothesis for `observation` using the current verified-rule library."""
        raise NotImplementedError("Implement alongside the JEPA fusion. See docs/phases/2.3-recognition.md.")

    def sleep_step(
        self, real_cases: list[dict[str, Any]], fantasy_cases: list[FantasyCase],
    ) -> dict[str, float]:
        """One sleep-phase update: refactor + retrain on real + self-generated cases."""
        raise NotImplementedError("Implement alongside the JEPA fusion. See docs/phases/2.3-recognition.md.")
