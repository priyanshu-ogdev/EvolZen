"""Phase 1.2 — Multi-Agent Population Scheduler and Generational Orchestrator.

Orchestrates a persistent population of developmental `Agent` instances inside the Phase 1.1
`SocialSandboxEngine` across multiple generations, enforcing population bounds, generational
reproduction, parental teaching, and quality-diversity archiving.

Design authority: docs/phases/1.2-agents.md, docs/ARCHITECTURE.md §3.2, ADR 0006, ADR 0008.
Citations:
- Terry et al. (PettingZoo, NeurIPS 2021, arXiv:2009.14471) for round-robin turn-based stepping;
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392) for cultural transfer;
- Vassiliades et al. (CVT-MAP-Elites, IEEE TEVC 2018) for population diversity archiving;
- Agno (Manual-guided agents and cultural transfer, 2026) for living manual transmission;
- Henrich & Boyd (J. Theor. Biol. 2002) for norm retention and cultural diffusion under environmental scarcity;
- Zheng et al. (Science Advances 2022, doi:10.1126/sciadv.abk2607) for wealth Gini dynamics under resource shocks.

Multi-generational population dynamics remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from evolzen.agents.agent import Agent
from evolzen.agents.development.lifecycle import stage_at
from evolzen.agents.qd_archive import (
    CVTArchive,
    QDArchiveEntry,
    compute_behavioral_descriptor,
)
from evolzen.economy.metrics import compute_gini_coefficient
from evolzen.environment.adapter import (
    execute_decision,
    legal_candidates,
    observe_features,
)
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import (
    Candidate,
    DevelopmentConfig,
    LifeStage,
    Outcome,
)
from evolzen.schemas.transition import ExogenousInput, State, Transition
from evolzen.schemas.world import WorldState

if TYPE_CHECKING:
    from evolzen.agents.inference import InferenceBackend
    from evolzen.economy.manuals import ManualStore
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
        manual_store: ManualStore | None = None,
        backend: InferenceBackend | None = None,
        run_id: str = "population-run",
        branch_id: str = "main",
    ) -> None:
        self.engine = engine
        self.state = initial_state
        self.config = config or DevelopmentConfig()
        self.archive = archive or CVTArchive.uniform_hypercube(num_centroids=32, dimensions=5)
        self.store = store
        self.manual_store = manual_store
        self.backend = backend
        self.run_id = run_id
        self.branch_id = branch_id

        self.agents: dict[str, Agent] = {}
        self._init_agents_from_world()

    def _init_agents_from_world(self) -> int:
        """Instantiate Agent entities for newly born agents in the world.

        Returns:
            Number of newly registered agents.
        """
        world = WorldState.from_state(self.state)
        new_count = 0
        for agent_id, w_agent in sorted(world.agents.items()):
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
                parent_agents = tuple(
                    self.agents[p_id]
                    for p_id in w_agent.parents
                    if p_id in self.agents
                    and stage_at(self.agents[p_id].development, world.tick)
                    in (LifeStage.ADULT, LifeStage.ELDER)
                )
                init_tick = w_agent.born_at if not parent_agents else world.tick
                agent = Agent.create(
                    profile=profile,
                    seed=world.seed + len(self.agents),
                    tick=init_tick,
                    config=self.config,
                    parents=parent_agents,
                    backend=self.backend,
                )
                desc = compute_behavioral_descriptor(
                    agent.development.birth.genome,
                    profile,
                    dimension=self.archive._dimension,
                )
                agent.profile = profile.model_copy(update={"behavioral_descriptor": desc})
                if world.tick > agent.tick:
                    agent.advance(world.tick)
                self.agents[agent_id] = agent
                new_count += 1
        return new_count

    def step_agent(
        self,
        agent_id: str,
        *,
        seed: int | None = None,
        exogenous_input: ExogenousInput | None = None,
    ) -> tuple[Transition, Outcome] | None:
        """Step one living agent through the observation -> decision -> host-execution loop."""
        agent = self.agents.get(agent_id)
        if agent is None:
            return None

        world = WorldState.from_state(self.state)
        if stage_at(agent.development, world.tick) == LifeStage.DEAD:
            if agent.stage != LifeStage.DEAD:
                agent.advance(world.tick)
            return None

        w_agent = world.agents.get(agent_id)
        if w_agent is None or not w_agent.alive:
            return None

        features = observe_features(self.state, agent_id)
        candidates = legal_candidates(self.state, agent_id, config=self.config)

        # Ensure juvenile/reproductive agents withdraw from communal silos under famine/drought stress
        loc = world.locations.get(w_agent.location_id)
        loc_food = loc.resources.get("food", 0) if loc else 0
        under_famine_stress = (
            w_agent.energy < 0.65
            or w_agent.inventory.get("food", 0) == 0
            or loc_food == 0
            or exogenous_input is not None
        )
        withdraw_cand = next(
            (
                c
                for c in candidates
                if c.action_id.startswith("withdraw_institution:") and ":food:" in c.action_id
            ),
            None,
        )
        consume_cand = next(
            (c for c in candidates if c.action_id.startswith("consume:food")),
            None,
        )

        effective_candidates: tuple[Candidate, ...]
        if (
            w_agent.energy < 0.4
            and w_agent.inventory.get("food", 0) >= 1
            and consume_cand is not None
        ):
            effective_candidates = (consume_cand,)
        elif under_famine_stress and withdraw_cand is not None and w_agent.energy < 0.85:
            effective_candidates = (withdraw_cand,)
        else:
            effective_candidates = candidates

        if self.backend is not None:
            if agent.backend is None:
                agent.backend = self.backend
            action = agent.act_with_backend(
                features,
                effective_candidates,
                world.tick,
                world_context={"tick": world.tick, "agent_id": agent_id, "location_id": w_agent.location_id},
            )
            transition = self.engine.step(
                self.state,
                action,
                exogenous_input=exogenous_input,
                seed=seed,
            )
            raw_rewards = transition.emission.data.get("rewards", [0.0] * 8)
            rewards = tuple(float(v) for v in raw_rewards)
            if len(rewards) != 8:
                rewards = (0.0,) * 8
            next_tick = int(transition.emission.data.get("tick", world.tick + 1))
            pending = agent.development.pending
            seq = pending.sequence if pending is not None else 1
            act_id = pending.candidate.action_id if pending is not None else action.action_type
            outcome = Outcome(
                agent_id=agent_id,
                sequence=seq,
                tick=next_tick,
                action_id=act_id,
                evidence_id=str(transition.transition_id),
                rewards=rewards,
                verified=bool(transition.emission.data.get("invariant_passed", False)),
            )
        else:
            decision = agent.decide(features, effective_candidates, world.tick, seed=seed)
            transition, outcome = execute_decision(
                self.engine,
                self.state,
                decision,
                exogenous_input=exogenous_input,
                seed=seed,
            )

        if stage_at(agent.development, outcome.tick) == LifeStage.DEAD:
            agent.advance(outcome.tick)
        elif outcome.verified and agent.development.pending is not None:
            try:
                agent.observe(outcome)
            except ValueError:
                agent.advance(outcome.tick)
        else:
            agent.advance(outcome.tick)
        self.state = transition.next_state
        self._init_agents_from_world()

        if self.store is not None:
            self.store.append(transition, run_id=self.run_id, branch_id=self.branch_id)

        return transition, outcome

    def run_generation(
        self,
        steps: int = 10,
        *,
        seed: int = 42,
        drought_interval: int = 0,
        drought_severity: float = 0.5,
    ) -> PopulationSchedulerMetrics:
        """Execute `steps` world cycles across living agents with teaching and reproduction.

        Args:
            steps: Number of world cycles across living agents.
            seed: Simulation PRNG seed for deterministic stepping.
            drought_interval: Period (in ticks) between exogenous resource scarcity droughts. 0 disables.
            drought_severity: Fractional severity [0.0, 1.0] of resource scarcity during drought.
        """
        transitions_count = 0
        initial_agent_count = len(self.agents)
        deaths = 0
        teachings = 0
        drought_periods = 0
        drought_ticks = 0
        was_in_drought = False
        gini_values: list[float] = []

        drought_severity = max(0.0, min(1.0, float(drought_severity)))

        for step_idx in range(steps):
            world = WorldState.from_state(self.state)
            living_ids = [
                a_id for a_id, a in self.agents.items()
                if stage_at(a.development, world.tick) != LifeStage.DEAD
                and (w_a := world.agents.get(a_id)) is not None
                and w_a.alive
            ]

            for a_id in living_ids:
                curr_world = WorldState.from_state(self.state)
                in_drought = (
                    drought_interval > 0
                    and (curr_world.tick % drought_interval) < max(1, drought_interval // 4)
                )
                exog: ExogenousInput | None = None
                if in_drought:
                    drought_ticks += 1
                    if not was_in_drought:
                        drought_periods += 1
                    was_in_drought = True
                    exog = ExogenousInput(
                        tick=curr_world.tick + 1,
                        events=(
                            {
                                "type": "shock",
                                "deplete_fraction": drought_severity,
                                "shock_factor": round(max(0.0, min(1.0, 1.0 - drought_severity)), 4),
                            },
                        ),
                    )
                else:
                    was_in_drought = False

                step_res = self.step_agent(
                    a_id,
                    seed=seed + step_idx,
                    exogenous_input=exog,
                )
                if step_res is not None:
                    transitions_count += 1

            # Detect newly born agents
            self._init_agents_from_world()

            # Record macroeconomic state for Gini tracking
            post_step_world = WorldState.from_state(self.state)
            living_agents_now = [
                w_a for a_id, a in self.agents.items()
                if stage_at(a.development, post_step_world.tick) != LifeStage.DEAD
                and (w_a := post_step_world.agents.get(a_id)) is not None
                and w_a.alive
            ]
            if living_agents_now:
                wealths = [float(a.currency + sum(a.inventory.values())) for a in living_agents_now]
                gini_values.append(compute_gini_coefficient(wealths))

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
                        ):
                            # 1. Empirical skill knowledge teaching
                            if bool(agent.development.knowledge):
                                kn = agent.development.knowledge[0]
                                try:
                                    agent.teach(child, kn.context_key, kn.skill_key, curr_world.tick)
                                    teachings += 1
                                except ValueError:
                                    pass

                            # 2. Living manual hypothesis transmission
                            if self.manual_store is not None:
                                active_entries = self.manual_store.active_entries()
                                if active_entries:
                                    try:
                                        agent.teach_manual(child, active_entries[-1], curr_world.tick)
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
                if (stage_at(agent.development, curr_world.tick) == LifeStage.DEAD or (w_a and not w_a.alive)) and a_id in living_ids:
                    deaths += 1

        final_world = WorldState.from_state(self.state)
        final_living = [
            w_a for a_id, a in self.agents.items()
            if stage_at(a.development, final_world.tick) != LifeStage.DEAD
            and (w_a := final_world.agents.get(a_id)) is not None
            and w_a.alive
        ]
        active_pop = len(final_living)
        active_lineages = len({a.lineage_id for a in final_living})

        if len(gini_values) > 1:
            mean_g = sum(gini_values) / len(gini_values)
            var_g = sum((g - mean_g) ** 2 for g in gini_values) / len(gini_values)
            gini_volatility = round(math.sqrt(var_g), 4)
        else:
            gini_volatility = 0.0

        metadata: dict[str, Any] = {
            "drought_periods": drought_periods,
            "drought_ticks": drought_ticks,
            "drought_interval": drought_interval,
            "drought_severity": drought_severity,
            "gini_volatility": gini_volatility,
            "active_lineage_count": active_lineages,
            "mean_gini": round(sum(gini_values) / len(gini_values), 4) if gini_values else 0.0,
            "final_gini": gini_values[-1] if gini_values else 0.0,
        }

        return PopulationSchedulerMetrics(
            ticks_elapsed=final_world.tick,
            total_transitions=transitions_count,
            births=len(self.agents) - initial_agent_count,
            deaths=deaths,
            teachings=teachings,
            archive_coverage=self.archive.coverage(),
            active_population=active_pop,
            metadata=metadata,
        )
