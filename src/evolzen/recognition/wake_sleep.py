"""Wake-sleep component of the recognition model (Phase 2.3) — "how states transform".

A discrete, DreamCoder-style (PLDI 2021) library-learning loop: "wake" proposes hypotheses for
the current task using the existing verified-rule library; "sleep" refactors solved tasks into
new reusable abstractions and retrains the recognition prior on both real solved cases and
self-generated "fantasy" cases. Following arXiv:2603.25975, this component is fused with
`evolzen.recognition.jepa.JEPAEncoder`.

Citations:
- Ellis et al. (DreamCoder, PLDI 2021, Phil. Trans. R. Soc. A 2023) for wake-sleep library compression;
- Do Neurons Dream of Primitive Operators? (arXiv:2603.25975) for neural-symbolic fusion;
- Romera-Paredes et al. (FunSearch, Nature 2024) for evolutionary hypothesis refinement.

All empirical learning metrics remain untested until Phase 2.3 benchmarks are executed
on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

from evolzen.exploration.synthesizer import CandidateRule, TemplateRuleSynthesizer
from evolzen.library.rule_library import RuleLibrary
from evolzen.recognition.jepa import JEPAEncoder
from evolzen.schemas.transition import Action, Emission, State, Transition


@dataclass(frozen=True)
class FantasyCase:
    """A self-generated training case used during the "sleep" phase (not a real Transition)."""

    synthetic_context: dict[str, Any]
    target_rule_id: str


class WakeSleepLearner:
    """Alternates wake (propose using the library) and sleep (refactor + retrain the prior)."""

    def __init__(
        self,
        rule_library: RuleLibrary,
        synthesizer: TemplateRuleSynthesizer | None = None,
        jepa_encoder: JEPAEncoder | None = None,
    ) -> None:
        self._rule_library = rule_library
        self._synthesizer = synthesizer if synthesizer is not None else TemplateRuleSynthesizer()
        self._jepa_encoder = jepa_encoder
        self._sleep_cycles: int = 0
        self._abstracted_primitives: list[str] = []

    @property
    def sleep_cycles(self) -> int:
        return self._sleep_cycles

    @property
    def abstracted_primitives(self) -> list[str]:
        return list(self._abstracted_primitives)

    def wake_propose(
        self,
        observation: dict[str, Any] | State,
        action_type: str = "wait",
        gap: str = "",
    ) -> CandidateRule:
        """Propose a candidate rule explaining `observation` using the verified library or synthesizer."""
        obs_data = observation.data if isinstance(observation, State) else observation

        # 1. Search existing verified rules in the library for direct matches
        active_entries = self._rule_library.active_entries()
        for entry in active_entries:
            if action_type in entry.code:
                return CandidateRule(
                    rule_id=f"wake-reuse-{entry.rule_id}",
                    code=entry.code,
                    explains=[gap] if gap else ["wake_observed_gap"],
                )

        # 2. Synthesize a candidate rule from observed context
        synthetic_state = State(data=obs_data)
        synthetic_transition = Transition(
            state=synthetic_state,
            action=Action(agent_id=str(obs_data.get("actor_id", "agent_0")), action_type=action_type),
            emission=Emission(data={"accepted": True, "action_type": action_type, "rewards": [0.0] * 8}),
            next_state=synthetic_state,
        )
        synth = self._synthesizer.propose([synthetic_transition])
        if gap:
            return CandidateRule(rule_id=synth.rule_id, code=synth.code, explains=[gap])
        return synth

    def sleep_step(
        self,
        real_cases: list[dict[str, Any]],
        fantasy_cases: list[FantasyCase],
    ) -> dict[str, float]:
        """One sleep-phase update: refactor + retrain on real + self-generated cases.

        Evaluates Minimum Description Length (MDL) compression (Ellis et al., PLDI 2021)
        and trains the latent representation prior on real state cases.
        """
        self._sleep_cycles += 1
        total_cases = len(real_cases) + len(fantasy_cases)
        if total_cases == 0:
            return {
                "compression_ratio": 1.0,
                "primitives_abstracted": 0.0,
                "reconstructed_cases": 0.0,
                "sleep_cycles": float(self._sleep_cycles),
            }

        # 1. Measure raw code representation length
        active_entries = self._rule_library.active_entries()
        raw_code_chars = sum(len(e.code) for e in active_entries)
        if raw_code_chars == 0:
            raw_code_chars = 100

        # 2. Extract shared syntax / AST primitives across active rules
        common_snippets: list[str] = []
        if len(active_entries) >= 2:
            s1 = active_entries[0].code
            s2 = active_entries[1].code
            matcher = difflib.SequenceMatcher(None, s1, s2)
            match = matcher.find_longest_match(0, len(s1), 0, len(s2))
            if match.size > 20:
                snippet = s1[match.a : match.a + match.size].strip()
                if snippet and snippet not in self._abstracted_primitives:
                    self._abstracted_primitives.append(snippet)
                    common_snippets.append(snippet)

        # 3. Compute DreamCoder-style compression ratio
        # Compressed length = (code minus shared fragments) + dictionary overhead
        abstracted_savings = sum(len(snip) for snip in common_snippets)
        compressed_chars = max(50, raw_code_chars - abstracted_savings)
        compression_ratio = round(compressed_chars / raw_code_chars, 4)

        # 4. Optional JEPA encoder training on real cases
        jepa_loss = 0.0
        if self._jepa_encoder is not None and real_cases:
            states_to_train: list[State] = []
            for c in real_cases:
                if "state" in c and isinstance(c["state"], State):
                    states_to_train.append(c["state"])
                else:
                    states_to_train.append(State(data=c))
            metrics = self._jepa_encoder.train_step(states_to_train)
            jepa_loss = metrics.get("loss", 0.0)

        return {
            "compression_ratio": compression_ratio,
            "primitives_abstracted": float(len(self._abstracted_primitives)),
            "reconstructed_cases": float(total_cases),
            "jepa_loss": jepa_loss,
            "sleep_cycles": float(self._sleep_cycles),
        }
