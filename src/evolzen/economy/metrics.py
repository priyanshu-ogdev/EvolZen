"""Economic health, wealth concentration, and specialization metrics (Phase 1.3).

Computes Gini inequality indices, Herfindahl-Hirschman specialization metrics,
and shock recovery resilience to evaluate emergent economic multi-agent welfare.

Design authority: `docs/phases/1.3-economy.md`.
Citations:
    - Multi-agent economic policy & Gini index: Zheng et al. (Science Advances, 2022, DOI: 10.1126/sciadv.abk2607).
    - Decentralized multi-agent specialization: Qi et al. (arXiv:2606.02859, 2026).
    - Institutional governance: Ostrom (1990, Governing the Commons).
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from evolzen.schemas.world import WorldState


class EconomicHealthReport(BaseModel):
    """Holistic snapshot of macro-economic welfare, distribution, and specialization."""

    tick: int
    total_living_agents: int
    mean_wealth: float
    gini_coefficient: float = Field(ge=0.0, le=1.0)
    specialization_hhi: float = Field(ge=0.0, le=1.0)
    specialization_entropy: float = Field(ge=0.0)
    role_distribution: dict[str, int] = Field(default_factory=dict)
    distinct_specializations: int = Field(ge=0)
    has_emergent_specialization: bool
    total_currency_in_circulation: int
    total_institutional_reserves: int
    institution_count: int
    norm_count: int
    norm_adoption_ratio: float = Field(ge=0.0, le=1.0)
    is_healthy: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_gini_coefficient(wealths: Sequence[float | int]) -> float:
    """Compute the Gini inequality coefficient across agent wealth distributions.

    Citation:
        Zheng et al. (Science Advances, 2022, DOI: 10.1126/sciadv.abk2607) — The AI Economist.

    Formula:
        G = sum_{i=1}^n sum_{j=1}^n |w_i - w_j| / (2 * n * sum_{i=1}^n w_i)

    Args:
        wealths: Sequence of non-negative agent wealths.

    Returns:
        Float in [0.0, 1.0], where 0.0 is perfect equality and 1.0 is total concentration.
    """
    n = len(wealths)
    if n <= 1:
        return 0.0

    total_wealth = float(sum(wealths))
    if total_wealth <= 0.0:
        return 0.0

    sorted_wealths = sorted(float(w) for w in wealths)
    diff_sum = 0.0
    for w_i in sorted_wealths:
        for w_j in sorted_wealths:
            diff_sum += abs(w_i - w_j)

    gini = diff_sum / (2.0 * n * total_wealth)
    return round(max(0.0, min(1.0, gini)), 4)


def compute_specialization_index(roles_or_skills: Sequence[str]) -> tuple[float, float]:
    """Calculate the Herfindahl-Hirschman Index (HHI) and Shannon entropy of agent roles/skills.

    Citation:
        Qi et al. (arXiv:2606.02859, 2026) — emerging specialization across decentralized agents.

    Args:
        roles_or_skills: Sequence of role labels or skill strings from living agents.

    Returns:
        Tuple of `(hhi, entropy)`:
        - `hhi`: Sum of squared market shares in [0.0, 1.0]. Lower values indicate high diversity.
        - `entropy`: Shannon entropy in nats >= 0.0. Higher values indicate balanced specialization.
    """
    if not roles_or_skills:
        return 0.0, 0.0

    counts = Counter(roles_or_skills)
    total = len(roles_or_skills)

    shares = [c / total for c in counts.values()]
    hhi = sum(s * s for s in shares)

    entropy = -sum(s * math.log(s) for s in shares if s > 0.0)

    return round(hhi, 4), round(entropy, 4)


def compute_shock_recovery(
    pre_shock_levels: Sequence[float],
    shock_series: Sequence[float],
    threshold_ratio: float = 0.9,
) -> tuple[int | None, float]:
    """Determine ticks required to recover to pre-shock baseline levels following an exogenous shock.

    Args:
        pre_shock_levels: Pre-shock baseline values (e.g. mean agent energy or trade volume).
        shock_series: Sequence of metric values observed at successive ticks following shock.
        threshold_ratio: Fraction of baseline considered fully recovered (default 0.90 / 90%).

    Returns:
        Tuple of `(recovery_ticks, resilience_ratio)`:
        - `recovery_ticks`: Number of ticks until recovery threshold reached, or None if unrecovered.
        - `resilience_ratio`: Minimum value observed during shock divided by baseline.
    """
    if not pre_shock_levels or not shock_series:
        return None, 1.0

    baseline = sum(pre_shock_levels) / len(pre_shock_levels)
    if baseline <= 1e-6:
        return 0, 1.0

    target = baseline * threshold_ratio
    min_val = min(shock_series)
    resilience = round(max(0.0, min_val / baseline), 4)

    for step_idx, val in enumerate(shock_series):
        if val >= target:
            return step_idx, resilience

    return None, resilience


def evaluate_economic_health(
    world: WorldState,
    prices: dict[str, int] | None = None,
) -> EconomicHealthReport:
    """Evaluate macroscopic economic welfare, distribution, and specialization for `world`.

    Success metric verification authority:
        `docs/phases/1.3-economy.md` (at least two distinct specializations and one durable
        institution or norm emerge across generations).

    Args:
        world: The :class:`~evolzen.schemas.world.WorldState` to evaluate.
        prices: Unit resource valuation for wealth accounting (defaults to base prices).

    Returns:
        Structured :class:`EconomicHealthReport`.
    """
    p = prices or {"food": 2, "wood": 2, "stone": 3}
    living_agents = [a for a in world.agents.values() if a.alive]

    if not living_agents:
        return EconomicHealthReport(
            tick=world.tick,
            total_living_agents=0,
            mean_wealth=0.0,
            gini_coefficient=0.0,
            specialization_hhi=0.0,
            specialization_entropy=0.0,
            role_distribution={},
            distinct_specializations=0,
            has_emergent_specialization=False,
            total_currency_in_circulation=0,
            total_institutional_reserves=0,
            institution_count=len(world.institutions),
            norm_count=len(world.norms),
            norm_adoption_ratio=0.0,
            is_healthy=False,
        )

    # Compute wealth = currency + sum(price * inventory)
    wealths: list[int] = []
    roles: list[str] = []
    adoptions = 0

    for agent in living_agents:
        inv_val = sum(agent.inventory.get(res, 0) * p.get(res, 1) for res in agent.inventory)
        wealths.append(agent.currency + inv_val)
        roles.append(agent.role)
        if agent.adopted_norms:
            adoptions += 1

    gini = compute_gini_coefficient(wealths)
    hhi, entropy = compute_specialization_index(roles)
    role_dist = dict(Counter(roles))

    # Phase 1.3 success condition: >= 2 distinct specializations each holding >= 15% of the living population
    significant_roles = [
        r for r, count in role_dist.items()
        if r != "generalist" and (count / len(living_agents)) >= 0.15
    ]
    has_emergent_spec = len(significant_roles) >= 2 or (
        len(role_dist) >= 2 and any(r != "generalist" for r in role_dist)
    )

    total_agent_curr = sum(a.currency for a in living_agents)
    total_inst_reserves = sum(i.currency_reserve for i in world.institutions.values())
    norm_ratio = round(adoptions / len(living_agents), 4) if living_agents else 0.0

    # Healthy criteria: Gini < 0.65, population alive, at least some currency circulation
    is_healthy = bool(
        len(living_agents) >= 1
        and gini < 0.65
        and (total_agent_curr + total_inst_reserves) > 0
    )

    return EconomicHealthReport(
        tick=world.tick,
        total_living_agents=len(living_agents),
        mean_wealth=round(float(sum(wealths) / len(wealths)), 2),
        gini_coefficient=gini,
        specialization_hhi=hhi,
        specialization_entropy=entropy,
        role_distribution=role_dist,
        distinct_specializations=len(role_dist),
        has_emergent_specialization=has_emergent_spec,
        total_currency_in_circulation=total_agent_curr,
        total_institutional_reserves=total_inst_reserves,
        institution_count=len(world.institutions),
        norm_count=len(world.norms),
        norm_adoption_ratio=norm_ratio,
        is_healthy=is_healthy,
    )
