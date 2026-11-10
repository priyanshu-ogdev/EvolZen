"""The Moore-machine transition schema (Phase 1.1).

`evolzen.environment` is formalized as a deterministic rendered Moore machine — states, typed
actions, typed emissions — following Tycho (arXiv:2607.28287). This is a deliberate
representation choice: it's what lets `evolzen.exploration.synthesizer` be an off-the-shelf
coding-agent harness rather than a bespoke system, and it's what makes this project's transition
logs directly comparable to the published ARC-AGI-3 literature.

Every outcome logged through this schema must be independently re-derivable from the state and
action alone (Phase 1.1's success metric) — that property is what "verifiable," as this project
uses the word throughout, actually means.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class State(BaseModel):
    """A single, deterministic environment state.

    `data` is intentionally an open dict — the concrete state representation depends on which
    Phase 1.1 domain is chosen (negotiation game / market sim / code-with-tests) — but every
    concrete domain implementation must ensure two `State` instances with equal `data` are
    genuinely equivalent, since equality here is used by `evolzen.exploration.verifier`.
    """

    model_config = ConfigDict(frozen=True)

    state_id: UUID = Field(default_factory=uuid4)
    data: dict[str, Any]


class Action(BaseModel):
    """A single typed action taken by an agent."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    action_type: str
    params: dict[str, Any] = Field(default_factory=dict)


class Emission(BaseModel):
    """What the environment emits in response to an action — the observable outcome."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]


class Transition(BaseModel):
    """One (state, action) -> (emission, next_state) record.

    This is the unit `evolzen.environment` logs, `evolzen.exploration.verifier` checks
    candidate rules against (exact reproduction of every recorded transition, not "fits well"),
    and `evolzen.library` is built from. `evolzen.predictor` / `evolzen.recognition` never
    mutate these records; they only read them.
    """

    model_config = ConfigDict(frozen=True)

    transition_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    state: State
    action: Action
    emission: Emission
    next_state: State
