"""The interactive transition-system schema (Phase 1.1).

`evolzen.environment` is formalized as a seeded, typed interactive transition system —
states, typed actions, explicit exogenous inputs, seeds, and typed emissions — following
Tycho (arXiv:2607.28287) and ADR 0005. Every outcome logged through this schema must be
independently re-derivable from `(state, action, exogenous_input, seed)` alone. These
contracts are an EvolZen design choice and remain empirically untested until Phase 1.1
experiments are run.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class State(BaseModel):
    """A single, deterministic environment state.

    `data` holds canonical JSON-serializable state. Concrete domain implementations must
    ensure two `State` instances with equal `data` are genuinely equivalent, since
    `evolzen.exploration.verifier` and exact replay compare state equivalence.
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


class ExogenousInput(BaseModel):
    """Explicit exogenous input applied alongside or between agent actions (Phase 1.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tick: int = Field(default=0, ge=0)
    events: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class Emission(BaseModel):
    """What the environment emits in response to an action — the observable outcome."""

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]


class Transition(BaseModel):
    """One `(state, action, exogenous_input, seed) -> (emission, next_state)` record.

    This is the unit `evolzen.environment` logs, `evolzen.exploration.verifier` checks
    candidate rules against (exact reproduction of every recorded transition), and
    `evolzen.library` is built from. `evolzen.predictor` / `evolzen.recognition` never
    mutate these records; they only read them.
    """

    model_config = ConfigDict(frozen=True)

    transition_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    state: State
    action: Action
    exogenous_input: ExogenousInput = Field(default_factory=ExogenousInput)
    seed: int = 0
    emission: Emission
    next_state: State
