"""Unit tests for structured inference backends."""
from __future__ import annotations

from evolzen.agents.inference import TransformersBackend
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate
from evolzen.schemas.world import ActionType


def test_transformers_backend_build_prompt_and_offline_fallback() -> None:
    backend = TransformersBackend(offline_fallback=True)
    profile = AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-0",
        roles=("scout",),
        adopted_norms=("conserve",),
    )
    signal = (0.1, -0.2, 0.3, 0.0, -0.5, 0.4, 0.0, 0.1)
    motive_weights = (0.125,) * 8
    candidates = (
        Candidate(
            action_id="wait",
            context_key="world:loc-0",
            skill_key="wait:v1",
            predicted=(0.0,) * 8,
            cost=0.0,
            minimum_age=0,
            permitted=True,
        ),
        Candidate(
            action_id="gather:food:1",
            context_key="world:loc-0",
            skill_key="gather:food:v1",
            predicted=(0.1,) * 8,
            cost=0.05,
            minimum_age=0,
            permitted=True,
        ),
    )
    world_ctx = {"location_id": "loc-0"}

    prompt = backend.build_prompt(profile, signal, candidates, motive_weights, world_ctx)
    assert "agent-0" in prompt
    assert "wait" in prompt
    assert "gather:food:1" in prompt

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT
