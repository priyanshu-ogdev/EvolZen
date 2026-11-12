"""Invariant verification and property-based tests for `evolzen.environment`."""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from evolzen.environment import SocialSandboxEngine, check_invariants
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import ActionType, WorldState


def test_invariants_detect_conservation_and_ownership_violations() -> None:
    engine = SocialSandboxEngine(default_seed=1)
    s0 = engine.reset()
    w0 = WorldState.from_state(s0)
    assert check_invariants(None, w0).passed is True

    # Tamper with food inventory without accounting update
    bad_agent = w0.agents["agent-0"].model_copy(update={"inventory": {"food": 999, "wood": 2, "stone": 0}})
    bad_agents = dict(w0.agents)
    bad_agents["agent-0"] = bad_agent
    bad_world = w0.model_copy(update={"agents": bad_agents})
    report = check_invariants(w0, bad_world)
    assert report.passed is False
    failed = {c.name for c in report.checks if not c.passed}
    assert "resource_conservation" in failed

    # Tamper with clock regression
    regressed = w0.model_copy(update={"tick": 0})
    w1 = w0.model_copy(update={"tick": 5})
    assert check_invariants(w1, regressed).passed is False


@given(
    choices=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=3),
            st.sampled_from(["wait", "gather_food", "gather_wood", "consume_food", "move"]),
            st.booleans(),
        ),
        min_size=1,
        max_size=25,
    )
)
def test_random_action_sequences_always_preserve_invariants(
    choices: list[tuple[int, str, bool]],
) -> None:
    engine = SocialSandboxEngine(default_seed=21)
    state = engine.reset(seed=21)
    for idx, (agent_idx, choice, do_regen) in enumerate(choices):
        world = WorldState.from_state(state)
        agent_id = f"agent-{agent_idx}"
        loc = world.locations[world.agents[agent_id].location_id]
        if choice == "wait":
            action = Action(agent_id=agent_id, action_type=ActionType.WAIT)
        elif choice == "gather_food":
            action = Action(agent_id=agent_id, action_type=ActionType.GATHER, params={"resource": "food", "amount": 1})
        elif choice == "gather_wood":
            action = Action(agent_id=agent_id, action_type=ActionType.GATHER, params={"resource": "wood", "amount": 1})
        elif choice == "consume_food":
            action = Action(agent_id=agent_id, action_type=ActionType.CONSUME, params={"resource": "food", "amount": 1})
        else:
            action = Action(
                agent_id=agent_id,
                action_type=ActionType.MOVE,
                params={"target_location": loc.neighbors[0]},
            )
        exog = ExogenousInput(
            tick=world.tick + 1,
            events=({"type": "regen"},) if do_regen and idx % 3 == 0 else (),
        )
        tr = engine.step(state, action, exogenous_input=exog, seed=21)
        assert tr.emission.data["invariant_passed"] is True
        state = tr.next_state

