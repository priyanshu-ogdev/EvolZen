"""Smoke test for Phase 1.1 local throughput and persistence pilot helper."""
from __future__ import annotations

from pathlib import Path

from evolzen.environment import run_environment_pilot
from evolzen.schemas.world import WorldSnapshot
from evolzen.storage.transition_log import TransitionLogStore


def test_environment_pilot_smoke(tmp_path: Path) -> None:
    metrics = run_environment_pilot(db_path=tmp_path / "pilot.duckdb", steps=20, seed=7)
    assert metrics.steps == 20
    assert metrics.ticks_per_second > 0.0
    assert metrics.writes_per_second > 0.0
    assert metrics.replay_exact_match is True
    assert metrics.snapshot_bytes > 0
    assert metrics.db_bytes > 0


def test_environment_pilot_saves_periodic_snapshots(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot_snaps.duckdb"
    metrics = run_environment_pilot(
        db_path=db_path, steps=10, seed=7, snapshot_interval=3
    )
    assert metrics.steps == 10
    assert metrics.replay_exact_match is True

    with TransitionLogStore(db_path) as store:
        assert store.count(run_id="pilot-run", branch_id="main") == 10
        assert store.latest_snapshot("pilot-run", "main", max_tick=2) is not None
        snap_ticks = []
        for tick_target in (0, 3, 6, 9):
            snap: WorldSnapshot | None = store.latest_snapshot(
                "pilot-run", "main", max_tick=tick_target
            )
            assert snap is not None
            snap_ticks.append(snap.tick)
        assert snap_ticks == [0, 3, 6, 9]
        # No snapshot was saved at tick 10 since 10 % 3 != 0
        latest = store.latest_snapshot("pilot-run", "main")
        assert latest is not None and latest.tick == 9

