"""End-to-end multi-agent population integration test (Phase 1.2).

Wires `SocialSandboxEngine`, `PopulationScheduler`, `ManualStore`, and `TransitionLogStore`
across multi-tick generational rollouts, intergenerational teaching, and genetic inheritance.
"""
from __future__ import annotations

from pathlib import Path

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.economy.manuals import ManualStore
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.development import DevelopmentConfig, LifeStage
from evolzen.schemas.manual import ManualEntry
from evolzen.schemas.provenance import ProvenanceCategory, ProvenanceRecord
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType, WorldState
from evolzen.storage.transition_log import TransitionLogStore


def test_population_scheduler_multi_step_rollout(tmp_path: Path) -> None:
    db_path = tmp_path / "population_transitions.duckdb"
    store = TransitionLogStore(db_path)

    engine = SocialSandboxEngine(default_seed=42, num_agents=3)
    s0 = engine.reset(seed=42, run_id="integration-run")

    cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=60, lifespan=100)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        config=cfg,
        store=store,
        run_id="integration-run",
    )
    assert len(scheduler.agents) == 3

    metrics = scheduler.run_generation(steps=5, seed=42)
    assert metrics.total_transitions == 15
    assert metrics.active_population == 3
    assert metrics.ticks_elapsed == 15

    # Verify transitions were committed to DuckDB store
    persisted_count = store.count(run_id="integration-run")
    assert persisted_count == 15
    assert store.verify_integrity() is True

    # Advance clock and verify lifecycle staging
    w_final = WorldState.from_state(scheduler.state)
    assert w_final.tick == 15


def test_population_scheduler_with_manual_store_and_teaching(tmp_path: Path) -> None:
    """Verifies that colocated adult parents transmit active living manual entries to children."""
    engine = SocialSandboxEngine(default_seed=100, num_agents=2)
    s0 = engine.reset(seed=100, run_id="manual-teaching-run")
    w0 = WorldState.from_state(s0)

    # Configure agent-0 as an adult parent at location-0, and agent-1 as its child
    loc_id = next(iter(w0.locations.keys()))
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(
        update={
            "born_at": 0,
            "location_id": loc_id,
            "generation": 0,
            "parents": (),
        }
    )
    agents["agent-1"] = agents["agent-1"].model_copy(
        update={
            "born_at": 25,
            "location_id": loc_id,
            "generation": 1,
            "parents": ("agent-0",),
        }
    )
    custom_state = w0.model_copy(
        update={
            "agents": agents,
            "tick": 25,
            "adulthood_age": 20,
        }
    ).to_state()

    # Create a living manual with provenanced ground-truth entry
    prov = ProvenanceRecord.create(
        provenance_id="prov-manual-1",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="docs/protocol.md",
        description="Core protocol for food gathering and trading",
    )
    entry = ManualEntry(
        text="Maintain at least 5 food units before initiating trades.",
        written_by="human_expert",
        provenance=prov,
        category=ProvenanceCategory.HUMAN_AUTHORED,
    )
    manual_store = ManualStore(real_data_floor=0.2)
    manual_store.add_entry("resource_allocation", entry)

    cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=50, lifespan=100)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=custom_state,
        config=cfg,
        manual_store=manual_store,
        run_id="manual-teaching-run",
    )

    # Verify agent-0 is adult and agent-1 is adolescent/child
    assert scheduler.agents["agent-0"].stage in (LifeStage.ADULT, LifeStage.ELDER)
    assert scheduler.agents["agent-1"].stage in (LifeStage.CHILD, LifeStage.ADOLESCENT)

    # Run generation
    metrics = scheduler.run_generation(steps=2, seed=10)
    assert metrics.teachings >= 1

    # Verify child received the manual entry lesson
    child_dev = scheduler.agents["agent-1"].development
    assert len(child_dev.lessons) >= 1
    assert any(
        les.manual_entry is not None and "Maintain at least 5 food units" in les.manual_entry.text
        for les in child_dev.lessons
    )


def test_population_scheduler_spawns_offspring_with_lineage(tmp_path: Path) -> None:
    """Verifies that an agent spawning offspring correctly registers the new child with inherited lineage."""
    engine = SocialSandboxEngine(default_seed=200, num_agents=1)
    s0 = engine.reset(seed=200, run_id="spawn-offspring-run")
    w0 = WorldState.from_state(s0)

    # Configure parent agent as adult with adulthood_age=20, born_at=0, tick=25
    parent_id = "agent-0"
    agents = dict(w0.agents)
    agents[parent_id] = agents[parent_id].model_copy(
        update={"born_at": 0, "generation": 0, "parents": ()}
    )
    state = w0.model_copy(update={"agents": agents, "tick": 25, "adulthood_age": 20}).to_state()

    cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=60, lifespan=100)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=state,
        config=cfg,
        run_id="spawn-offspring-run",
    )

    # Step the engine directly to execute SPAWN_OFFSPRING
    spawn_action = Action(
        agent_id=parent_id,
        action_type=ActionType.SPAWN_OFFSPRING,
        params={"child_id": "child-0", "endow_currency": 5},
    )
    trans = engine.step(scheduler.state, spawn_action, seed=1)
    scheduler.state = trans.next_state

    # Scheduler registers the child
    new_count = scheduler._init_agents_from_world()
    assert new_count == 1
    assert "child-0" in scheduler.agents

    child_agent = scheduler.agents["child-0"]
    assert child_agent.profile.parents == (parent_id,)
    assert child_agent.profile.generation == 1
    assert child_agent.development.birth.parents == (parent_id,)
    assert child_agent.development.birth.generation == 1


def test_population_multi_generation_simulation_with_tier1_and_archive(tmp_path: Path) -> None:
    """Verifies a multi-step population simulation with Tier-1 decision engine and CVTArchive admission."""
    db_path = tmp_path / "sim_transitions.duckdb"
    store = TransitionLogStore(db_path)

    engine = SocialSandboxEngine(default_seed=300, num_agents=3)
    s0 = engine.reset(seed=300, run_id="tier1-sim-run")

    prov = ProvenanceRecord.create(
        provenance_id="prov-sim-1",
        category=ProvenanceCategory.SIMULATOR_TRACE,
        uri_or_source="sim://trace-0",
        description="Simulator baseline trace",
    )
    entry = ManualEntry(
        text="Conserve energy when fatigue exceeds 0.7.",
        written_by="sim_observer",
        provenance=prov,
        category=ProvenanceCategory.SIMULATOR_TRACE,
    )
    manual_store = ManualStore(real_data_floor=0.2)
    manual_store.add_entry("conservation", entry)

    # Use Tier-1 Augmented Chebyshev scalarization with accelerated lifecycle
    cfg = DevelopmentConfig(
        adolescence=4,
        adulthood=8,
        elderhood=30,
        lifespan=60,
        use_tier1_decision=True,
        chebyshev_rho=0.01,
        exploration_c=0.2,
    )

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        config=cfg,
        manual_store=manual_store,
        store=store,
        run_id="tier1-sim-run",
    )

    # Run 12 simulation steps across all agents (agents will age from childhood into adulthood)
    metrics = scheduler.run_generation(steps=12, seed=42)
    assert metrics.total_transitions == 36
    assert metrics.ticks_elapsed == 36
    assert metrics.active_population > 0

    # Since agents reached adulthood (tick 12 >= adulthood 8), verify archive admission
    assert scheduler.archive.coverage() > 0
    entries = scheduler.archive.entries()
    assert len(entries) > 0
    assert all(len(e.behavioral_descriptor) == 5 for e in entries)

    # Check store persistence integrity
    assert store.count(run_id="tier1-sim-run") == 36
    assert store.verify_integrity() is True

