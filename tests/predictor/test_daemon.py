"""Tests for autonomous background training daemon (Phase 2.1)."""
from __future__ import annotations

import time
from pathlib import Path

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.predictor.daemon import OnlineTrainingDaemon
from evolzen.schemas.transition import Action
from evolzen.storage.transition_log import TransitionLogStore


def _seed_transitions(db_path: Path, count: int = 12) -> None:
    """Helper to populate DuckDB store with verified synthetic transitions."""
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=count + 10)
        state = engine.reset(seed=42)
        cur = state
        for i in range(count):
            act_type = "wait" if i % 2 == 0 else "gather"
            action = Action(agent_id="agent_0", action_type=act_type)
            trans = engine.step(cur, action)
            store.append(trans)
            cur = trans.next_state


def test_daemon_empty_db(tmp_path: Path) -> None:
    """OnlineTrainingDaemon should handle nonexistent or empty databases gracefully."""
    nonexistent = tmp_path / "nonexistent.duckdb"
    daemon = OnlineTrainingDaemon(db_path=nonexistent, batch_size=8)
    assert daemon.step_once() is None
    assert daemon.last_seq_no == 0
    assert daemon.update_count == 0

    empty_db = tmp_path / "empty.duckdb"
    with TransitionLogStore(empty_db) as store:
        assert store.count() == 0

    daemon_empty = OnlineTrainingDaemon(db_path=empty_db, batch_size=8)
    assert daemon_empty.step_once() is None
    assert daemon_empty.last_seq_no == 0
    assert daemon_empty.update_count == 0


def test_daemon_step_once(tmp_path: Path) -> None:
    """OnlineTrainingDaemon.step_once() ingests batches and advances sequence tracking."""
    db_path = tmp_path / "step_test.duckdb"
    _seed_transitions(db_path, count=12)

    daemon = OnlineTrainingDaemon(db_path=db_path, batch_size=8, seed=42)
    assert daemon.last_seq_no == 0
    assert daemon.update_count == 0

    summary = daemon.step_once()
    assert summary is not None
    assert summary["batch_size"] == 8
    assert summary["last_seq_no"] == 8
    assert summary["update_count"] == 1
    assert daemon.last_seq_no == 8
    assert daemon.update_count == 1
    assert daemon.policy_entropy >= 0.0
    assert daemon.jepa_variance >= 0.0
    assert 0 <= daemon.active_dimensions <= daemon.jepa.embedding_dim
    assert len(daemon.rehearsal_buffer) == 8

    # Only 4 transitions remain (< batch_size 8); without allow_partial, step_once returns None
    assert daemon.step_once() is None
    assert daemon.last_seq_no == 8
    assert daemon.update_count == 1

    # With allow_partial=True, the remaining 4 transitions are ingested
    summary2 = daemon.step_once(allow_partial=True)
    assert summary2 is not None
    assert summary2["batch_size"] == 4
    assert summary2["last_seq_no"] == 12
    assert summary2["update_count"] == 2
    assert daemon.last_seq_no == 12
    assert daemon.update_count == 2
    assert len(daemon.rehearsal_buffer) == 12

    daemon.stop()


def test_daemon_thread_lifecycle(tmp_path: Path) -> None:
    """OnlineTrainingDaemon starts and stops cleanly via context manager in background thread."""
    db_path = tmp_path / "thread_test.duckdb"
    _seed_transitions(db_path, count=16)

    daemon = OnlineTrainingDaemon(
        db_path=db_path,
        batch_size=8,
        poll_interval=0.05,
        max_steps=2,
        seed=42,
    )

    with daemon:
        assert daemon.is_running
        deadline = time.time() + 2.0
        while time.time() < deadline and daemon.update_count < 2:
            time.sleep(0.05)

    assert not daemon.is_running
    assert daemon.update_count >= 2
    assert daemon.last_seq_no >= 16


def test_daemon_metrics_reporting(tmp_path: Path) -> None:
    """OnlineTrainingDaemon exposes internal subcomponents and coherent metrics properties."""
    db_path = tmp_path / "metrics_test.duckdb"
    _seed_transitions(db_path, count=8)

    daemon = OnlineTrainingDaemon(db_path=db_path, batch_size=8, seed=42)
    assert daemon.predictor is not None
    assert daemon.rehearsal_buffer is not None
    assert daemon.planner is not None
    assert daemon.jepa is not None
    assert daemon.latest_summary is None

    res = daemon.step_once()
    assert res is not None
    assert daemon.latest_summary == res
    assert daemon.latest_summary["update_count"] == daemon.update_count == 1
    assert daemon.latest_summary["jepa_rep_variance"] == daemon.jepa_variance
    assert daemon.latest_summary["active_dimensions"] == daemon.active_dimensions
    assert daemon.latest_summary["policy_entropy"] == daemon.policy_entropy

    daemon.stop()
