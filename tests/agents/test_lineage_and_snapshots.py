"""Unit tests for Phase 1.2 lineage snapshots, population metrics, and demographic tracking."""
from __future__ import annotations

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.agent_profile import (
    AgentProfile,
    LineageNode,
    LineageSnapshot,
    PopulationSnapshot,
)
from evolzen.schemas.development import DevelopmentConfig
from evolzen.schemas.world import WorldState


def test_lineage_node_and_snapshots_schemas() -> None:
    """Verifies that LineageNode, LineageSnapshot, and PopulationSnapshot instantiate and serialize."""
    node1 = LineageNode(
        agent_id="agent-0",
        lineage_id="lineage-alpha",
        generation=0,
        parents=(),
        children=("agent-1",),
        born_at=0,
        died_at=100,
        roles=("gatherer",),
        behavioral_descriptor=(0.1, 0.2, 0.3, 0.4, 0.5),
    )
    node2 = LineageNode(
        agent_id="agent-1",
        lineage_id="lineage-alpha",
        generation=1,
        parents=("agent-0",),
        children=(),
        born_at=25,
        died_at=None,
        roles=("craftsman",),
        behavioral_descriptor=(0.2, 0.3, 0.4, 0.5, 0.6),
    )

    lin_snap = LineageSnapshot(
        lineage_id="lineage-alpha",
        founder_id="agent-0",
        nodes={"agent-0": node1, "agent-1": node2},
        active_members=("agent-1",),
        is_extinct=False,
        extinct_at_tick=None,
        total_born=2,
        max_generation=1,
    )
    assert lin_snap.is_extinct is False
    assert lin_snap.total_born == 2
    assert lin_snap.max_generation == 1

    profile = AgentProfile(
        agent_id="agent-1",
        lineage_id="lineage-alpha",
        generation=1,
        parents=("agent-0",),
        roles=("craftsman",),
    )
    pop_snap = PopulationSnapshot(
        snapshot_id="pop-snap-100",
        tick=100,
        generation=1,
        total_agents=2,
        active_population=1,
        profiles={"agent-1": profile},
        lineages={"lineage-alpha": lin_snap},
        archive_coverage=5,
        gini_coefficient=0.15,
        role_distribution={"craftsman": 1},
    )
    assert pop_snap.snapshot_id == "pop-snap-100"
    assert pop_snap.active_population == 1
    assert pop_snap.gini_coefficient == 0.15

    # Check JSON roundtrip
    dumped = pop_snap.model_dump_json()
    restored = PopulationSnapshot.model_validate_json(dumped)
    assert restored.snapshot_id == pop_snap.snapshot_id
    assert restored.lineages["lineage-alpha"].total_born == 2


def test_scheduler_genealogy_and_population_snapshot() -> None:
    """Verifies that PopulationScheduler tracks genealogical nodes and exports population snapshots."""
    engine = SocialSandboxEngine(default_seed=77, num_agents=3, num_locations=2)
    s0 = engine.reset(seed=77, run_id="genealogy-test")

    cfg = DevelopmentConfig(adolescence=5, adulthood=10, elderhood=50, lifespan=100)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        config=cfg,
        run_id="genealogy-test",
    )

    assert len(scheduler.lineage_nodes) == 3
    pop_snap = scheduler.create_population_snapshot()
    assert pop_snap.total_agents == 3
    assert pop_snap.active_population == 3
    assert len(pop_snap.lineages) >= 1

    # Record social interaction and verify metrics
    scheduler.record_interaction("agent-0", "agent-1")
    scheduler.record_interaction("agent-1", "agent-2")
    tot_int, density = scheduler.compute_interaction_metrics()
    assert tot_int == 2
    assert density > 0.0

    # Verify specialization metrics
    hhi, entropy, role_counts = scheduler.compute_specialization()
    assert 0.0 <= hhi <= 1.0
    assert entropy >= 0.0
    assert sum(role_counts.values()) == 3


def test_scheduler_extinction_and_replacement_tracking() -> None:
    """Verifies that lineage extinctions and replacements are properly reported in metrics."""
    engine = SocialSandboxEngine(default_seed=12, num_agents=2, num_locations=2)
    s0 = engine.reset(seed=12, run_id="extinction-test")
    w0 = WorldState.from_state(s0)

    # Set distinct lineages: agent-0 is lineage-alpha, agent-1 is lineage-beta
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"lineage_id": "lineage-alpha"})
    agents["agent-1"] = agents["agent-1"].model_copy(update={"lineage_id": "lineage-beta"})
    s_custom = w0.model_copy(update={"agents": agents}).to_state()

    cfg = DevelopmentConfig(adolescence=5, adulthood=10, elderhood=20, lifespan=25)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s_custom,
        config=cfg,
        run_id="extinction-test",
    )

    # Prime previous lineages
    scheduler._previous_active_lineages = {"lineage-alpha", "lineage-beta"}

    # Simulate agent-0 dying
    w_curr = WorldState.from_state(scheduler.state)
    agents_updated = dict(w_curr.agents)
    agents_updated["agent-0"] = agents_updated["agent-0"].model_copy(update={"alive": False})
    scheduler.state = w_curr.model_copy(update={"agents": agents_updated}).to_state()

    # Run 1 step to trigger metrics
    metrics = scheduler.run_generation(steps=1, seed=12)
    assert metrics.extinctions >= 1
    assert metrics.replacements >= 1


def test_scheduler_prune_dead_agents() -> None:
    """Verifies that prune_dead_agents removes dead agents from active dictionary to prevent leaks."""
    engine = SocialSandboxEngine(default_seed=55, num_agents=3, num_locations=2)
    s0 = engine.reset(seed=55, run_id="prune-test")
    w0 = WorldState.from_state(s0)

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        run_id="prune-test",
    )
    assert "agent-0" in scheduler.agents

    # Mark agent-0 dead in world state
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"alive": False})
    scheduler.state = w0.model_copy(update={"agents": agents}).to_state()

    pruned = scheduler.prune_dead_agents()
    assert pruned == 1
    assert "agent-0" not in scheduler.agents
    assert "agent-0" in scheduler.inactive_agents
