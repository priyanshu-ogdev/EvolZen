"""Integration tests between `SocialSandboxEngine` and `evolzen.agents.development`."""
from __future__ import annotations

import pytest

from evolzen.agents.development import advance, born, decide, observe, teach
from evolzen.environment import (
    SocialSandboxEngine,
    action_from_candidate,
    execute_decision,
    legal_candidates,
    observe_features,
)
from evolzen.schemas.development import Candidate, Decision, DevelopmentConfig
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import ActionType, CapabilityPackage, WorldState


def test_developmental_agent_lifecycle_loop_in_social_sandbox() -> None:
    engine = SocialSandboxEngine(default_seed=12, num_agents=2)
    world_state = engine.reset(seed=12)

    child = born("agent-0", seed=100, tick=0)
    for _ in range(4):
        features = observe_features(world_state, "agent-0")
        assert len(features) == 8
        assert all(-1.0 <= f <= 1.0 for f in features)

        candidates = legal_candidates(world_state, "agent-0")
        assert any(c.action_id == "wait" and c.permitted for c in candidates)

        waiting = decide(child, features, candidates, WorldState.from_state(world_state).tick)
        assert waiting.pending is not None

        transition, outcome = execute_decision(engine, world_state, waiting.pending)
        assert outcome.verified is True
        child = observe(waiting, outcome)
        world_state = transition.next_state

    assert len(child.recent) == 4
    assert child.tick == WorldState.from_state(world_state).tick


def test_living_parent_teaching_and_stale_decision_rejection() -> None:
    cfg = DevelopmentConfig(adolescence=10, adulthood=30, elderhood=80, lifespan=120)
    engine = SocialSandboxEngine(default_seed=15, num_agents=2)
    world_state = engine.reset(seed=15, initial_agent_age=35)

    parent = born("agent-0", seed=1, tick=0, config=cfg)
    parent = advance(parent, 35)
    features = observe_features(world_state, "agent-0")
    candidates = legal_candidates(world_state, "agent-0", config=cfg)
    waiting = decide(parent, features, candidates, 35)
    assert waiting.pending is not None

    tr, outcome = execute_decision(engine, world_state, waiting.pending)
    parent = observe(waiting, outcome)

    # Stale decision at old tick must be rejected
    with pytest.raises(ValueError, match="Stale decision tick"):
        execute_decision(engine, tr.next_state, waiting.pending)

    # Advance parent and teach newborn child without mutating world state
    next_world_tick = WorldState.from_state(tr.next_state).tick
    child = born("agent-1", seed=2, tick=next_world_tick, config=cfg, parents=(parent,))
    taught_child = teach(
        parent,
        child,
        waiting.pending.candidate.context_key,
        waiting.pending.candidate.skill_key,
        next_world_tick,
    )
    assert len(taught_child.lessons) == 1
    assert taught_child.knowledge == ()

    # Ensure exogenous tick jump keeps adapter and engine aligned
    jumped = engine.step(
        tr.next_state,
        execute_decision(
            engine,
            tr.next_state,
            decide(
                taught_child,
                observe_features(tr.next_state, "agent-1"),
                legal_candidates(tr.next_state, "agent-1", config=cfg),
                next_world_tick,
            ).pending,  # type: ignore[arg-type]
            exogenous_input=ExogenousInput(tick=next_world_tick + 1),
        )[0].action,
        exogenous_input=ExogenousInput(tick=next_world_tick + 1),
    )
    assert WorldState.from_state(jumped.next_state).tick == next_world_tick + 1


def test_legal_candidates_surfaces_capabilities_and_maps_actions() -> None:
    engine = SocialSandboxEngine(default_seed=19)
    s0 = engine.reset(seed=19)

    plow_pkg = CapabilityPackage(
        package_id="craft:plow:v1",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1},
        output_kind="plow",
        min_age=250,
        evidence_id="ev-plow-1",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    reg_tr = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": plow_pkg.model_dump(mode="json")},
        ),
    )
    assert reg_tr.emission.data["accepted"] is True

    candidates = {c.action_id: c for c in legal_candidates(reg_tr.next_state, "agent-0")}
    assert candidates["craft:tool:v1"].minimum_age == 0
    assert candidates["craft:tool:v1"].permitted is False  # lacks stone initially
    assert candidates["craft:plow:v1"].minimum_age == 250
    assert candidates["craft:plow:v1"].permitted is True  # has 2 wood

    act_by_kind = action_from_candidate("craft:plow", "agent-0", state=reg_tr.next_state)
    assert act_by_kind.action_type == ActionType.CRAFT
    assert act_by_kind.params["package_id"] == "craft:plow:v1"

    act_by_pkg = action_from_candidate("craft:plow:v1", "agent-0", state=reg_tr.next_state)
    assert act_by_pkg.action_type == ActionType.CRAFT
    assert act_by_pkg.params["package_id"] == "craft:plow:v1"

    act_improve = action_from_candidate("improve_location:food", "agent-0", state=reg_tr.next_state)
    assert act_improve.action_type == ActionType.IMPROVE_LOCATION
    assert act_improve.params == {"target_resource": "food"}


def _forged_decision(
    *,
    tick: int,
    context_key: str,
    action_id: str,
    skill_key: str,
    sequence: int,
) -> Decision:
    return Decision(
        agent_id="agent-0",
        sequence=sequence,
        tick=tick,
        candidate=Candidate(
            action_id=action_id,
            context_key=context_key,
            skill_key=skill_key,
            predicted=(0.0,) * 8,
            minimum_age=0,
            permitted=True,
        ),
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )


def test_execute_decision_rejects_forged_unpermitted_underage_and_illegal_decisions() -> None:
    engine = SocialSandboxEngine(default_seed=23)
    s0 = engine.reset(seed=23, initial_agent_age=0)
    world = WorldState.from_state(s0)
    ctx = f"{world.world_version}:{world.agents['agent-0'].location_id}"

    # 1. Forged permitted=True for craft:tool:v1 when agent-0 lacks stone
    forged_unpermitted = _forged_decision(
        tick=world.tick,
        context_key=ctx,
        action_id="craft:tool:v1",
        skill_key="craft:tool:v1",
        sequence=1,
    )
    with pytest.raises(ValueError, match="not permitted"):
        execute_decision(engine, s0, forged_unpermitted)

    # 2. Forged minimum_age=0 for found_institution:guild when agent-0 age is 0 < 300
    forged_underage = _forged_decision(
        tick=world.tick,
        context_key=ctx,
        action_id="found_institution:guild",
        skill_key="found_institution:v1",
        sequence=2,
    )
    with pytest.raises(ValueError, match="below minimum_age"):
        execute_decision(engine, s0, forged_underage)

    # 3. Forged unknown/illegal action_id
    forged_illegal = _forged_decision(
        tick=world.tick,
        context_key=ctx,
        action_id="craft:spaceship",
        skill_key="craft:spaceship",
        sequence=3,
    )
    with pytest.raises(ValueError, match="not legal"):
        execute_decision(engine, s0, forged_illegal)


def test_action_from_candidate_full_17_coverage() -> None:
    """Verify action_from_candidate accurately translates all 17 ActionTypes."""
    act_wait = action_from_candidate("wait", "agent-0")
    assert act_wait.action_type == ActionType.WAIT
    assert act_wait.params == {}

    act_gather = action_from_candidate("gather:food:2", "agent-0")
    assert act_gather.action_type == ActionType.GATHER
    assert act_gather.params == {"resource": "food", "amount": 2}

    act_consume = action_from_candidate("consume:food:1", "agent-0")
    assert act_consume.action_type == ActionType.CONSUME
    assert act_consume.params == {"resource": "food", "amount": 1}

    act_move = action_from_candidate("move:loc-1", "agent-0")
    assert act_move.action_type == ActionType.MOVE
    assert act_move.params == {"target_location": "loc-1"}

    act_craft = action_from_candidate("craft:tool:v1", "agent-0")
    assert act_craft.action_type == ActionType.CRAFT
    assert act_craft.params == {"package_id": "craft:tool:v1", "kind": "tool"}

    act_improve = action_from_candidate("improve_location:food", "agent-0")
    assert act_improve.action_type == ActionType.IMPROVE_LOCATION
    assert act_improve.params == {"target_resource": "food"}

    act_found = action_from_candidate("found_institution:guild:5", "agent-0")
    assert act_found.action_type == ActionType.FOUND_INSTITUTION
    assert act_found.params == {"name": "guild", "seed_currency": 5}

    act_trade = action_from_candidate("trade:agent-1:food:1:2", "agent-0")
    assert act_trade.action_type == ActionType.TRADE
    assert act_trade.params == {
        "counterparty_id": "agent-1",
        "offer_resource": "food",
        "offer_qty": 1,
        "price": 2,
    }

    act_prop_cont = action_from_candidate("propose_contract:agent-1:wood:1:food:1", "agent-0")
    assert act_prop_cont.action_type == ActionType.PROPOSE_CONTRACT
    assert act_prop_cont.params == {
        "counterparty_id": "agent-1",
        "offer_resource": "wood",
        "offer_qty": 1,
        "request_resource": "food",
        "request_qty": 1,
    }

    act_ful_cont = action_from_candidate("fulfill_contract:contract-1", "agent-0")
    assert act_ful_cont.action_type == ActionType.FULFILL_CONTRACT
    assert act_ful_cont.params == {"contract_id": "contract-1"}

    act_join_inst = action_from_candidate("join_institution:guild", "agent-0")
    assert act_join_inst.action_type == ActionType.JOIN_INSTITUTION
    assert act_join_inst.params == {"institution_id": "guild"}

    act_contrib = action_from_candidate("contribute_institution:guild:wood:1", "agent-0")
    assert act_contrib.action_type == ActionType.CONTRIBUTE_INSTITUTION
    assert act_contrib.params == {
        "institution_id": "guild",
        "resource": "wood",
        "amount": 1,
    }

    act_prop_norm = action_from_candidate(
        "propose_norm:norm-1:conservation:Conserve Food", "agent-0"
    )
    assert act_prop_norm.action_type == ActionType.PROPOSE_NORM
    assert act_prop_norm.params == {
        "norm_id": "norm-1",
        "rule_kind": "conservation",
        "title": "Conserve Food",
    }

    act_adopt_norm = action_from_candidate("adopt_norm:norm-1", "agent-0")
    assert act_adopt_norm.action_type == ActionType.ADOPT_NORM
    assert act_adopt_norm.params == {"norm_id": "norm-1"}

    act_role = action_from_candidate("assign_role:scholar", "agent-0")
    assert act_role.action_type == ActionType.ASSIGN_ROLE
    assert act_role.params == {"role": "scholar"}

    act_spawn = action_from_candidate("spawn_offspring:child-1:5", "agent-0")
    assert act_spawn.action_type == ActionType.SPAWN_OFFSPRING
    assert act_spawn.params == {"child_id": "child-1", "endow_currency": 5}

    act_reg_cap = action_from_candidate(
        "register_capability:craft:expert_plow:v1:expert_plow", "agent-0"
    )
    assert act_reg_cap.action_type == ActionType.REGISTER_CAPABILITY
    assert act_reg_cap.params["evidence_id"] == "ev-craft:expert_plow:v1"
    assert act_reg_cap.params["package"]["package_id"] == "craft:expert_plow:v1"
    assert act_reg_cap.params["package"]["output_kind"] == "expert_plow"

    with pytest.raises(ValueError, match="Unsupported candidate action_id"):
        action_from_candidate("teleport:mars", "agent-0")


def test_legal_candidates_surfaces_new_actions_and_executes_decisions() -> None:
    """Verify that developmental agents can select and execute new actions end-to-end."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=3, num_locations=2)
    s0 = engine.reset(seed=42, initial_agent_age=350)
    w0 = WorldState.from_state(s0)

    # 1. Candidate surfacing
    cands_a0 = {c.action_id: c for c in legal_candidates(s0, "agent-0")}
    assert "wait" in cands_a0
    assert any(k.startswith("gather:") for k in cands_a0)
    assert any(k.startswith("consume:") for k in cands_a0)
    assert any(k.startswith("move:") for k in cands_a0)
    assert any(k.startswith("craft:") for k in cands_a0)
    assert any(k.startswith("improve_location:") for k in cands_a0)
    assert "found_institution:guild" in cands_a0
    assert any(k.startswith("trade:agent-2:") for k in cands_a0)
    assert any(k.startswith("propose_contract:agent-2:") for k in cands_a0)
    assert any(k.startswith("propose_norm:") for k in cands_a0)
    assert any(k.startswith("assign_role:") for k in cands_a0)
    assert any(k.startswith("spawn_offspring:") for k in cands_a0)
    assert any(k.startswith("register_capability:") for k in cands_a0)

    # 2. Execute trade:agent-2:food:1:2
    trade_cand = [c for c in cands_a0.values() if c.action_id.startswith("trade:agent-2:")][0]
    dec_trade = Decision(
        agent_id="agent-0",
        sequence=1,
        tick=w0.tick,
        candidate=trade_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr1, out1 = execute_decision(engine, s0, dec_trade)
    assert out1.verified is True
    w1 = WorldState.from_state(tr1.next_state)
    assert w1.agents["agent-0"].currency == 22
    assert w1.agents["agent-2"].currency == 18

    # 3. Execute propose_contract
    prop_cand = [
        c for c in legal_candidates(tr1.next_state, "agent-0")
        if c.action_id.startswith("propose_contract:agent-2:")
    ][0]
    dec_prop = Decision(
        agent_id="agent-0",
        sequence=2,
        tick=w1.tick,
        candidate=prop_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr2, out2 = execute_decision(engine, tr1.next_state, dec_prop)
    assert out2.verified is True
    w2 = WorldState.from_state(tr2.next_state)
    assert len(w2.contracts) == 1
    cid = list(w2.contracts.keys())[0]

    # 4. Agent-2 fulfills the contract
    ful_cand = [
        c for c in legal_candidates(tr2.next_state, "agent-2")
        if c.action_id == f"fulfill_contract:{cid}"
    ][0]
    dec_ful = Decision(
        agent_id="agent-2",
        sequence=1,
        tick=w2.tick,
        candidate=ful_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr3, out3 = execute_decision(engine, tr2.next_state, dec_ful)
    assert out3.verified is True
    w3 = WorldState.from_state(tr3.next_state)
    assert w3.contracts[cid].status == "fulfilled"

    # 5. Execute assign_role:scholar
    role_cand = [
        c for c in legal_candidates(tr3.next_state, "agent-0")
        if c.action_id == "assign_role:scholar"
    ][0]
    dec_role = Decision(
        agent_id="agent-0",
        sequence=3,
        tick=w3.tick,
        candidate=role_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr4, out4 = execute_decision(engine, tr3.next_state, dec_role)
    assert out4.verified is True
    w4 = WorldState.from_state(tr4.next_state)
    assert w4.agents["agent-0"].role == "scholar"

    # 6. Execute propose_norm
    norm_cand = [
        c for c in legal_candidates(tr4.next_state, "agent-0")
        if c.action_id.startswith("propose_norm:")
    ][0]
    dec_norm = Decision(
        agent_id="agent-0",
        sequence=4,
        tick=w4.tick,
        candidate=norm_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr5, out5 = execute_decision(engine, tr4.next_state, dec_norm)
    assert out5.verified is True
    w5 = WorldState.from_state(tr5.next_state)
    assert len(w5.norms) >= 1
    norm_id = list(w5.norms.keys())[0]

    # 7. Agent-2 adopts the norm
    adopt_cand = [
        c for c in legal_candidates(tr5.next_state, "agent-2")
        if c.action_id == f"adopt_norm:{norm_id}"
    ][0]
    dec_adopt = Decision(
        agent_id="agent-2",
        sequence=2,
        tick=w5.tick,
        candidate=adopt_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr6, out6 = execute_decision(engine, tr5.next_state, dec_adopt)
    assert out6.verified is True
    w6 = WorldState.from_state(tr6.next_state)
    assert "agent-2" in w6.norms[norm_id].adopters

    # 8. Agent-0 founds institution
    found_cand = [
        c for c in legal_candidates(tr6.next_state, "agent-0")
        if c.action_id == "found_institution:guild"
    ][0]
    dec_found = Decision(
        agent_id="agent-0",
        sequence=5,
        tick=w6.tick,
        candidate=found_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr7, out7 = execute_decision(engine, tr6.next_state, dec_found)
    assert out7.verified is True
    w7 = WorldState.from_state(tr7.next_state)
    assert len(w7.institutions) >= 1
    inst_id = list(w7.institutions.keys())[0]
    assert w7.institutions[inst_id].name == "guild"

    # 9. Agent-2 joins institution
    join_cand = [
        c for c in legal_candidates(tr7.next_state, "agent-2")
        if c.action_id == f"join_institution:{inst_id}"
    ][0]
    dec_join = Decision(
        agent_id="agent-2",
        sequence=3,
        tick=w7.tick,
        candidate=join_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr8, out8 = execute_decision(engine, tr7.next_state, dec_join)
    assert out8.verified is True
    w8 = WorldState.from_state(tr8.next_state)
    assert "agent-2" in w8.institutions[inst_id].member_ids

    # 10. Agent-2 contributes to institution
    contrib_cand = [
        c for c in legal_candidates(tr8.next_state, "agent-2")
        if c.action_id.startswith(f"contribute_institution:{inst_id}:")
    ][0]
    dec_contrib = Decision(
        agent_id="agent-2",
        sequence=4,
        tick=w8.tick,
        candidate=contrib_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr9, out9 = execute_decision(engine, tr8.next_state, dec_contrib)
    assert out9.verified is True
    w9 = WorldState.from_state(tr9.next_state)
    assert sum(w9.institutions[inst_id].treasury.values()) >= 1

    # 11. Agent-0 spawns offspring
    spawn_cand = [
        c for c in legal_candidates(tr9.next_state, "agent-0")
        if c.action_id.startswith("spawn_offspring:") and c.permitted
    ][0]
    dec_spawn = Decision(
        agent_id="agent-0",
        sequence=6,
        tick=w9.tick,
        candidate=spawn_cand,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr10, out10 = execute_decision(engine, tr9.next_state, dec_spawn)
    assert out10.verified is True
    w10 = WorldState.from_state(tr10.next_state)
    living_agents = [a for a in w10.agents.values() if a.alive]
    assert len(living_agents) == 4


def test_stage1_and_stage2_architectural_integration() -> None:
    """Verify that Stage 1 interventions/replay work smoothly with Stage 2 host adapter."""
    from evolzen.environment.interventions import apply_intervention
    from evolzen.environment.replay import replay_transitions
    from evolzen.schemas.world import InterventionSpec

    engine = SocialSandboxEngine(default_seed=99, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=99, initial_agent_age=400)

    # Apply Stage 1 intervention: elevate status on agent-0
    action0 = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    spec = InterventionSpec(
        intervention_id="iv-status",
        kind="set_variable",
        target_path="agents.agent-0.status",
        value=0.2,
    )
    base_tr, iv_tr = apply_intervention(engine, s0, action0, spec, seed=99)
    assert base_tr.emission.data["accepted"] is True
    assert iv_tr.emission.data["accepted"] is True
    w_iv = WorldState.from_state(iv_tr.next_state)
    assert w_iv.agents["agent-0"].status == 0.2

    # On the intervened state branch, agent-0 selects a developmental decision
    candidates = legal_candidates(iv_tr.next_state, "agent-0")
    cand_reg = [
        c for c in candidates
        if c.action_id.startswith("register_capability:") and c.permitted
    ][0]
    dec_reg = Decision(
        agent_id="agent-0",
        sequence=1,
        tick=w_iv.tick,
        candidate=cand_reg,
        activation=(0.0,) * 8,
        ratios=(0.125,) * 8,
        score=1.0,
    )
    tr1, out1 = execute_decision(engine, iv_tr.next_state, dec_reg)
    assert out1.verified is True
    w1 = WorldState.from_state(tr1.next_state)
    assert len(w1.capabilities) >= 2

    # Verify Stage 1 replay over the trajectory reproduces without divergence
    replayed = replay_transitions(
        engine,
        initial_state=iv_tr.next_state,
        transitions=[tr1],
    )
    assert replayed.exact_match is True
    assert replayed.matched == 1
    assert not replayed.mismatches
    assert not replayed.invariant_failures


