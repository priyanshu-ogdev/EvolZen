"""Tests for Phase 1.3 economic health, Gini wealth concentration, and specialization metrics."""
from __future__ import annotations

import math

from evolzen.economy.metrics import (
    compute_gini_coefficient,
    compute_shock_recovery,
    compute_specialization_index,
    evaluate_economic_health,
)
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.world import InstitutionRecord, NormRecord, WorldState


def test_compute_gini_coefficient() -> None:
    """Verify Gini coefficient accurately measures wealth distribution."""
    # Perfect equality: everyone has 20 currency
    assert compute_gini_coefficient([20, 20, 20, 20]) == 0.0

    # Extreme inequality: one person owns everything
    gini_extreme = compute_gini_coefficient([0, 0, 0, 100])
    assert gini_extreme == 0.75

    # Edge cases: 0 or 1 agent
    assert compute_gini_coefficient([]) == 0.0
    assert compute_gini_coefficient([50]) == 0.0
    assert compute_gini_coefficient([0, 0, 0]) == 0.0


def test_compute_specialization_index() -> None:
    """Verify HHI and Shannon entropy reflect division of labor and role diversity."""
    # Single homogeneous role: maximum concentration
    hhi_mono, entropy_mono = compute_specialization_index(["gatherer"] * 4)
    assert hhi_mono == 1.0
    assert entropy_mono == 0.0

    # Perfect 4-way division of labor: minimum HHI, maximum entropy
    roles = ["gatherer", "craftsman", "trader", "scholar"]
    hhi_div, entropy_div = compute_specialization_index(roles)
    assert hhi_div == 0.25
    assert round(entropy_div, 2) == round(math.log(4), 2)

    # Empty sequence
    assert compute_specialization_index([]) == (0.0, 0.0)


def test_compute_shock_recovery() -> None:
    """Verify shock recovery detects rebound ticks and resilience ratio."""
    baseline = [100.0, 100.0, 100.0]

    # Rebound: drops to 30, then 50, then 92 (>= 90 target at index 2)
    series_recovered = [30.0, 50.0, 92.0, 95.0]
    rec_ticks, resilience = compute_shock_recovery(baseline, series_recovered, threshold_ratio=0.9)
    assert rec_ticks == 2
    assert resilience == 0.30

    # Permanent depression: fails to reach 90
    series_depressed = [30.0, 40.0, 45.0, 50.0]
    rec_failed, resilience_dep = compute_shock_recovery(baseline, series_depressed, threshold_ratio=0.9)
    assert rec_failed is None
    assert resilience_dep == 0.30


def test_evaluate_economic_health_with_world_state() -> None:
    """Verify evaluate_economic_health computes comprehensive welfare report from WorldState."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=4, num_locations=2)
    s0 = engine.reset(seed=42, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # Differentiate roles across agents to test specialization emergence
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(
        update={"role": "gatherer", "currency": 25, "adopted_norms": ("norm-share-1",)}
    )
    agents["agent-1"] = agents["agent-1"].model_copy(
        update={"role": "craftsman", "currency": 30, "adopted_norms": ("norm-share-1",)}
    )
    agents["agent-2"] = agents["agent-2"].model_copy(update={"role": "trader", "currency": 20})
    agents["agent-3"] = agents["agent-3"].model_copy(update={"role": "scholar", "currency": 15})

    # Add norm and institution
    norm = NormRecord(
        norm_id="norm-share-1",
        title="Share Common Surplus",
        proposer_id="agent-0",
        rule_kind="conservation",
        adopters=("agent-0", "agent-1"),
        created_tick=0,
    )
    inst = InstitutionRecord(
        institution_id="guild-trade",
        name="Merchant Guild",
        founder_id="agent-2",
        location_id="plaza",
        member_ids=("agent-2",),
        treasury={"wood": 5},
        currency_reserve=12,
        contribution_rate=0.1,
        created_tick=0,
    )

    w_rich = w0.model_copy(
        update={
            "agents": agents,
            "norms": {"norm-share-1": norm},
            "institutions": {"guild-trade": inst},
        }
    )

    report = evaluate_economic_health(w_rich)

    assert report.total_living_agents == 4
    assert report.distinct_specializations == 4
    assert report.has_emergent_specialization is True
    assert report.gini_coefficient < 0.30  # Relatively egalitarian
    assert report.institution_count == 1
    assert report.total_institutional_reserves == 12
    assert report.total_currency_in_circulation == 90  # 25 + 30 + 20 + 15
    assert report.norm_count == 1
    assert report.norm_adoption_ratio == 0.5  # 2 of 4 agents adopted
    assert report.is_healthy is True
