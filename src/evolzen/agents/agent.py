"""Phase 1.2 — Unified Agent Class and Developmental Runtime.

Implements the unified `Agent` entity combining persistent social identity (`AgentProfile`),
the eight-coordinate developmental core (`AgentDevelopmentState`), and optional structured
neural generation (`InferenceBackend`).

Design authority: docs/phases/1.2-agents.md, docs/ARCHITECTURE.md §3.2, ADR 0006, ADR 0008.
Citations:
- Hayes et al. (AAMAS 2022, DOI:10.1007/s10458-022-09552-y) for multi-objective decision scalarization;
- Keramati & Gutkin (eLife 2014, DOI:10.7554/eLife.04811) for homeostatic drive-reduction utility;
- Park et al. (Generative Agents, arXiv:2304.03442) for agent memory horizon and social profile;
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392) for cultural transfer.

All neural inference and population orchestration mechanics remain empirically untested until
Phase 1.2 experiments are run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from evolzen.agents.development import (
    advance,
    born,
    decide,
    observe,
    stage_at,
    teach,
    teach_manual,
)
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import (
    AgentDevelopmentState,
    Candidate,
    Decision,
    DevelopmentConfig,
    LifeStage,
    Outcome,
    Signal,
)
from evolzen.schemas.manual import ManualEntry
from evolzen.schemas.transition import Action

if TYPE_CHECKING:
    from evolzen.agents.inference import InferenceBackend


@dataclass
class Agent:
    """Unified developmental agent in the EvolZen multi-agent population."""

    profile: AgentProfile
    development: AgentDevelopmentState = field(repr=False)
    backend: InferenceBackend | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        profile: AgentProfile,
        *,
        seed: int,
        tick: int = 0,
        config: DevelopmentConfig | None = None,
        parents: tuple[Agent, ...] = (),
        backend: InferenceBackend | None = None,
    ) -> Agent:
        """Instantiate a newborn agent with an initialized developmental state."""
        dev_parents = tuple(p.development for p in parents)
        dev_state = born(
            agent_id=profile.agent_id,
            seed=seed,
            tick=tick,
            config=config,
            parents=dev_parents,
        )
        return cls(profile=profile, development=dev_state, backend=backend)

    @property
    def agent_id(self) -> str:
        """Authoritative identifier of this agent."""
        return self.profile.agent_id

    @property
    def tick(self) -> int:
        """Current internal developmental clock tick."""
        return self.development.tick

    @property
    def age(self) -> int:
        """Elapsed ticks since birth."""
        return self.development.tick - self.development.birth.born_at

    @property
    def stage(self) -> LifeStage:
        """Current developmental life stage of the agent."""
        return stage_at(self.development, self.tick)

    def advance(self, tick: int) -> None:
        """Advance the agent's developmental lifecycle to `tick`."""
        self.development = advance(self.development, tick)

    def decide(
        self,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        tick: int,
        *,
        world_context: dict[str, Any] | None = None,
    ) -> Decision:
        """Select a candidate action proposal satisfying host-mediated decision invariants."""
        # Update internal motive dynamics and obtain deterministic decision proposal
        next_dev = decide(self.development, signal, candidates, tick)
        self.development = next_dev
        pending = self.development.pending
        if pending is None:
            raise RuntimeError(f"Agent {self.agent_id!r} failed to produce a pending decision")
        return pending

    def act_with_backend(
        self,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        tick: int,
        world_context: dict[str, Any],
    ) -> Action:
        """Generate a schema-constrained Action via the configured `InferenceBackend`."""
        if self.backend is None:
            raise RuntimeError(f"Agent {self.agent_id!r} has no configured InferenceBackend")
        decision = self.decide(signal, candidates, tick, world_context=world_context)
        return self.backend.generate_action(
            profile=self.profile,
            signal=signal,
            candidates=candidates,
            motive_weights=decision.ratios,
            world_context=world_context,
        )

    def observe(self, outcome: Outcome) -> None:
        """Ingest a host-verified `Outcome` receipt and update learned skill estimates."""
        self.development = observe(self.development, outcome)

    def teach(
        self,
        child: Agent,
        context_key: str,
        skill_key: str,
        tick: int,
        manual_entry: ManualEntry | None = None,
    ) -> None:
        """Transmit parental advice to `child` without mutating personal evidence or world state."""
        child.development = teach(
            self.development,
            child.development,
            context_key,
            skill_key,
            tick,
            manual_entry=manual_entry,
        )

    def teach_manual(
        self,
        child: Agent,
        manual_entry: ManualEntry,
        tick: int,
    ) -> None:
        """Transmit an active manual entry hypothesis to `child` without mutating personal evidence."""
        child.development = teach_manual(
            self.development,
            child.development,
            manual_entry,
            tick,
        )
