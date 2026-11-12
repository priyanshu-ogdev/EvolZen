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

