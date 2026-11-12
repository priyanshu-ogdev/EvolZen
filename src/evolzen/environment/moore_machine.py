"""Phase 1.1 interactive transition-system specification (Phase 0 compatibility module).

Per ADR 0005 and Tycho (arXiv:2607.28287), the formal object is a seeded, typed
interactive transition system `(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})`.
The `moore_machine.py` module name and `MooreMachineSpec` dataclass are retained for
compatibility with downstream exploration and evaluation consumers. This specification is an
EvolZen design choice and remains empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from evolzen.schemas.world import ActionType


@dataclass(frozen=True)
class MooreMachineSpec:
    """Declares the action and emission vocabulary of one environment domain."""

    name: str
    action_types: tuple[str, ...]
    emission_fields: tuple[str, ...]
    description: str = field(default="")


SOCIAL_SANDBOX_SPEC = MooreMachineSpec(
    name="evolzen-social-sandbox-v1",
    action_types=tuple(action.value for action in ActionType),
    emission_fields=(
        "accepted",
        "reason",
        "tick",
        "step_index",
        "actor_id",
        "action_type",
        "rewards",
        "growth_events",
        "invariant_passed",
        "exogenous_applied",
        "evidence_id",
    ),
    description=(
        "Persistent, event-sourced discrete social sandbox over locations, resources, "
        "agents/lineages, artifacts/capabilities, contracts/institutions, norms, and shocks."
    ),
)
