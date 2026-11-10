"""The growing, frozen, non-overwriting verified-rule library (Phase 1.5).

Verified rules (that passed `evolzen.exploration.verifier.Verifier`) become frozen entries
here. A new entry spawns only when no existing rule adequately explains a new observation — the
same "does this fit anything I already have" logic as a Dirichlet process mixture model
(Ferguson, 1973). Existing entries are never overwritten; the Phase 1.5 success metric is
exactly zero forgetting on a held-out regression bank across repeated additions.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from evolzen.exploration.synthesizer import CandidateRule

RoutingConfidenceFn = Callable[[CandidateRule, CandidateRule], float]


@dataclass
class RuleLibrary:
    """Append-only (per Phase 1.5) collection of verified rules."""

    _entries: dict[str, CandidateRule] = field(default_factory=dict)

    def spawn_if_novel(
        self, rule: CandidateRule, routing_confidence_fn: RoutingConfidenceFn, threshold: float = 0.5
    ) -> bool:
        """Add `rule` as a new entry only if no existing entry explains it well enough.

        Returns True if a new entry was spawned.
        """
        best_confidence = max(
            (routing_confidence_fn(rule, existing) for existing in self._entries.values()),
            default=0.0,
        )
        if best_confidence >= threshold:
            return False  # an existing entry already explains this well enough
        self._entries[rule.rule_id] = rule
        return True

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, rule_id: str) -> CandidateRule | None:
        return self._entries.get(rule_id)
