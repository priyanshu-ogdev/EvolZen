"""Tests for DuckDB replay, branching, snapshot restore, and controlled interventions."""
from __future__ import annotations

from pathlib import Path

from evolzen.environment import (
    SocialSandboxEngine,
    apply_intervention,
    branch_from_snapshot,
    replay_from_store,
    replay_transitions,
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


def test_replay_transitions_propagates_cascading_divergence() -> None:
    engine = SocialSandboxEngine(default_seed=42)
    s0 = engine.reset(seed=42)

    tr0 = engine.step(
        s0,
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "food", "amount": 1}),
        seed=42,
    )
    tr1 = engine.step(
        tr0.next_state,
        Action(agent_id="agent-0", action_type=ActionType.CONSUME, params={"resource": "food", "amount": 1}),
        seed=42,
    )

    # 1. Exact replay from s0 matches perfectly
    res_exact = replay_transitions(engine, s0, [tr0, tr1])
    assert res_exact.exact_match is True
    assert res_exact.matched == 2

    # 2. Replay from an initial state with perturbed fatigue (valid invariants, but divergent state)
    w0_mod = WorldState.from_state(s0)
    agent0 = w0_mod.agents["agent-0"]
    w0_perturbed = w0_mod.model_copy(
        update={"agents": {**w0_mod.agents, "agent-0": agent0.model_copy(update={"fatigue": 0.5})}}
    )
    s0_perturbed = w0_perturbed.to_state()

    # With cascading state propagation, the perturbation propagates to step 1
    res_perturbed = replay_transitions(engine, s0_perturbed, [tr0, tr1])
    assert res_perturbed.exact_match is False
    assert len(res_perturbed.mismatches) >= 1
    # step 1 must see the divergent state from step 0
    assert any("step 1: initial state mismatch" in m for m in res_perturbed.mismatches)


def test_interventions_currency_reconciliation() -> None:
    engine = SocialSandboxEngine(default_seed=42)
    s0 = engine.reset(seed=42)

    act = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    # Intervene on currency: increase agent-0 currency from 20 to 50
    spec = InterventionSpec(
        intervention_id="iv-currency-grant",
        kind="set_variable",
        target_path="agents.agent-0.currency",
        value=50,
    )
    base_tr, iv_tr = apply_intervention(engine, s0, act, spec, seed=42)
    assert base_tr.emission.data["accepted"] is True
    assert iv_tr.emission.data["accepted"] is True

    w_base = WorldState.from_state(base_tr.next_state)
    w_iv = WorldState.from_state(iv_tr.next_state)
    assert w_base.agents["agent-0"].currency == 20
    assert w_iv.agents["agent-0"].currency == 50
    # Currency conservation in w_iv must hold with reconciled initial_currency
    assert w_iv.accounting.initial_currency == sum(a.currency for a in w_iv.agents.values())


def test_interventions_sequence_path_indexing() -> None:
    engine = SocialSandboxEngine(default_seed=42)
    s0 = engine.reset(seed=42)

    w0 = WorldState.from_state(s0)
    # Give agent-0 a tuple of skills
    w0_mod = w0.model_copy(
        update={"agents": {**w0.agents, "agent-0": w0.agents["agent-0"].model_copy(update={"skills": ("foraging", "mining")})}}
    )
    s0_mod = w0_mod.to_state()

    spec = InterventionSpec(
        intervention_id="iv-sequence",
        kind="set_variable",
        target_path="agents.agent-0.skills.1",
        value="masonry",
    )
    act = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    base_tr, iv_tr = apply_intervention(engine, s0_mod, act, spec, seed=42)
    w_iv = WorldState.from_state(iv_tr.next_state)
    assert w_iv.agents["agent-0"].skills == ("foraging", "masonry")


