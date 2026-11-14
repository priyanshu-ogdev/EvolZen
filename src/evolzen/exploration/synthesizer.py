"""The synthesizer half of the actor/synthesizer/verifier loop (Phase 1.4).

Deliberately a thin interface. arXiv:2605.05138 (Executable World Models for ARC-AGI-3 in the
Era of Coding Agents) shows an off-the-shelf coding-agent harness — wired directly to an
environment's transition-log API, with a scratch directory to write and test hypothesis code
in, and the exact-match verifier as its acceptance gate — reaches 58% mean RHAE on public
ARC-AGI-3 games with zero domain-specific hand-coding. The intended implementation path is to
satisfy this `Synthesizer` protocol with a wrapper around such a harness, not to build program
synthesis from scratch.

Citations:
- Romera-Paredes et al. (FunSearch, Nature 2024, DOI: 10.1038/s41586-023-06924-6) for evaluator-gated
  LLM evolutionary program search;
- Executable World Models for ARC-AGI-3 (arXiv:2605.05138) for coding-agent hypothesis synthesis;
- Wang et al. (Voyager, TMLR 2023) for self-verifying code synthesis.

All synthesized program behaviors remain untested until Phase 1.4 exploration experiments are run.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from evolzen.schemas.transition import Transition


@dataclass(frozen=True)
class CandidateRule:
    """A synthesizer's hypothesis about how the environment behaves.

    `code` is executable Python implementing a `(State, Action, ExogenousInput, seed) -> Emission` prediction —
    exactly what `evolzen.exploration.verifier.Verifier` checks by exact replay under Sandbox isolation.
    """

    rule_id: str
    code: str
    explains: list[str]  # transition_ids this rule was synthesized to explain


class Synthesizer(Protocol):
    """Protocol satisfied by either a bespoke synthesizer or a coding-agent-harness wrapper."""

    def propose(self, observed_transitions: list[Transition]) -> CandidateRule:
        """Propose a candidate rule explaining the given transitions."""
        ...


class TemplateRuleSynthesizer:
    """Deterministic rule synthesizer generating executable Python prediction functions from observed transitions.

    Analyzes observed transitions and synthesizes Python code predicting action emissions,
    designed to be verified under Sandbox isolation before promotion to RuleLibrary.
    """

    def __init__(self, rule_prefix: str = "rule") -> None:
        self.rule_prefix = rule_prefix
        self._counter = 0

    def propose(self, observed_transitions: list[Transition]) -> CandidateRule:
        """Propose an executable CandidateRule explaining the given transitions."""
        if not observed_transitions:
            raise ValueError("Cannot synthesize rule from empty transitions")

        self._counter += 1
        rule_id = f"{self.rule_prefix}-{self._counter}"
        t_ids = [str(t.transition_id) for t in observed_transitions]

        first_emission = observed_transitions[0].emission.data
        all_same = all(t.emission.data == first_emission for t in observed_transitions)

        if all_same:
            emission_json = json.dumps(first_emission)
            code = (
                f"def predict(state, action, ex_input=None, seed=None):\n"
                f"    return {{\"emission\": {emission_json}}}\n"
            )
        else:
            mapping: dict[str, Any] = {}
            for t in observed_transitions:
                mapping[t.action.action_type] = t.emission.data
            mapping_json = json.dumps(mapping)
            code = (
                f"def predict(state, action, ex_input=None, seed=None):\n"
                f"    action_type = action.get('action_type', '')\n"
                f"    mapping = {mapping_json}\n"
                f"    if action_type in mapping:\n"
                f"        return {{\"emission\": mapping[action_type]}}\n"
                f"    return {{\"emission\": {{}}}}\n"
            )

        return CandidateRule(rule_id=rule_id, code=code, explains=t_ids)
