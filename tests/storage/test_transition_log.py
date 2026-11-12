"""Tests for DuckDB-backed `evolzen.storage.TransitionLogStore`."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import (
    BranchRecord,
    GrowthAttribution,
    GrowthCategory,
    GrowthEvent,
)
from evolzen.storage.transition_log import SCHEMA_VERSION, TransitionLogStore


def test_append_count_list_and_integrity_chain(tmp_path: Path) -> None:
    db_path = tmp_path / "transitions.duckdb"
    engine = SocialSandboxEngine(default_seed=11)
    s0 = engine.reset(seed=11, run_id="run-1")
    t1 = engine.step(s0, Action(agent_id="agent-0", action_type="gather", params={"resource": "food"}))
    t2 = engine.step(
        t1.next_state,
        Action(agent_id="agent-1", action_type="wait"),
        exogenous_input=ExogenousInput(tick=2, events=({"type": "regen"},)),
        seed=11,
    )

    with TransitionLogStore(db_path) as store:
        assert store.schema_version() == SCHEMA_VERSION
        assert store.count() == 0
        store.append(t1, run_id="run-1", branch_id="main")
        store.append(t2, run_id="run-1", branch_id="main")
        assert store.count() == 2
        assert store.count(run_id="run-1", branch_id="main") == 2
        assert store.verify_integrity() is True

        loaded = store.list_transitions(run_id="run-1", branch_id="main")
        assert len(loaded) == 2
        assert loaded[0].next_state.data == t1.next_state.data
        assert loaded[1].exogenous_input.events == ({"type": "regen"},)

        with pytest.raises(duckdb.ConstraintException):
            store.append(t1, run_id="run-1", branch_id="main")
        assert store.count() == 2


def test_integrity_detects_tampering(tmp_path: Path) -> None:
    db_path = tmp_path / "tamper.duckdb"
    engine = SocialSandboxEngine(default_seed=3)
    s0 = engine.reset(seed=3)
    t1 = engine.step(s0, Action(agent_id="agent-0", action_type="wait"))

    with TransitionLogStore(db_path) as store:
        store.append(t1)
        assert store.verify_integrity() is True

    conn = duckdb.connect(str(db_path))
    conn.execute("UPDATE transitions SET seed = 999 WHERE seq_no = 1")
    conn.close()

    with TransitionLogStore(db_path) as store:
        assert store.verify_integrity() is False


def test_snapshots_growth_events_and_branches_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "world.duckdb"
    engine = SocialSandboxEngine(default_seed=5)
    s0 = engine.reset(seed=5, run_id="run-a")
    snap = engine.snapshot(s0)
    t1 = engine.step(s0, Action(agent_id="agent-0", action_type="propose_norm", params={"title": "Fairness"}))
    ev = GrowthEvent(
        event_id="g1",
        tick=1,
        category=GrowthCategory.NORM_BELIEF_MANUAL,
        attribution=GrowthAttribution.AGENT_ACTION,
        actor_id="agent-0",
        entity_id="norm-1",
        summary="Proposed norm Fairness",
        transition_id=str(t1.transition_id),
    )
    branch = BranchRecord(
        branch_id="alt",
        run_id="run-a",
        parent_branch_id="main",
        fork_tick=0,
        fork_snapshot_id=snap.snapshot_id,
    )

    with TransitionLogStore(db_path) as store:
        store.save_snapshot(snap)
        loaded_snap = store.load_snapshot(snap.snapshot_id)
        assert loaded_snap == snap
        assert store.latest_snapshot("run-a", "main") == snap

        store.append_growth_events([ev], run_id="run-a", branch_id="main")
        assert store.list_growth_events(run_id="run-a") == [ev]

        store.record_branch(branch)
        assert store.list_branches(run_id="run-a") == [branch]


def test_distinct_runs_share_branch_id_and_save_snapshot_and_branch_is_atomic(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "multi_run.duckdb"
    engine = SocialSandboxEngine(default_seed=19)
    s_a = engine.reset(seed=19, run_id="run-alpha")
    s_b = engine.reset(seed=19, run_id="run-beta")
    snap_a = engine.snapshot(s_a, snapshot_id="snap-alpha-cf-0")
    snap_b = engine.snapshot(s_b, snapshot_id="snap-beta-cf-0")

    branch_a = BranchRecord(
        branch_id="counterfactual",
        run_id="run-alpha",
        parent_branch_id="main",
        fork_tick=0,
        fork_snapshot_id=snap_a.snapshot_id,
    )
    branch_b = BranchRecord(
        branch_id="counterfactual",
        run_id="run-beta",
        parent_branch_id="main",
        fork_tick=0,
        fork_snapshot_id=snap_b.snapshot_id,
    )

    with TransitionLogStore(db_path) as store:
        store.save_snapshot_and_branch(snap_a, branch_a)
        store.save_snapshot_and_branch(snap_b, branch_b)

        assert store.list_branches(run_id="run-alpha") == [branch_a]
        assert store.list_branches(run_id="run-beta") == [branch_b]
        assert len(store.list_branches()) == 2

        # Duplicate (run_id, branch_id) must fail atomically without persisting the new snapshot
        snap_dup = engine.snapshot(s_a, snapshot_id="snap-alpha-cf-dup")
        dup_branch = BranchRecord(
            branch_id="counterfactual",
            run_id="run-alpha",
            parent_branch_id="main",
            fork_tick=0,
            fork_snapshot_id=snap_dup.snapshot_id,
        )
        with pytest.raises(duckdb.ConstraintException):
            store.save_snapshot_and_branch(snap_dup, dup_branch)
        with pytest.raises(KeyError):
            store.load_snapshot("snap-alpha-cf-dup")

