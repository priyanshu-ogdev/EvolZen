"""Unit and PettingZoo AEC API tests for `evolzen.environment.pettingzoo_env`."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pettingzoo.test import api_test  # type: ignore[import-untyped]

from evolzen.environment import SocialSandboxAECEnv, SocialSandboxEngine
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import ActionType, GrowthAttribution, GrowthCategory, WorldState
from evolzen.storage.transition_log import TransitionLogStore


def test_pettingzoo_api_compatibility() -> None:
    env = SocialSandboxAECEnv(SocialSandboxEngine(max_ticks=25, num_agents=3), seed=7)
    api_test(env, num_cycles=15, verbose_progress=False)


def test_pettingzoo_aec_reset_observe_last_step_and_truncation() -> None:
    env = SocialSandboxAECEnv(
        SocialSandboxEngine(default_seed=11, max_ticks=3, num_agents=2),
        seed=11,
        render_mode="ansi",
    )
    env.reset(seed=11, options={"initial_agent_age": 0})
    assert env.agents == ["agent-0", "agent-1"]
    assert env.agent_selection == "agent-0"

    obs = env.observe("agent-0")
    assert obs.shape == (8,)
    assert obs.dtype == np.float32
    assert np.all(obs >= -1.0) and np.all(obs <= 1.0)
    assert env.observation_space("agent-0").contains(obs)

    last_obs, reward, terminated, truncated, info = env.last()
    assert np.allclose(last_obs, obs)
    assert reward == 0.0
    assert terminated is False
    assert truncated is False
    assert info["action_mask"][0] == 1

    # Step discrete action (1 = gather food) for agent-0
    env.step(1)
    assert env.agent_selection == "agent-1"
    assert env.infos["agent-0"]["accepted"] is True

    # Step typed Action for agent-1
    env.step(Action(agent_id="agent-1", action_type=ActionType.WAIT))
    assert env.agent_selection == "agent-0"
    assert env.infos["agent-1"]["accepted"] is True

    # Mismatched agent_id or invalid action type fails loudly
    with pytest.raises(ValueError, match="does not match active agent"):
        env.step(Action(agent_id="agent-1", action_type=ActionType.WAIT))
    with pytest.raises(TypeError, match="Unsupported action type"):
        env.step("wait")  # type: ignore[arg-type]

    # Third step reaches max_ticks=3 and marks living agents truncated
    env.step(0)
    world = WorldState.from_state(env.current_state)
    assert world.tick == 3
    assert all(env.truncations[aid] is True for aid in env.agents)
    assert "SocialSandbox(tick=3" in env.render()
    env.close()


def test_pettingzoo_step_with_exogenous_seed_and_store(tmp_path: Path) -> None:
    """Verify AECEnv.step supports exogenous inputs, seeds, and logs to TransitionLogStore."""
    db_path = tmp_path / "pettingzoo.duckdb"
    store = TransitionLogStore(db_path=db_path)
    engine = SocialSandboxEngine(default_seed=15, max_ticks=10, num_agents=2, num_locations=1)
    env = SocialSandboxAECEnv(
        engine,
        seed=15,
        store=store,
        run_id="pz-macro-run",
        branch_id="main",
    )
    env.reset(seed=15)
    assert env.store is store

    # Step with exogenous shock and deterministic seed
    exog = ExogenousInput(
        tick=0,
        events=({"type": "shock", "shock_factor": 0.3},),
    )
    env.step(0, exogenous_input=exog, seed=999)

    assert env.last_transition is not None
    assert env.last_transition.seed == 999
    assert "shock" in env.last_transition.emission.data["exogenous_applied"]

    # Verify state updated shock_factor on location
    world = WorldState.from_state(env.current_state)
    assert world.locations["plaza"].shock_factor == 0.3

    # Verify transition was persisted to DuckDB
    logged = store.list_transitions(run_id="pz-macro-run", branch_id="main")
    assert len(logged) == 1
    assert logged[0].transition_id == env.last_transition.transition_id
    env.close()


def test_pettingzoo_expanded_16_discrete_actions_decoding_and_norms() -> None:
    """Verify expanded 16 discrete actions decode properly and norm actions execute."""
    engine = SocialSandboxEngine(default_seed=25, max_ticks=500, num_agents=2, num_locations=1)
    env = SocialSandboxAECEnv(engine, seed=25)
    env.reset(seed=25, options={"initial_agent_age": 300})

    assert env.action_space("agent-0").n == 16  # type: ignore[attr-defined]

    # Verify decoders produce expected ActionTypes
    act_trade = env.decode_action("agent-0", 10)
    assert act_trade.action_type == ActionType.TRADE
    assert act_trade.params["counterparty_id"] == "agent-1"

    act_join = env.decode_action("agent-0", 11)
    assert act_join.action_type == ActionType.JOIN_INSTITUTION

    act_contrib = env.decode_action("agent-0", 12)
    assert act_contrib.action_type == ActionType.CONTRIBUTE_INSTITUTION

    act_prop_norm = env.decode_action("agent-0", 13)
    assert act_prop_norm.action_type == ActionType.PROPOSE_NORM

    act_adopt_norm = env.decode_action("agent-0", 14)
    assert act_adopt_norm.action_type == ActionType.ADOPT_NORM

    act_spawn = env.decode_action("agent-0", 15)
    assert act_spawn.action_type == ActionType.SPAWN_OFFSPRING

    # Execute discrete action 13: propose norm by agent-0
    # First elevate status of agent-0 so proposing norm is permitted
    w0 = WorldState.from_state(env.current_state)
    a0 = w0.agents["agent-0"].model_copy(update={"status": 0.5})
    s_elevated = w0.model_copy(update={"agents": {"agent-0": a0, "agent-1": w0.agents["agent-1"]}}).to_state()
    env.reset(options={"state": s_elevated})

    env.step(13)  # agent-0 proposes norm
    w1 = WorldState.from_state(env.current_state)
    assert len(w1.norms) == 1
    norm_id = list(w1.norms.keys())[0]

    # Now agent-1 adopts the norm via discrete action 14
    assert env.agent_selection == "agent-1"
    env.step(14)
    w2 = WorldState.from_state(env.current_state)
    assert norm_id in w2.agents["agent-1"].adopted_norms
    env.close()


def test_endogenous_ecology_growth_attribution() -> None:
    """Verify undisturbed ecosystems expand carrying capacity as an endogenous process."""
    engine = SocialSandboxEngine(default_seed=35, max_ticks=100, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=35)
    w0 = WorldState.from_state(s0)

    # Set location to flourishing state (food stock == food cap, shock_factor == 1.0) at tick 49
    loc = w0.locations["plaza"]
    cap_food = loc.capacities["food"]
    loc_res = dict(loc.resources)
    loc_res["food"] = cap_food
    flourishing_loc = loc.model_copy(update={"resources": loc_res, "shock_factor": 1.0})
    init_res = dict(w0.accounting.initial_resources)
    init_res["food"] = init_res.get("food", 0) + (cap_food - loc.resources.get("food", 0))

    s_flourishing = w0.model_copy(
        update={
            "locations": {"plaza": flourishing_loc},
            "accounting": w0.accounting.model_copy(update={"initial_resources": init_res}),
            "tick": 49,
        }
    ).to_state()

    # Step to tick 50 (next_tick = 50, triggers _expand_endogenous_ecology)
    act_wait = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    tr = engine.step(s_flourishing, act_wait)
    assert tr.emission.data["accepted"] is True

    w_expanded = WorldState.from_state(tr.next_state)
    assert w_expanded.locations["plaza"].capacities["food"] == cap_food + 1

    # Verify GrowthAttribution.ENDOGENOUS_PROCESS was emitted
    growth_events = tr.emission.data["growth_events"]
    endogenous_events = [
        e for e in growth_events
        if e["category"] == GrowthCategory.LOCATION_RESOURCE
        and e["attribution"] == GrowthAttribution.ENDOGENOUS_PROCESS
    ]
    assert len(endogenous_events) == 1
    assert endogenous_events[0]["actor_id"] == "world"
    assert "Expanded plaza food capacity" in endogenous_events[0]["summary"]
