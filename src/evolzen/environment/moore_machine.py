"""The Moore-machine formalization backing the Phase 1.1 environment.

Following Tycho (arXiv:2607.28287): the environment is treated as a deterministic rendered
Moore machine — states, typed actions, typed emissions. `evolzen.schemas.transition` holds the
concrete data types; this module holds the *specification* of a machine (its action space and
emission space) that a concrete `Environment` implementation must satisfy.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MooreMachineSpec:
    """Declares the shape of one environment domain.

    A concrete Phase 1.1 domain (negotiation game / market sim / code-with-tests) provides one
    of these, describing what action types and emission fields it supports, so that
    `evolzen.exploration.synthesizer` (an off-the-shelf coding-agent harness or a bespoke one)
    knows what it's working with without inspecting the environment's internals.
    """

    name: str
    action_types: tuple[str, ...]
    emission_fields: tuple[str, ...]
    description: str = field(default="")
