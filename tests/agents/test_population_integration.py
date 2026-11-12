"""End-to-end multi-agent population integration test (Phase 1.2).

Wires `SocialSandboxEngine`, `PopulationScheduler`, and `TransitionLogStore`
across multi-tick generational rollouts.
"""
from __future__ import annotations

from pathlib import Path

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.development import DevelopmentConfig
from evolzen.schemas.world import WorldState
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
