"""The synthesizer half of the actor/synthesizer/verifier loop (Phase 1.4).

Deliberately a thin interface. arXiv:2605.05138 (Executable World Models for ARC-AGI-3 in the
Era of Coding Agents) shows an off-the-shelf coding-agent harness — wired directly to an
environment's transition-log API, with a scratch directory to write and test hypothesis code
in, and the exact-match verifier as its acceptance gate — reaches 58% mean RHAE on public
ARC-AGI-3 games with zero domain-specific hand-coding. The intended implementation path is to
satisfy this `Synthesizer` protocol with a wrapper around such a harness, not to build program
synthesis from scratch.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from evolzen.schemas.transition import Transition


@dataclass(frozen=True)
class CandidateRule:
    """A synthesizer's hypothesis about how the environment behaves.

    `code` is executable Python implementing a `(State, Action) -> Emission` prediction —
    exactly what `evolzen.exploration.verifier.Verifier` checks by exact replay.
    """

    rule_id: str
    code: str
    explains: list[str]  # transition_ids this rule was synthesized to explain


class Synthesizer(Protocol):
    """Protocol satisfied by either a bespoke synthesizer or a coding-agent-harness wrapper."""

    def propose(self, observed_transitions: list[Transition]) -> CandidateRule:
        """Propose a candidate rule explaining the given transitions."""
        ...
