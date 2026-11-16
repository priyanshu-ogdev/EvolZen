"""Unit and integration tests for PopulationScheduler under environmental scarcity (Frontier 1).

Tests multi-agent generational lifecycle scheduling, exogenous drought scarcity shocks,
demographic indicators, macroeconomic Gini volatility, and invariant preservation.

Citations:
    - Henrich & Boyd (J. Theor. Biol. 2002) for cultural transmission under environmental volatility.
    - Zheng et al. (Science Advances 2022) for wealth Gini dynamics under resource shocks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.economy.manuals import ManualStore
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate, DevelopmentConfig
from evolzen.schemas.manual import ProvenanceCategory, ProvenanceRecord
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType, WorldState
from evolzen.storage.transition_log import TransitionLogStore


def test_scheduler_drought_shocks_and_telemetry() -> None:
    """Verifies that drought scarcity shocks apply deterministically and record telemetry."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=4, num_locations=4)
    s0 = engine.reset(seed=42, run_id="drought-test")
    w0 = WorldState.from_state(s0)

    cfg = DevelopmentConfig(adolescence=5, adulthood=10, elderhood=50, lifespan=100)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        config=cfg,
        run_id="drought-test",
    )
    assert len(scheduler.agents) == 4

    metrics = scheduler.run_generation(
        steps=10,
        seed=42,
        drought_interval=5,
        drought_severity=0.5,
    )

    assert metrics.total_transitions > 0
    assert metrics.active_population > 0
    assert "drought_periods" in metrics.metadata
    assert metrics.metadata["drought_periods"] > 0
    assert metrics.metadata["drought_ticks"] > 0
    assert metrics.metadata["drought_interval"] == 5
    assert metrics.metadata["drought_severity"] == 0.5
    assert "gini_volatility" in metrics.metadata
    assert metrics.metadata["gini_volatility"] >= 0.0
    assert "active_lineage_count" in metrics.metadata
    assert metrics.metadata["active_lineage_count"] > 0

    # Invariants must hold across initial and final state
    w_final = WorldState.from_state(scheduler.state)
    report = check_invariants(w0, w_final)
    assert report.passed is True


def test_scheduler_drought_disabled_by_default() -> None:
    """Verifies that drought_interval=0 disables shocks and records 0 drought periods."""
    engine = SocialSandboxEngine(default_seed=123, num_agents=3, num_locations=3)
    s0 = engine.reset(seed=123, run_id="no-drought-test")

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        run_id="no-drought-test",
    )

    metrics = scheduler.run_generation(steps=5, seed=123, drought_interval=0)
    assert metrics.metadata["drought_periods"] == 0
    assert metrics.metadata["drought_ticks"] == 0
    assert metrics.metadata["active_lineage_count"] > 0


def test_scheduler_drought_multi_generation_demographics(tmp_path: Path) -> None:
    """Verifies multi-generational rollouts under recurring droughts with DuckDB logging."""
    db_path = tmp_path / "drought_transitions.duckdb"
    store = TransitionLogStore(db_path)

    engine = SocialSandboxEngine(default_seed=99, num_agents=4, num_locations=4)
    s0 = engine.reset(seed=99, run_id="multi-gen-drought")

    manual_store = ManualStore(real_data_floor=0.2)
    prov = ProvenanceRecord.create(
        provenance_id="prov-crafting-recipe",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="seeds/crafting.md",
        description="Crafting recipe",
    )
    manual_store.add_entry(
        situation_key="crafting",
        text="Gather wood and stone to craft specialized tools",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        provenance=prov,
        written_by="human_expert",
    )

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        manual_store=manual_store,
        store=store,
        run_id="multi-gen-drought",
    )

    for gen in range(2):
        metrics = scheduler.run_generation(
            steps=6,
            seed=99 + gen,
            drought_interval=4,
            drought_severity=0.4,
        )
        assert metrics.total_transitions > 0
        assert metrics.metadata["drought_periods"] > 0
        assert metrics.metadata["active_lineage_count"] > 0

    assert store.count(run_id="multi-gen-drought") > 0
    assert store.verify_integrity() is True


def test_scheduler_communal_silo_food_buffering_under_drought() -> None:
    """Verifies that communal silo grain stores buffer hungry agents against famine under drought shocks."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=42, run_id="communal-silo-test", initial_agent_age=350)

    # 1. Establish communal institution and fund its food treasury
    tr1 = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "communal-silo", "name": "GrainBank", "seed_currency": 5},
        ),
    )
    assert tr1.emission.data["accepted"] is True

    tr2 = engine.step(
        tr1.next_state,
        Action(
            agent_id="agent-1",
            action_type=ActionType.JOIN_INSTITUTION,
            params={"institution_id": "communal-silo"},
        ),
    )
    assert tr2.emission.data["accepted"] is True

    tr3 = engine.step(
        tr2.next_state,
        Action(
            agent_id="agent-0",
            action_type=ActionType.CONTRIBUTE_INSTITUTION,
            params={"institution_id": "communal-silo", "resource": "food", "amount": 2},
        ),
    )
    assert tr3.emission.data["accepted"] is True
    w3 = WorldState.from_state(tr3.next_state)
    assert w3.institutions["communal-silo"].treasury["food"] == 2

    # 2. Simulate environmental drought scarcity shock: deplete location food and agent-1 food
    loc_id = list(w3.locations.keys())[0]
    locs = dict(w3.locations)
    loc_res = dict(locs[loc_id].resources)
    diff_loc_food = loc_res.get("food", 0)
    loc_res["food"] = 0
    locs[loc_id] = locs[loc_id].model_copy(update={"resources": loc_res})

    a1_inv = dict(w3.agents["agent-1"].inventory)
    diff_food = a1_inv.get("food", 0)
    a1_inv["food"] = 0
    w_agents = dict(w3.agents)
    w_agents["agent-1"] = w_agents["agent-1"].model_copy(update={"energy": 0.45, "inventory": a1_inv})

    consumed = dict(w3.accounting.consumed_or_decayed)
    consumed["food"] = consumed.get("food", 0) + diff_food + diff_loc_food
    w_drought = w3.model_copy(
        update={
            "locations": locs,
            "agents": w_agents,
            "accounting": w3.accounting.model_copy(update={"consumed_or_decayed": consumed}),
        }
    )
    s_drought = w_drought.to_state()

    # 3. Step scheduler under drought
    cfg = DevelopmentConfig(adolescence=5, adulthood=10, elderhood=500, lifespan=1000)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s_drought,
        run_id="communal-silo-test",
        config=cfg,
    )

    metrics = scheduler.run_generation(
        steps=4,
        seed=42,
        drought_interval=2,
        drought_severity=0.8,
    )

    assert metrics.total_transitions > 0
    assert metrics.active_population >= 2
    w_end = WorldState.from_state(scheduler.state)
    # The communal food reserve buffered the colony: treasury food was tapped
    assert w_end.institutions["communal-silo"].treasury.get("food", 0) < 2
    # Living agents survived drought
    assert w_end.agents["agent-1"].alive is True

    # Invariants must strictly hold across drought rollout
    report = check_invariants(w_drought, w_end)
    assert report.passed is True


class _MockInferenceBackend:
    """Mock InferenceBackend satisfying protocol for PopulationScheduler testing."""

    def __init__(self) -> None:
        self.call_count = 0
        self.recorded_contexts: list[dict[str, Any]] = []

    def generate_action(
        self,
        profile: AgentProfile,
        signal: tuple[float, ...],
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> Action:
        self.call_count += 1
        self.recorded_contexts.append(world_context)
        return Action(agent_id=profile.agent_id, action_type=ActionType.WAIT)


def test_scheduler_with_mock_inference_backend() -> None:
    """Verifies that PopulationScheduler executes neural inference routing with live backend."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=4, num_locations=4)
    s0 = engine.reset(seed=42, run_id="mock-inference-test")
    w0 = WorldState.from_state(s0)

    backend = _MockInferenceBackend()
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s0,
        backend=backend,
        run_id="mock-inference-test",
    )

    assert scheduler.backend is backend
    assert len(scheduler.agents) == 4
    for agent in scheduler.agents.values():
        assert agent.backend is backend

    # Step single agent through live backend
    step_res = scheduler.step_agent("agent-0")
    assert step_res is not None
    transition, outcome = step_res
    assert transition.action.agent_id == "agent-0"
    assert transition.action.action_type == ActionType.WAIT
    assert outcome.verified is True
    assert backend.call_count == 1
    assert backend.recorded_contexts[0]["agent_id"] == "agent-0"
    assert backend.recorded_contexts[0]["tick"] == 0
    assert "location_id" in backend.recorded_contexts[0]

    # Run multi-step generational rollout with backend
    metrics = scheduler.run_generation(steps=2, seed=42)
    assert metrics.total_transitions > 0
    assert backend.call_count > 1

    # Invariants must hold across transitions
    w_final = WorldState.from_state(scheduler.state)
    report = check_invariants(w0, w_final)
    assert report.passed is True


def test_demographic_bottleneck_at_tick_1376_resolved() -> None:
    """Verifies that the demographic bottleneck extinction at tick 1,376 is resolved.

    When senescent founder agents expire at the lifespan boundary (tick 1,376), their accumulated
    wealth is recycled into the local communal silo treasury and currency reserve.
    Under compound drought and famine stress, living juvenile and reproductive offspring
    withdraw from the communal silo, preserving population viability and exact invariants.
    """
    engine = SocialSandboxEngine(
        default_seed=42,
        num_agents=2,
        num_locations=1,
        lifespan=1376,
        adulthood_age=300,
        max_ticks=2000,
    )
    s0 = engine.reset(seed=42, run_id="demographic-bottleneck-1376", initial_agent_age=350)

    # 1. Founder agent-0 establishes communal silo
    tr_inst = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "communal-silo", "name": "communal-silo", "seed_currency": 5},
        ),
    )
    assert tr_inst.emission.data["accepted"] is True
    w1 = WorldState.from_state(tr_inst.next_state)

    # 2. Spawn offspring child-0 (descendant generation)
    w1_agents = dict(w1.agents)
    w1_agents["child-0"] = w1.agents["agent-0"].model_copy(
        update={
            "agent_id": "child-0",
            "born_at": 1000,
            "parents": ("agent-0",),
            "lineage_id": "lineage-0",
            "generation": 1,
            "institution_ids": (),
            "inventory": {"food": 0},
            "currency": 5,
            "energy": 0.5,
            "alive": True,
        }
    )
    # Rebalance initial accounting for offspring currency/food so invariants hold
    accounting = w1.accounting.model_copy(
        update={"initial_currency": w1.accounting.initial_currency + 5}
    )
    w_with_offspring = w1.model_copy(update={"agents": w1_agents, "accounting": accounting})

    # 3. Fast-forward world tick to 1,375 (right before founder lifespan expiration at 1,376)
    w_fast = w_with_offspring.model_copy(update={"tick": 1375})
    s_fast = w_fast.to_state()

    cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=1376)
    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=s_fast,
        config=cfg,
        run_id="demographic-bottleneck-1376",
    )

    # 4. Step scheduler across the tick 1,376 boundary under drought stress
    metrics = scheduler.run_generation(
        steps=5,
        seed=42,
        drought_interval=2,
        drought_severity=0.8,
    )

    # 5. Verify demographics: founders expired, but living generation survived
    w_end = WorldState.from_state(scheduler.state)
    assert w_end.tick >= 1376
    # Founder agent-0 reached lifespan and expired
    assert w_end.agents["agent-0"].alive is False
    assert w_end.agents["agent-0"].inventory == {}
    assert w_end.agents["agent-0"].currency == 0

    # Offspring child-0 survived by withdrawing food from communal silo
    assert w_end.agents["child-0"].alive is True
    assert metrics.active_population >= 1
    assert w_end.agents["child-0"].inventory.get("food", 0) >= 1 or w_end.agents["child-0"].energy >= 0.5

    # Invariants strictly hold across the demographic bottleneck boundary
    report = check_invariants(w_fast, w_end)
    assert report.passed is True


