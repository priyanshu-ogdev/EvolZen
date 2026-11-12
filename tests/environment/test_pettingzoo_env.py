"""Unit and PettingZoo AEC API tests for `evolzen.environment.pettingzoo_env`."""
from __future__ import annotations

import numpy as np
import pytest
from pettingzoo.test import api_test  # type: ignore[import-untyped]

from evolzen.environment import SocialSandboxAECEnv, SocialSandboxEngine
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType, WorldState


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
