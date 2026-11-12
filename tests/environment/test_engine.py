"""Phase 1.1 SocialSandboxEngine tests: determinism, growth, shocks, and legality."""
from __future__ import annotations

from evolzen.environment import (
    SOCIAL_SANDBOX_SPEC,
    Environment,
    SocialSandboxEngine,
    summarize_growth,
)
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import (
    ActionType,
    CapabilityPackage,
    GrowthCategory,
    GrowthEvent,
    WorldState,
)


def test_engine_satisfies_environment_protocol_and_spec() -> None:
    engine: Environment = SocialSandboxEngine()
    state = engine.reset()
    assert not engine.is_terminal(state)
    tr = engine.step(state, Action(agent_id="agent-0", action_type=ActionType.WAIT))
    assert tr.emission.data["accepted"] is True
    assert set(SOCIAL_SANDBOX_SPEC.emission_fields).issubset(tr.emission.data.keys())


def test_zero_hidden_mutable_state_determinism() -> None:
    engine_a = SocialSandboxEngine(default_seed=101)
    engine_b = SocialSandboxEngine(default_seed=101)
    s_a = engine_a.reset()
    s_b = engine_b.reset()
    assert s_a.data == s_b.data

    actions = [
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "wood", "amount": 2}),
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "stone", "amount": 1}),
        Action(agent_id="agent-0", action_type=ActionType.CRAFT, params={"kind": "tool"}),
    ]
    for idx, act in enumerate(actions):
        exog = ExogenousInput(tick=idx + 1, events=({"type": "regen"},) if idx == 2 else ())
        t_a = engine_a.step(s_a, act, exogenous_input=exog, seed=101)
        t_b = engine_b.step(s_b, act, exogenous_input=exog, seed=101)
        assert t_a.transition_id == t_b.transition_id
        assert t_a.emission.data == t_b.emission.data
        assert t_a.next_state.data == t_b.next_state.data
        s_a = t_a.next_state
        s_b = t_b.next_state


def test_legality_and_capability_verification_gates() -> None:
    engine = SocialSandboxEngine(default_seed=7)
    s0 = engine.reset()

    bad_agent = engine.step(s0, Action(agent_id="ghost", action_type=ActionType.WAIT))
    assert bad_agent.emission.data["accepted"] is False

    unverified_pkg = CapabilityPackage(
        package_id="unverified:v1",
        output_kind="bridge",
        verified_replay=True,
        verified_intervention=False,
        verified_containment=False,
    )
    bad_cap = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": unverified_pkg.model_dump(mode="json")},
        ),
    )
    assert bad_cap.emission.data["accepted"] is False
    assert "unverified:v1" not in WorldState.from_state(bad_cap.next_state).capabilities

    # Underage reproduction fails, adult reproduction succeeds
    young_birth = engine.step(
        s0, Action(agent_id="agent-0", action_type=ActionType.SPAWN_OFFSPRING, params={"child_id": "kid"})
    )
    assert young_birth.emission.data["accepted"] is False

    # Advance clock to adulthood and mark dead at lifespan
    adult_state = engine.reset(initial_agent_age=350)
    adult_birth = engine.step(
        adult_state,
        Action(agent_id="agent-0", action_type=ActionType.SPAWN_OFFSPRING, params={"child_id": "kid-1"}),
    )
    assert adult_birth.emission.data["accepted"] is True
    assert "kid-1" in WorldState.from_state(adult_birth.next_state).agents

    expired = engine.step(
        adult_state,
        Action(agent_id="agent-0", action_type=ActionType.WAIT),
        exogenous_input=ExogenousInput(tick=1500),
    )
    assert WorldState.from_state(expired.next_state).agents["agent-0"].alive is False
    dead_act = engine.step(expired.next_state, Action(agent_id="agent-0", action_type=ActionType.WAIT))
    assert dead_act.emission.data["accepted"] is False


def test_long_run_produces_durable_growth_in_at_least_three_categories_and_survives_shock() -> None:
    engine = SocialSandboxEngine(default_seed=19, max_ticks=500)
    state = engine.reset(initial_agent_age=320)
    growth_events: list[GrowthEvent] = []

    plan = [
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "wood", "amount": 2}),
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "stone", "amount": 1}),
        Action(agent_id="agent-0", action_type=ActionType.CRAFT, params={"kind": "tool"}),
        Action(agent_id="agent-1", action_type=ActionType.FOUND_INSTITUTION, params={"name": "Commons"}),
        Action(agent_id="agent-2", action_type=ActionType.PROPOSE_NORM, params={"title": "Rationing"}),
        Action(agent_id="agent-3", action_type=ActionType.ASSIGN_ROLE, params={"role": "steward"}),
        Action(agent_id="agent-1", action_type=ActionType.SPAWN_OFFSPRING, params={"child_id": "child-1"}),
    ]
    for act in plan:
        tr = engine.step(state, act)
        assert tr.emission.data["accepted"] is True, tr.emission.data["reason"]
        assert tr.emission.data["invariant_passed"] is True
        growth_events.extend(GrowthEvent.model_validate(g) for g in tr.emission.data["growth_events"])
        state = tr.next_state

    summary = summarize_growth(growth_events)
    populated_categories = [cat for cat, count in summary.items() if count > 0]
    assert len(populated_categories) >= 4
    assert summary[GrowthCategory.ARTIFACT_CAPABILITY] >= 1
    assert summary[GrowthCategory.CONTRACT_MARKET_INSTITUTION] >= 1
    assert summary[GrowthCategory.NORM_BELIEF_MANUAL] >= 1
    assert summary[GrowthCategory.AGENT_ROLE_LINEAGE] >= 2

    # Inject a severe drought shock and verify world survives and recovers via exogenous regen
    shock_tr = engine.step(
        state,
        Action(agent_id="agent-0", action_type=ActionType.WAIT),
        exogenous_input=ExogenousInput(
            tick=WorldState.from_state(state).tick + 1,
            events=({"type": "shock", "deplete_fraction": 0.6, "shock_factor": 0.25},),
        ),
    )
    shocked_world = WorldState.from_state(shock_tr.next_state)
    shocked_food = sum(loc.resources["food"] for loc in shocked_world.locations.values())
    assert shocked_world.locations["plaza"].shock_factor == 0.25

    state = shock_tr.next_state
    for tick_offset in range(6):
        state = engine.step(
            state,
            Action(agent_id=f"agent-{tick_offset % 4}", action_type=ActionType.WAIT),
            exogenous_input=ExogenousInput(
                tick=WorldState.from_state(state).tick + 1,
                events=({"type": "regen"},),
            ),
        ).next_state

    recovered_world = WorldState.from_state(state)
    recovered_food = sum(loc.resources["food"] for loc in recovered_world.locations.values())
    assert recovered_food > shocked_food
    assert recovered_world.locations["plaza"].shock_factor == 1.0
    assert not engine.is_terminal(state)


def test_trade_contracts_institutions_and_verified_capability_craft() -> None:
    engine = SocialSandboxEngine(default_seed=29, num_locations=1, num_agents=3)
    state = engine.reset(seed=29, initial_agent_age=320)

    verified_pkg = CapabilityPackage(
        package_id="craft:cart:v1",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1},
        output_kind="cart",
        min_age=100,
        evidence_id="ev-cart-1",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    steps = [
        Action(
            agent_id="agent-0",
            action_type=ActionType.TRADE,
            params={"counterparty_id": "agent-1", "offer_resource": "food", "offer_qty": 1, "price": 4},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.PROPOSE_CONTRACT,
            params={
                "contract_id": "c-1",
                "counterparty_id": "agent-2",
                "offer_resource": "wood",
                "offer_qty": 1,
                "request_resource": "food",
                "request_qty": 1,
            },
        ),
        Action(
            agent_id="agent-2",
            action_type=ActionType.FULFILL_CONTRACT,
            params={"contract_id": "c-1"},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "guild-1", "name": "Artisans", "seed_currency": 5},
        ),
        Action(
            agent_id="agent-1",
            action_type=ActionType.JOIN_INSTITUTION,
            params={"institution_id": "guild-1"},
        ),
        Action(
            agent_id="agent-1",
            action_type=ActionType.CONTRIBUTE_INSTITUTION,
            params={"institution_id": "guild-1", "resource": "food", "amount": 1},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": verified_pkg.model_dump(mode="json")},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.CRAFT,
            params={"package_id": "craft:cart:v1", "artifact_id": "cart-1"},
        ),
    ]
    for act in steps:
        tr = engine.step(state, act)
        assert tr.emission.data["accepted"] is True, tr.emission.data["reason"]
        assert tr.emission.data["invariant_passed"] is True
        state = tr.next_state

    final_world = WorldState.from_state(state)
    assert final_world.contracts["c-1"].status == "fulfilled"
    assert set(final_world.institutions["guild-1"].member_ids) == {"agent-0", "agent-1"}
    assert final_world.institutions["guild-1"].treasury["food"] == 1
    assert final_world.artifacts["cart-1"].kind == "cart"
    assert final_world.agents["agent-0"].currency == 19  # 20 + 4 (trade) - 5 (found_institution)


def test_craft_rejects_unregistered_arbitrary_recipes_and_unverified_packages() -> None:
    engine = SocialSandboxEngine(default_seed=31)
    s0 = engine.reset(seed=31)

    arbitrary = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.CRAFT,
            params={"kind": "spaceship", "recipe": {"wood": 1}, "artifact_id": "ship-1"},
        ),
    )
    assert arbitrary.emission.data["accepted"] is False
    assert "ship-1" not in WorldState.from_state(arbitrary.next_state).artifacts

    unknown_pkg = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.CRAFT,
            params={"package_id": "craft:missing:v1"},
        ),
    )
    assert unknown_pkg.emission.data["accepted"] is False

    # Verified package with min_age=400 rejects underage crafter
    adult_s = engine.reset(seed=31, initial_agent_age=310)
    gated_pkg = CapabilityPackage(
        package_id="craft:loom:v1",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1},
        output_kind="loom",
        min_age=400,
        evidence_id="ev-loom-1",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    reg = engine.step(
        adult_s,
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": gated_pkg.model_dump(mode="json")},
        ),
    )
    assert reg.emission.data["accepted"] is True
    underage_craft = engine.step(
        reg.next_state,
        Action(
            agent_id="agent-0",
            action_type=ActionType.CRAFT,
            params={"package_id": "craft:loom:v1", "artifact_id": "loom-1"},
        ),
    )
    assert underage_craft.emission.data["accepted"] is False
    assert "minimum age" in underage_craft.emission.data["reason"]


def test_found_institution_enforces_world_adulthood_age() -> None:
    engine = SocialSandboxEngine(default_seed=37)
    young_state = engine.reset(seed=37, initial_agent_age=0)

    # Attempting to override min_age=0 below world.adulthood_age (300) must fail
    rejected = engine.step(
        young_state,
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "guild-early", "name": "Early", "min_age": 0},
        ),
    )
    assert rejected.emission.data["accepted"] is False
    assert "guild-early" not in WorldState.from_state(rejected.next_state).institutions

    adult_state = engine.reset(seed=37, initial_agent_age=310)
    tightened = engine.step(
        adult_state,
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "guild-elder", "name": "Elders", "min_age": 400},
        ),
    )
    assert tightened.emission.data["accepted"] is False


def test_register_capability_requires_evidence_id_and_craft_action_type() -> None:
    engine = SocialSandboxEngine(default_seed=41)
    s0 = engine.reset(seed=41)

    no_evidence = CapabilityPackage(
        package_id="craft:noev:v1",
        action_type=ActionType.CRAFT,
        output_kind="basket",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    res_no_ev = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": no_evidence.model_dump(mode="json")},
        ),
    )
    assert res_no_ev.emission.data["accepted"] is False
    assert "evidence_id" in res_no_ev.emission.data["reason"]

    wrong_type = CapabilityPackage(
        package_id="gather:hack:v1",
        action_type=ActionType.GATHER,
        output_kind="hack",
        evidence_id="ev-hack",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    res_wrong_type = engine.step(
        s0,
        Action(
            agent_id="agent-0",
            action_type=ActionType.REGISTER_CAPABILITY,
            params={"package": wrong_type.model_dump(mode="json")},
        ),
    )
    assert res_wrong_type.emission.data["accepted"] is False
    assert "action_type" in res_wrong_type.emission.data["reason"]


def test_empty_string_ids_and_max_ticks_guard_reject_cleanly() -> None:
    engine = SocialSandboxEngine(default_seed=43, max_ticks=5)
    s_adult = engine.reset(seed=43, initial_agent_age=320)
    # Give agent-0 stone to test artifact_id=""
    s_stone = engine.step(
        s_adult,
        Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "stone", "amount": 1}),
    ).next_state

    empty_cases = [
        Action(agent_id="agent-0", action_type=ActionType.CRAFT, params={"kind": "tool", "artifact_id": ""}),
        Action(
            agent_id="agent-0",
            action_type=ActionType.PROPOSE_CONTRACT,
            params={"counterparty_id": "agent-1", "contract_id": "   "},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "", "name": "Valid"},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.FOUND_INSTITUTION,
            params={"institution_id": "inst-ok", "name": ""},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.PROPOSE_NORM,
            params={"norm_id": "", "title": "Valid"},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.PROPOSE_NORM,
            params={"norm_id": "norm-ok", "title": ""},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.SPAWN_OFFSPRING,
            params={"child_id": ""},
        ),
        Action(
            agent_id="agent-0",
            action_type=ActionType.ASSIGN_ROLE,
            params={"role": ""},
        ),
    ]
    for bad_action in empty_cases:
        tr = engine.step(s_stone, bad_action)
        assert tr.emission.data["accepted"] is False

    # Test world.tick >= world.max_ticks rejects cleanly without advancing tick or applying exog
    s_at_max = engine.reset(seed=43, initial_agent_age=5)
    assert engine.is_terminal(s_at_max) is True
    capped = engine.step(
        s_at_max,
        Action(agent_id="agent-0", action_type=ActionType.WAIT),
        exogenous_input=ExogenousInput(tick=6, events=({"type": "regen"},)),
    )
    assert capped.emission.data["accepted"] is False
    assert "max_ticks" in capped.emission.data["reason"]
    assert capped.emission.data["exogenous_applied"] == []
    assert WorldState.from_state(capped.next_state).tick == 5
