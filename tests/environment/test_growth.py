"""Unit tests for `evolzen.environment.growth`."""
from __future__ import annotations

from evolzen.environment import SocialSandboxEngine
from evolzen.environment.growth import extract_growth_events, summarize_growth
from evolzen.environment.world_state import build_default_world
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import (
    ActionType,
    GrowthAttribution,
    GrowthCategory,
    GrowthEvent,
    WorldState,
)


def test_extract_growth_events_covers_all_five_categories_and_attributions() -> None:
    base = build_default_world(seed=13, initial_agent_age=310)
    plaza = base.locations["plaza"]

    # 1. Agent-attributed LOCATION_RESOURCE via IMPROVE_LOCATION
    expanded_plaza = plaza.model_copy(
        update={"capacities": {**plaza.capacities, "food": plaza.capacities["food"] + 10}}
    )
    next_agent_improve = base.model_copy(
        update={
            "tick": base.tick + 1,
            "locations": {**base.locations, "plaza": expanded_plaza},
        }
    )
    agent_events = extract_growth_events(
        base,
        next_agent_improve,
        Action(agent_id="agent-0", action_type=ActionType.IMPROVE_LOCATION, params={"target_resource": "food"}),
        ExogenousInput(tick=base.tick + 1),
        "tr-1",
    )
    assert len(agent_events) == 1
    assert agent_events[0].category == GrowthCategory.LOCATION_RESOURCE
    assert agent_events[0].attribution == GrowthAttribution.AGENT_ACTION
    assert agent_events[0].actor_id == "agent-0"
    assert agent_events[0].entity_id == "plaza:food"

    # 2. Exogenous-attributed LOCATION_RESOURCE when exogenous events exist
    exog_events = extract_growth_events(
        base,
        next_agent_improve,
        Action(agent_id="agent-0", action_type=ActionType.WAIT),
        ExogenousInput(tick=base.tick + 1, events=({"type": "expand"},)),
        "tr-2",
    )
    assert exog_events[0].attribution == GrowthAttribution.EXOGENOUS_INPUT
    assert exog_events[0].actor_id == "world"

    # 3. Endogenous-attributed LOCATION_RESOURCE when neither IMPROVE_LOCATION nor exogenous event
    endo_events = extract_growth_events(
        base,
        next_agent_improve,
        Action(agent_id="agent-0", action_type=ActionType.WAIT),
        ExogenousInput(tick=base.tick + 1),
        "tr-3",
    )
    assert endo_events[0].attribution == GrowthAttribution.ENDOGENOUS_PROCESS
    assert endo_events[0].actor_id == "world"


def test_improve_location_emits_location_resource_and_preserves_conservation() -> None:
    engine = SocialSandboxEngine(default_seed=17)
    s0 = engine.reset(seed=17)
    # Give agent-0 enough stone to perform IMPROVE_LOCATION (cost: wood=2, stone=2)
    s1 = engine.step(
        s0, Action(agent_id="agent-0", action_type=ActionType.GATHER, params={"resource": "stone", "amount": 2})
    ).next_state
    before_world = WorldState.from_state(s1)
    before_cap = before_world.locations["plaza"].capacities["food"]

    tr = engine.step(
        s1,
        Action(
            agent_id="agent-0",
            action_type=ActionType.IMPROVE_LOCATION,
            params={"target_resource": "food"},
        ),
    )
    assert tr.emission.data["accepted"] is True, tr.emission.data["reason"]
    assert tr.emission.data["invariant_passed"] is True
    after_world = WorldState.from_state(tr.next_state)
    assert after_world.locations["plaza"].capacities["food"] == before_cap + 10
    assert after_world.accounting.consumed_or_decayed["wood"] == 2
    assert after_world.accounting.consumed_or_decayed["stone"] == 2

    emitted = [GrowthEvent.model_validate(g) for g in tr.emission.data["growth_events"]]
    assert len(emitted) == 1
    assert emitted[0].category == GrowthCategory.LOCATION_RESOURCE
    assert emitted[0].attribution == GrowthAttribution.AGENT_ACTION
    assert emitted[0].actor_id == "agent-0"

    summary = summarize_growth(emitted)
    assert summary[GrowthCategory.LOCATION_RESOURCE] == 1
    assert summary[GrowthCategory.ARTIFACT_CAPABILITY] == 0
    assert set(summary.keys()) == set(GrowthCategory)
