"""Tests for DuckDB replay, branching, snapshot restore, and controlled interventions."""
from __future__ import annotations

from pathlib import Path

from evolzen.environment import (
    SocialSandboxEngine,
    apply_intervention,
    branch_from_snapshot,
    replay_from_store,
)
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import ActionType, InterventionSpec, WorldState
from evolzen.storage.transition_log import TransitionLogStore


def test_store_snapshot_branch_and_exact_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "replay.duckdb"
    engine = SocialSandboxEngine(default_seed=33)
    s0 = engine.reset(seed=33, run_id="run-replay")
    snap0 = engine.snapshot(s0)

    actions = [
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "food", "amount": 2}),
        Action(agent_id="agent-1", action_type=ActionType.PROPOSE_NORM, params={"title": "Reciprocity"}),
        Action(agent_id="agent-2", action_type=ActionType.ADOPT_NORM, params={"norm_id": "norm-2-agent-1"}),
        Action(agent_id="agent-0", action_type=ActionType.CONSUME, params={"resource": "food", "amount": 1}),
    ]

    with TransitionLogStore(db_path) as store:
        store.save_snapshot(snap0)
        state = s0
        mid_snapshot = None
        for i, act in enumerate(actions):
            tr = engine.step(
                state,
                act,
                exogenous_input=ExogenousInput(tick=i + 1),
                seed=33,
            )
            store.append(tr, run_id="run-replay", branch_id="main")
            state = tr.next_state
            if i == 1:
                mid_snapshot = engine.snapshot(state, parent_snapshot_id=snap0.snapshot_id)
                store.save_snapshot(mid_snapshot)

        full_replay = replay_from_store(engine, store, run_id="run-replay", branch_id="main")
        assert full_replay.exact_match is True
        assert full_replay.total_transitions == 2  # replays from mid_snapshot (tick 2 -> tick 4)
        assert full_replay.final_state.data == state.data

        assert mid_snapshot is not None
        branch_rec, branch_state = branch_from_snapshot(
            engine, store, mid_snapshot, new_branch_id="counterfactual"
        )
        assert branch_rec.parent_branch_id == "main"
        branch_tr = engine.step(
            branch_state,
            Action(agent_id="agent-3", action_type=ActionType.ASSIGN_ROLE, params={"role": "trader"}),
        )
        store.append(branch_tr, run_id="run-replay", branch_id="counterfactual")

        branch_replay = replay_from_store(
            engine, store, run_id="run-replay", branch_id="counterfactual"
        )
        assert branch_replay.exact_match is True
        # Parent main branch state remains untouched
        assert "agent-3" in WorldState.from_state(state).agents
        assert WorldState.from_state(state).agents["agent-3"].role == "generalist"
        assert WorldState.from_state(branch_replay.final_state).agents["agent-3"].role == "trader"


def test_interventions_withhold_action_and_set_variable() -> None:
    engine = SocialSandboxEngine(default_seed=9)
    s0 = engine.reset(seed=9)

    gather_act = Action(
        agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "food", "amount": 2}
    )
    base_tr, withheld_tr = apply_intervention(
        engine,
        s0,
        gather_act,
        InterventionSpec(
            intervention_id="iv-withhold",
            kind="withhold_action",
            withheld_agent_id="agent-0",
        ),
        seed=9,
    )
    assert base_tr.emission.data["action_type"] == ActionType.GATHER
    assert withheld_tr.emission.data["action_type"] == ActionType.WAIT
    assert WorldState.from_state(base_tr.next_state).agents["agent-0"].inventory["food"] == 5
    assert WorldState.from_state(withheld_tr.next_state).agents["agent-0"].inventory["food"] == 3

    base_tr2, var_tr = apply_intervention(
        engine,
        s0,
        gather_act,
        InterventionSpec(
            intervention_id="iv-deplete",
            kind="set_variable",
            target_path="locations.plaza.resources.food",
            value=0,
        ),
        seed=9,
    )
    assert base_tr2.emission.data["accepted"] is True
    assert var_tr.emission.data["accepted"] is False


def test_replay_from_store_up_to_tick_stops_at_exact_tick(tmp_path: Path) -> None:
    db_path = tmp_path / "upto.duckdb"
    engine = SocialSandboxEngine(default_seed=17)
    s0 = engine.reset(seed=17, run_id="run-upto")
    snap0 = engine.snapshot(s0)

    with TransitionLogStore(db_path) as store:
        store.save_snapshot(snap0)
        state = s0
        for step_idx in range(4):
            tr = engine.step(
                state,
                Action(agent_id="agent-0", action_type=ActionType.WAIT),
                exogenous_input=ExogenousInput(tick=step_idx + 1),
                seed=17,
            )
            store.append(tr, run_id="run-upto", branch_id="main")
            state = tr.next_state
            if step_idx == 1:
                store.save_snapshot(engine.snapshot(state, parent_snapshot_id=snap0.snapshot_id))

        at_zero = replay_from_store(engine, store, run_id="run-upto", branch_id="main", up_to_tick=0)
        assert at_zero.exact_match is True
        assert at_zero.total_transitions == 0
        assert WorldState.from_state(at_zero.final_state).tick == 0

        at_one = replay_from_store(engine, store, run_id="run-upto", branch_id="main", up_to_tick=1)
        assert at_one.exact_match is True
        assert at_one.total_transitions == 1
        assert WorldState.from_state(at_one.final_state).tick == 1

        at_three = replay_from_store(engine, store, run_id="run-upto", branch_id="main", up_to_tick=3)
        assert at_three.exact_match is True
        assert at_three.total_transitions == 1  # replays mid_snapshot (tick 2 -> tick 3)
        assert WorldState.from_state(at_three.final_state).tick == 3

