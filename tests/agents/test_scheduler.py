"""Unit and integration tests for PopulationScheduler under environmental scarcity (Frontier 1).

Tests multi-agent generational lifecycle scheduling, exogenous drought scarcity shocks,
demographic indicators, macroeconomic Gini volatility, and invariant preservation.

Citations:
    - Henrich & Boyd (J. Theor. Biol. 2002) for cultural transmission under environmental volatility.
    - Zheng et al. (Science Advances 2022) for wealth Gini dynamics under resource shocks.
"""
from __future__ import annotations

from pathlib import Path

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.economy.manuals import ManualStore
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants
from evolzen.schemas.development import DevelopmentConfig
from evolzen.schemas.manual import ProvenanceCategory, ProvenanceRecord
from evolzen.schemas.world import WorldState
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
