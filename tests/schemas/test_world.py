"""Schema validation and round-trip tests for `evolzen.schemas.world` and `ExogenousInput`."""
from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from evolzen.environment.world_state import build_default_world
from evolzen.schemas import Action, Emission, ExogenousInput, State, Transition
from evolzen.schemas.world import (
    ActionType,
    CapabilityPackage,
    GrowthAttribution,
    GrowthCategory,
    GrowthEvent,
    WorldAgentState,
    WorldState,
)


def test_world_state_canonical_roundtrip_is_deterministic() -> None:
    w1 = build_default_world(seed=7, run_id="r1")
    w2 = build_default_world(seed=7, run_id="r1")
    assert w1.state_hash() == w2.state_hash()
    s1 = w1.to_state()
    s2 = w2.to_state()
    assert s1.state_id == s2.state_id
    assert s1.data == s2.data
    restored = WorldState.from_state(s1)
    assert restored == w1


def test_world_records_forbid_extra_fields_and_nonfinite_floats() -> None:
    with pytest.raises(ValidationError):
        ExogenousInput(tick=1, unexpected=True)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        WorldAgentState(
            agent_id="a0",
            location_id="plaza",
            lineage_id="lin-0",
            energy=math.nan,
        )


def test_transition_preserves_backward_compatibility_and_exogenous_fields() -> None:
    legacy = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a0", action_type="wait"),
        emission=Emission(data={"ok": True}),
        next_state=State(data={"tick": 1}),
    )
    assert legacy.seed == 0
    assert legacy.exogenous_input.events == ()

    exog = ExogenousInput(tick=3, events=({"type": "shock"},))
    rich = Transition(
        state=State(data={"tick": 2}),
        action=Action(agent_id="a0", action_type="wait"),
        exogenous_input=exog,
        seed=99,
        emission=Emission(data={"ok": True}),
        next_state=State(data={"tick": 3}),
    )
    restored = Transition.model_validate_json(rich.model_dump_json())
    assert restored.seed == 99
    assert restored.exogenous_input.tick == 3
    assert restored.exogenous_input.events == ({"type": "shock"},)


def test_growth_event_and_capability_package_validation() -> None:
    ev = GrowthEvent(
        event_id="ev-1",
        tick=5,
        category=GrowthCategory.ARTIFACT_CAPABILITY,
        attribution=GrowthAttribution.AGENT_ACTION,
        actor_id="agent-0",
        entity_id="art-1",
        summary="Crafted tool",
        transition_id="t-1",
    )
    assert ev.category == GrowthCategory.ARTIFACT_CAPABILITY

    pkg = CapabilityPackage(package_id="pkg-1", output_kind="plow")
    assert pkg.evidence_id == ""
    assert not (pkg.verified_replay and pkg.verified_intervention and pkg.verified_containment)
    assert ActionType.IMPROVE_LOCATION.value == "improve_location"

    ev_pkg = CapabilityPackage(
        package_id="pkg-2",
        output_kind="cart",
        evidence_id="ev-2",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )
    assert ev_pkg.evidence_id == "ev-2"

