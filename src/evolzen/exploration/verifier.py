"""The verifier half of the actor/synthesizer/verifier loop (Phase 1.4).

The implementable replacement for the original blueprint's unspecified "Causal Gate": a
candidate rule is admitted to the library only if it reproduces every recorded transition
exactly — not "fits well." This is the same falsifiability bar used throughout the project
(Phase 1.5 library promotion, Phase 2.2 recognition-model promotion reuse this exact class).
"""
from __future__ import annotations

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.schemas.transition import Transition


class Verifier:
    """Checks a CandidateRule for exact-match reproduction of recorded transitions."""

    def verify(self, rule: CandidateRule, held_out_transitions: list[Transition]) -> bool:
        """Return True only if `rule` exactly reproduces every transition in the held-out set.

        Phase 0 stub — real implementation `exec`s `rule.code` in a restricted namespace
        (inside `evolzen.containment.Sandbox` — see Phase 2.2, and never bypass this even during
        early development) and compares its predicted emission against each transition's
        actual `emission`, field by field.
        """
        raise NotImplementedError(
            "Implement alongside Phase 1.1's domain and Phase 2.2's sandboxing. "
            "See docs/phases/1.4-exploration.md."
        )
