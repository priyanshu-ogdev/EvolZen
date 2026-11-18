"""Phase 1.2 — Multi-Agent Population Scheduler and Generational Orchestrator.

Orchestrates a persistent population of developmental `Agent` instances inside the Phase 1.1
`SocialSandboxEngine` across multiple generations, enforcing population bounds, generational
reproduction, parental teaching, genealogical lineage tracking, and quality-diversity archiving.

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

import contextlib
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
from evolzen.schemas.agent_profile import (
    AgentProfile,
    CommunicationGraphSnapshot,
    LineageNode,
    LineageSnapshot,
    PopulationSnapshot,
)
from evolzen.schemas.development import (
    Candidate,
    DevelopmentConfig,
    LifeStage,
    Outcome,
)
from evolzen.schemas.transition import ExogenousInput, State, Transition
from evolzen.schemas.world import ActionType, WorldState

if TYPE_CHECKING:
    from evolzen.agents.inference import InferenceBackend
    from evolzen.agents.trainer import CuratedTrajectory, OfflineAdapterTrainer, ValidationResult
    from evolzen.economy.manuals import ManualStore
    from evolzen.library.rule_library import RuleLibrary
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
    extinctions: int = 0
    replacements: int = 0
    specialization_hhi: float = 0.0
    interaction_density: float = 0.0
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
        rule_library: RuleLibrary | None = None,
        backend: InferenceBackend | None = None,
        run_id: str = "population-run",
        branch_id: str = "main",
        executor: str = "sequential",
    ) -> None:
        self.engine = engine
        self.state = initial_state
        self.config = config or DevelopmentConfig()
        self.archive = archive or CVTArchive.uniform_hypercube(num_centroids=32, dimensions=5)
        self.store = store
        self.manual_store = manual_store
        self.rule_library = rule_library
        self.backend = backend
        self.run_id = run_id
        self.branch_id = branch_id
        self.executor = executor.lower().strip()

        # Synchronize active capabilities from RuleLibrary into WorldState
        if self.rule_library is not None:
            world = WorldState.from_state(self.state)
            updated_world = self.rule_library.export_capabilities_to_world(world)
            self.state = updated_world.to_state()

        self.agents: dict[str, Agent] = {}
        self.inactive_agents: dict[str, Agent] = {}
        self.lineage_nodes: dict[str, LineageNode] = {}
        self.interactions: dict[str, dict[str, int]] = {}
        self._previous_active_lineages: set[str] = set()

        self._init_agents_from_world()

    def record_interaction(self, source_id: str, target_id: str) -> None:
        """Record a directed social, trade, or teaching interaction between two agents."""
        if source_id == target_id:
            return
        targets = self.interactions.setdefault(source_id, {})
        targets[target_id] = targets.get(target_id, 0) + 1

    @property
    def world(self) -> WorldState:
        """Current WorldState projection reconstructed from self.state."""
        return WorldState.from_state(self.state)

    def compute_interaction_metrics(self) -> tuple[int, float]:
        """Compute total interaction volume and directed edge density across active agents.

        Returns:
            Tuple of (total_interactions, edge_density in [0.0, 1.0]).
        """
        world = WorldState.from_state(self.state)
        active_ids = [
            a_id for a_id, w_a in world.agents.items()
            if w_a.alive and stage_at(self.agents[a_id].development, world.tick) != LifeStage.DEAD
            if a_id in self.agents
        ]
        n = len(active_ids)
        total_possible = n * (n - 1) if n > 1 else 1

        total_interactions = sum(
            count
            for s, targets in self.interactions.items()
            for t, count in targets.items()
        )
        active_edges = sum(
            1
            for s, targets in self.interactions.items()
            for t in targets
            if s in active_ids and t in active_ids
        )
        density = min(1.0, round(active_edges / total_possible, 4)) if total_possible > 0 else 0.0
        return total_interactions, density

    def compute_specialization(self) -> tuple[float, float, dict[str, int]]:
        """Calculate Herfindahl-Hirschman Index (HHI) and Shannon entropy of vocational roles.

        Returns:
            Tuple of (hhi in [0.0, 1.0], shannon_entropy >= 0.0, role_counts).
        """
        world = WorldState.from_state(self.state)
        living_agents = [
            w_a for a_id, w_a in world.agents.items()
            if w_a.alive and stage_at(self.agents[a_id].development, world.tick) != LifeStage.DEAD
            if a_id in self.agents
        ]
        if not living_agents:
            return 0.0, 0.0, {}

        role_counts: dict[str, int] = {}
        for w_a in living_agents:
            role = w_a.role or "generalist"
            role_counts[role] = role_counts.get(role, 0) + 1

        total = float(len(living_agents))
        hhi = sum((count / total) ** 2 for count in role_counts.values())
        entropy = -sum((count / total) * math.log(count / total) for count in role_counts.values())
        return round(hhi, 4), round(entropy, 4), role_counts

    def create_lineage_snapshot(self, lineage_id: str) -> LineageSnapshot:
        """Construct an immutable genealogical snapshot for `lineage_id`."""
        world = WorldState.from_state(self.state)
        nodes_in_lineage = {
            k: v for k, v in self.lineage_nodes.items() if v.lineage_id == lineage_id
        }
        active_members = tuple(
            a_id
            for a_id in sorted(nodes_in_lineage)
            if (w_a := world.agents.get(a_id)) is not None and w_a.alive
        )
        is_extinct = len(active_members) == 0 and len(nodes_in_lineage) > 0
        founder_id = (
            min(nodes_in_lineage.keys(), key=lambda k: nodes_in_lineage[k].born_at)
            if nodes_in_lineage
            else lineage_id
        )
        max_gen = max((v.generation for v in nodes_in_lineage.values()), default=0)

        return LineageSnapshot(
            lineage_id=lineage_id,
            founder_id=founder_id,
            nodes=nodes_in_lineage,
            active_members=active_members,
            is_extinct=is_extinct,
            extinct_at_tick=world.tick if is_extinct else None,
            total_born=len(nodes_in_lineage),
            max_generation=max_gen,
        )

    def create_population_snapshot(self) -> PopulationSnapshot:
        """Generate a complete frozen snapshot of the multi-agent population."""
        world = WorldState.from_state(self.state)
        living_agents = [
            w_a for a_id, w_a in world.agents.items()
            if w_a.alive and stage_at(self.agents[a_id].development, world.tick) != LifeStage.DEAD
            if a_id in self.agents
        ]
        wealths = [float(a.currency + sum(a.inventory.values())) for a in living_agents]
        gini = compute_gini_coefficient(wealths) if wealths else 0.0

        all_lineage_ids = sorted({n.lineage_id for n in self.lineage_nodes.values()})
        lineages_snap = {lid: self.create_lineage_snapshot(lid) for lid in all_lineage_ids}

        total_int, density = self.compute_interaction_metrics()
        comm_snap = CommunicationGraphSnapshot(
            nodes=tuple(sorted(self.agents.keys())),
            interactions={s: dict(t) for s, t in self.interactions.items()},
            total_interactions=total_int,
            edge_density=density,
        )
        hhi, entropy, role_counts = self.compute_specialization()

        return PopulationSnapshot(
            snapshot_id=f"pop-snap-{world.tick}",
            tick=world.tick,
            generation=max((a.profile.generation for a in self.agents.values()), default=0),
            total_agents=len(self.lineage_nodes),
            active_population=len(living_agents),
            profiles={a_id: a.profile for a_id, a in self.agents.items() if a_id in world.agents and world.agents[a_id].alive},
            lineages=lineages_snap,
            communication_graph=comm_snap,
            archive_coverage=self.archive.coverage(),
            gini_coefficient=gini,
            role_distribution=role_counts,
        )

    def prune_dead_agents(self, max_inactive: int = 128) -> int:
        """Tombstone and prune dead agent runtimes from active memory to prevent leaks.

        Args:
            max_inactive: Maximum historical inactive agent instances to retain.

        Returns:
            Number of agent runtimes pruned.
        """
        world = WorldState.from_state(self.state)
        dead_ids = [
            a_id
            for a_id, agent in list(self.agents.items())
            if stage_at(agent.development, world.tick) == LifeStage.DEAD
            or ((w_a := world.agents.get(a_id)) is not None and not w_a.alive)
        ]
        pruned_count = 0
        for a_id in dead_ids:
            dead_agent = self.agents.pop(a_id, None)
            if dead_agent is not None:
                self.inactive_agents[a_id] = dead_agent
                pruned_count += 1

        # Keep inactive_agents bounded
        if len(self.inactive_agents) > max_inactive:
            overflow = len(self.inactive_agents) - max_inactive
            oldest_keys = list(self.inactive_agents.keys())[:overflow]
            for k in oldest_keys:
                self.inactive_agents.pop(k, None)

        return pruned_count

    def _init_agents_from_world(self) -> int:
        """Instantiate Agent entities and genealogical records for newly born agents.

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
                    seed=world.seed + len(self.lineage_nodes),
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

                # Register genealogical node
                node = LineageNode(
                    agent_id=agent_id,
                    lineage_id=w_agent.lineage_id,
                    generation=w_agent.generation,
                    parents=w_agent.parents,
                    children=(),
                    born_at=w_agent.born_at,
                    died_at=None,
                    roles=(w_agent.role,) if w_agent.role else ("generalist",),
                    behavioral_descriptor=desc,
                )
                self.lineage_nodes[agent_id] = node

                # Update parent children linkages
                for p_id in w_agent.parents:
                    if p_id in self.lineage_nodes:
                        p_node = self.lineage_nodes[p_id]
                        if agent_id not in p_node.children:
                            self.lineage_nodes[p_id] = p_node.model_copy(
                                update={"children": (*p_node.children, agent_id)}
                            )

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
            if agent_id in self.lineage_nodes and self.lineage_nodes[agent_id].died_at is None:
                self.lineage_nodes[agent_id] = self.lineage_nodes[agent_id].model_copy(
                    update={"died_at": world.tick}
                )
            return None

        w_agent = world.agents.get(agent_id)
        if w_agent is None or not w_agent.alive:
            if agent_id in self.lineage_nodes and self.lineage_nodes[agent_id].died_at is None:
                self.lineage_nodes[agent_id] = self.lineage_nodes[agent_id].model_copy(
                    update={"died_at": world.tick}
                )
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

        # Track social/trade interaction edge if applicable
        act = transition.action
        if act.action_type == ActionType.TRADE or act.action_type == ActionType.PROPOSE_CONTRACT:
            target_cp = act.params.get("counterparty_id")
            if isinstance(target_cp, str) and target_cp:
                self.record_interaction(agent_id, target_cp)
        elif act.action_type == ActionType.FULFILL_CONTRACT:
            cid = act.params.get("contract_id")
            if isinstance(cid, str) and cid in world.contracts:
                self.record_interaction(agent_id, world.contracts[cid].proposer_id)

        if stage_at(agent.development, outcome.tick) == LifeStage.DEAD:
            agent.advance(outcome.tick)
            if agent_id in self.lineage_nodes and self.lineage_nodes[agent_id].died_at is None:
                self.lineage_nodes[agent_id] = self.lineage_nodes[agent_id].model_copy(
                    update={"died_at": outcome.tick}
                )
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

        if self.rule_library is not None:
            if transition.action.action_type == ActionType.REGISTER_CAPABILITY:
                self.rule_library.import_capabilities_from_world(WorldState.from_state(transition.next_state))
            with contextlib.suppress(Exception):
                self.rule_library.regression_bank.ingest_transition(transition)

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
                            # Record teaching interaction
                            self.record_interaction(a_id, c_id)

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
            for a_id, agent in list(self.agents.items()):
                w_a = curr_world.agents.get(a_id)
                if (
                    stage_at(agent.development, curr_world.tick) == LifeStage.DEAD
                    or (w_a and not w_a.alive)
                ) and a_id in living_ids:
                    deaths += 1
                    if a_id in self.lineage_nodes and self.lineage_nodes[a_id].died_at is None:
                        self.lineage_nodes[a_id] = self.lineage_nodes[a_id].model_copy(
                            update={"died_at": curr_world.tick}
                        )

        final_world = WorldState.from_state(self.state)
        final_living = [
            w_a for a_id, a in self.agents.items()
            if stage_at(a.development, final_world.tick) != LifeStage.DEAD
            and (w_a := final_world.agents.get(a_id)) is not None
            and w_a.alive
        ]
        active_pop = len(final_living)
        current_active_lineages = {a.lineage_id for a in final_living}

        # Compute Extinctions and Replacements
        extinctions = 0
        replacements = 0
        if self._previous_active_lineages:
            lost_lineages = self._previous_active_lineages - current_active_lineages
            extinctions = len(lost_lineages)
            if extinctions > 0 and len(current_active_lineages) > 0:
                replacements = extinctions
        self._previous_active_lineages = set(current_active_lineages)

        # Compute Specialization & Interaction Metrics
        hhi, entropy, role_counts = self.compute_specialization()
        total_interactions, interaction_density = self.compute_interaction_metrics()

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
            "active_lineage_count": len(current_active_lineages),
            "mean_gini": round(sum(gini_values) / len(gini_values), 4) if gini_values else 0.0,
            "final_gini": gini_values[-1] if gini_values else 0.0,
            "role_entropy": entropy,
            "total_interactions": total_interactions,
            "role_distribution": role_counts,
        }

        # Safe pruning of dead agents to protect memory bounds during long runs
        self.prune_dead_agents()

        # Synchronize newly registered capabilities from world state into RuleLibrary
        if self.rule_library is not None:
            self.rule_library.import_capabilities_from_world(final_world)

        return PopulationSchedulerMetrics(
            ticks_elapsed=final_world.tick,
            total_transitions=transitions_count,
            births=len(self.lineage_nodes) - initial_agent_count,
            deaths=deaths,
            teachings=teachings,
            archive_coverage=self.archive.coverage(),
            active_population=active_pop,
            extinctions=extinctions,
            replacements=replacements,
            specialization_hhi=hhi,
            interaction_density=interaction_density,
            metadata=metadata,
        )

    def run_training_cycle(
        self,
        trainer: OfflineAdapterTrainer | None = None,
        *,
        validation_split: float = 0.25,
        rehearsal_trajectories: list[CuratedTrajectory] | None = None,
    ) -> dict[str, tuple[dict[str, Any], ValidationResult]]:
        """Run an offline private adapter training and promotion cycle across active lineages.

        Extracts transitions from `self.store`, curates trajectories, optimizes LoRA parameters,
        evaluates held-out validation performance and retention, and applies promoted checkpoints.

        Args:
            trainer: OfflineAdapterTrainer instance (creates a default one if omitted).
            validation_split: Fraction of trajectories to reserve for held-out validation.
            rehearsal_trajectories: Optional CLEAR historical rehearsal trajectories.

        Returns:
            Dictionary mapping lineage_id to (training_report, validation_result).
        """
        if self.store is None:
            return {}

        from evolzen.agents.trainer import OfflineAdapterTrainer

        active_trainer = trainer or OfflineAdapterTrainer()
        results = active_trainer.extract_and_train_from_store(
            self.store,
            run_id=self.run_id,
            validation_split=validation_split,
            rehearsal_trajectories=rehearsal_trajectories,
        )

        # Update profiles of living agents in promoted lineages with new checkpoint IDs
        for lineage_id, (_report, val_res) in results.items():
            if val_res.promoted:
                for agent in self.agents.values():
                    if agent.profile.lineage_id == lineage_id:
                        agent.profile = agent.profile.model_copy(
                            update={"adapter_checkpoint": val_res.checkpoint_id}
                        )

        return results
