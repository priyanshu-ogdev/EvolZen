"""Unit tests for `evolzen.environment.world_state`."""
from __future__ import annotations

import pytest

from evolzen.environment.invariants import check_invariants
from evolzen.environment.world_state import build_default_world, derive_rng
from evolzen.schemas.world import ActionType


def test_derive_rng_is_deterministic_and_input_sensitive() -> None:
    r1 = derive_rng(seed=7, tick=3, step_index=5, salt="alpha")
    r2 = derive_rng(seed=7, tick=3, step_index=5, salt="alpha")
    assert [r1.randint(0, 10_000) for _ in range(5)] == [
        r2.randint(0, 10_000) for _ in range(5)
    ]

    r_diff_salt = derive_rng(seed=7, tick=3, step_index=5, salt="beta")
    r_diff_tick = derive_rng(seed=7, tick=4, step_index=5, salt="alpha")
    r_diff_seed = derive_rng(seed=8, tick=3, step_index=5, salt="alpha")
    base = derive_rng(seed=7, tick=3, step_index=5, salt="alpha").randint(0, 10**9)
    assert r_diff_salt.randint(0, 10**9) != base
    assert r_diff_tick.randint(0, 10**9) != base
    assert r_diff_seed.randint(0, 10**9) != base


def test_build_default_world_topology_accounting_and_bootstrap_capability() -> None:
    w1 = build_default_world(seed=42, run_id="r1", branch_id="main", num_locations=5, num_agents=3)
    w2 = build_default_world(seed=42, run_id="r1", branch_id="main", num_locations=5, num_agents=3)
    assert w1 == w2
    assert set(w1.locations) == {"plaza", "grove", "quarry", "market_square", "sector_4"}
    assert len(w1.agents) == 3

    cap = w1.capabilities["craft:tool:v1"]
    assert cap.action_type == ActionType.CRAFT
    assert cap.output_kind == "tool"
    assert cap.evidence_id == "bootstrap:craft:tool:v1"
    assert cap.verified_replay and cap.verified_intervention and cap.verified_containment

    report = check_invariants(None, w1)
    assert report.passed is True

    # Single location has no neighbors; invalid counts raise ValueError
    solo = build_default_world(num_locations=1, num_agents=1)
    assert solo.locations["plaza"].neighbors == ()
    with pytest.raises(ValueError, match="num_locations"):
        build_default_world(num_locations=0)
    with pytest.raises(ValueError, match="num_agents"):
        build_default_world(num_agents=0)
    with pytest.raises(ValueError, match="num_agents"):
        build_default_world(num_agents=5, max_agents=4)
