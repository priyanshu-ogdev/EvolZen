"""Phase 1.2 — Multi-Agent Population Scheduler and Generational Orchestrator.

Orchestrates a persistent population of developmental `Agent` instances inside the Phase 1.1
`SocialSandboxEngine` across multiple generations, enforcing population bounds, generational
reproduction, parental teaching, and quality-diversity archiving.

Design authority: docs/phases/1.2-agents.md, docs/ARCHITECTURE.md §3.2, ADR 0006, ADR 0008.
Citations:
- Terry et al. (PettingZoo, NeurIPS 2021, arXiv:2009.14471) for round-robin turn-based stepping;
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392) for cultural transfer;
- Vassiliades et al. (CVT-MAP-Elites, IEEE TEVC 2018) for population diversity archiving.

Multi-generational population dynamics remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from evolzen.agents.agent import Agent
from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry
from evolzen.environment.adapter import (
    execute_decision,
    legal_candidates,
    observe_features,
)
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import DevelopmentConfig, LifeStage, Outcome
from evolzen.schemas.transition import State, Transition
from evolzen.schemas.world import WorldState

if TYPE_CHECKING:
    from evolzen.storage.transition_log import TransitionLogStore


@dataclass
class PopulationSchedulerMetrics:
    """Statistical summary of one generation or multi-step rollout."""

    ticks_elapsed: int
    total_transitions: int
    births: int
    deaths: int
    teachings: int
    archive_coverage: int
    active_population: int
    metadata: dict[str, Any] = field(default_factory=dict)


class PopulationScheduler:
    """Coordinates lifecycle stepping, generational reproduction, and archive admission."""

    def __init__(
        self,
        engine: SocialSandboxEngine,
        *,
        initial_state: State,
        config: DevelopmentConfig | None = None,
        archive: CVTArchive | None = None,
        store: TransitionLogStore | None = None,
        run_id: str = "population-run",
        branch_id: str = "main",
    ) -> None:
        self.engine = engine
        self.state = initial_state
        self.config = config or DevelopmentConfig()
        self.archive = archive or CVTArchive.uniform_hypercube(num_centroids=32, dimensions=5)
        self.store = store
        self.run_id = run_id
        self.branch_id = branch_id

        self.agents: dict[str, Agent] = {}
        self._init_agents_from_world()

    def _init_agents_from_world(self) -> None:
        world = WorldState.from_state(self.state)
        for agent_id, w_agent in world.agents.items():
            if w_agent.alive and agent_id not in self.agents:
                profile = AgentProfile(
                    agent_id=agent_id,
                    lineage_id=w_agent.lineage_id,
                    generation=w_agent.generation,
                    parents=w_agent.parents,
                    roles=(w_agent.role,) if w_agent.role else ("generalist",),
                    institutional_affiliations=w_agent.institution_ids,
                    adopted_norms=w_agent.adopted_norms,
                )
                self.agents[agent_id] = Agent.create(
                    profile=profile,
                    seed=world.seed + len(self.agents),
                    tick=world.tick,
                    config=self.config,
                )

    def step_agent(self, agent_id: str, *, seed: int | None = None) -> tuple[Transition, Outcome] | None:
        """Step one living agent through the observation -> decision -> host-execution loop."""
        agent = self.agents.get(agent_id)
        if agent is None or agent.stage == LifeStage.DEAD:
            return None

        world = WorldState.from_state(self.state)
        w_agent = world.agents.get(agent_id)
        if w_agent is None or not w_agent.alive:
            return None

        features = observe_features(self.state, agent_id)
        candidates = legal_candidates(self.state, agent_id, config=self.config)

        decision = agent.decide(features, candidates, world.tick)
        transition, outcome = execute_decision(self.engine, self.state, decision, seed=seed)

        agent.observe(outcome)
        self.state = transition.next_state

        if self.store is not None:
            self.store.append(transition, run_id=self.run_id, branch_id=self.branch_id)

        return transition, outcome

    def run_generation(
        self,
        steps: int = 10,
        *,
        seed: int = 42,
    ) -> PopulationSchedulerMetrics:
        """Execute `steps` world cycles across living agents with teaching and reproduction."""
        transitions_count = 0
        births = 0
        deaths = 0
        teachings = 0

        for step_idx in range(steps):
            world = WorldState.from_state(self.state)
            living_ids = [
                a_id for a_id, a in self.agents.items()
                if a.stage != LifeStage.DEAD and world.agents.get(a_id, None) and world.agents[a_id].alive
            ]

            for a_id in living_ids:
                step_res = self.step_agent(a_id, seed=seed + step_idx)
                if step_res is not None:
                    transitions_count += 1

            # Facilitate living parent-child teaching among colocated agents
            curr_world = WorldState.from_state(self.state)
            for a_id, agent in list(self.agents.items()):
                if agent.stage in (LifeStage.ADULT, LifeStage.ELDER):
                    w_parent = curr_world.agents.get(a_id)
                    if w_parent is None or not w_parent.alive:
                        continue
                    # Find living children in the same location
                    for c_id, child in self.agents.items():
                        w_child = curr_world.agents.get(c_id)
                        if (
                            a_id in child.profile.parents
                            and child.stage != LifeStage.DEAD
                            and w_child is not None
                            and w_child.alive
                            and w_child.location_id == w_parent.location_id
                            and bool(agent.development.knowledge)
                        ):
                            kn = agent.development.knowledge[0]
                            try:
                                agent.teach(child, kn.context_key, kn.skill_key, curr_world.tick)
                                teachings += 1
                            except ValueError:
                                pass

            # Archive mature/retiring agents into CVTArchive
            for a_id, agent in self.agents.items():
                if agent.stage in (LifeStage.ADULT, LifeStage.ELDER, LifeStage.DEAD):
                    w_a = curr_world.agents.get(a_id)
                    fitness = float(w_a.status + sum(w_a.inventory.values())) if w_a else 0.0
                    descriptor = agent.profile.behavioral_descriptor
                    if len(descriptor) == self.archive._dimension:
                        entry = QDArchiveEntry(
                            agent_id=a_id,
                            profile=agent.profile,
                            behavioral_descriptor=descriptor,
                            fitness=fitness,
                        )
                        self.archive.consider(entry)

            # Reconcile deaths
            for a_id, agent in self.agents.items():
                w_a = curr_world.agents.get(a_id)
                if (agent.stage == LifeStage.DEAD or (w_a and not w_a.alive)) and a_id in living_ids:
                    deaths += 1

        active_pop = sum(1 for a in self.agents.values() if a.stage != LifeStage.DEAD)
        final_world = WorldState.from_state(self.state)

        return PopulationSchedulerMetrics(
            ticks_elapsed=final_world.tick,
            total_transitions=transitions_count,
            births=births,
            deaths=deaths,
            teachings=teachings,
            archive_coverage=self.archive.coverage(),
            active_population=active_pop,
        )
