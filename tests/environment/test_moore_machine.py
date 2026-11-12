"""Unit tests for `evolzen.environment.moore_machine`."""
from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from evolzen.environment.moore_machine import SOCIAL_SANDBOX_SPEC, MooreMachineSpec
from evolzen.schemas.world import ActionType


def test_social_sandbox_spec_covers_all_action_types_and_emission_fields() -> None:
    assert SOCIAL_SANDBOX_SPEC.name == "evolzen-social-sandbox-v1"
    assert SOCIAL_SANDBOX_SPEC.action_types == tuple(action.value for action in ActionType)
    assert ActionType.IMPROVE_LOCATION.value in SOCIAL_SANDBOX_SPEC.action_types
    assert len(set(SOCIAL_SANDBOX_SPEC.emission_fields)) == len(SOCIAL_SANDBOX_SPEC.emission_fields)
    for required in ("accepted", "reason", "tick", "step_index", "rewards", "growth_events", "invariant_passed"):
        assert required in SOCIAL_SANDBOX_SPEC.emission_fields

    custom = MooreMachineSpec(name="m", action_types=("wait",), emission_fields=("accepted",))
    with pytest.raises(FrozenInstanceError):
        custom.name = "other"  # type: ignore[misc]
