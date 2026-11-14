"""Phase 1.2 developmental decision core with Tier-0 and Tier-1 multi-objective scalarization.

The implemented learning loop ranks declared candidate actions using internal homeostatic drive
priorities and learned empirical outcome vectors. Features:
- Tier-0 Baseline: Linear scalarization with greedy argmax selection.
- Tier-1 Multi-Objective: Augmented Chebyshev scalarization (Hayes et al., AAMAS 2022; Van Moffaert
  & Nowé, JMLR 2014) ensuring Pareto optimality on non-convex fronts, UCB1 epistemic uncertainty
  exploration bonus (Auer et al., Machine Learning 2002), and Mellowmax temperature-controlled
  softmax candidate exploration (Asadi & Littman, ICML 2017).

Citations:
- Hayes et al. (A practical guide to multi-objective reinforcement learning, AAMAS 2022,
  DOI: 10.1007/s10458-022-09552-y);
- Van Moffaert & Nowé (Multi-objective reinforcement learning using sets of Pareto dominating policies,
  JMLR 2014);
- Auer, Cesa-Bianchi & Fischer (Finite-time analysis of the multiarmed bandit problem, Machine Learning 2002);
- Asadi & Littman (An alternative softmax operator for reinforcement learning, ICML 2017, arXiv:1612.05628).

All empirical decision-making benchmarks remain untested until Phase 1.2 population experiments are run.
"""

from __future__ import annotations

import math
import random

from evolzen.agents.development.learning import updated
from evolzen.agents.development.lifecycle import stage_at
from evolzen.agents.development.motivation import drive_step
from evolzen.schemas.development import BrainSnapshot, Candidate, Decision, LifeStage


def advance(snapshot: BrainSnapshot, tick: int) -> BrainSnapshot:
    """Advance the world clock without automatically learning or granting skills.

    Terminal expiry cancels pending work. The host must log that cancellation.
    A live pending action must be settled before advancing independently.
    """
    stage = stage_at(snapshot, tick)
    if snapshot.pending is not None and stage != LifeStage.DEAD:
        raise ValueError("Cannot advance with an unsettled action")
    return updated(snapshot, tick=tick, pending=None)


def linear_score(
    ratios: tuple[float, ...],
    values: tuple[float, ...],
    cost: float,
) -> float:
    """Compute Tier-0 linear scalarization utility: sum_k p_k * v_k - cost."""
    return sum(ratio * val for ratio, val in zip(ratios, values, strict=True)) - cost


def chebyshev_score(
    ratios: tuple[float, ...],
    values: tuple[float, ...],
    cost: float,
    *,
    utopia: tuple[float, ...] = (1.0,) * 8,
    rho: float = 0.01,
) -> float:
    """Compute Tier-1 Augmented Chebyshev scalarization utility.

    Evaluates the worst-case weighted deficit from the utopia point z*, augmented
    with a linear term to guarantee strict Pareto optimality (Hayes et al., AAMAS 2022):
        S(v, p) = -max_k { p_k * (z*_k - v_k) } + rho * sum_k (p_k * v_k) - cost

    Args:
        ratios: 8-D normalized motive priority weights (p_k >= 0, sum p_k = 1.0).
        values: 8-D predicted or estimated outcome vector (v_k in [-1.0, 1.0]).
        cost: Action execution cost in [0.0, 1.0].
        utopia: Ideal outcome reference vector z* (default: 1.0 on all coordinates).
        rho: Augmentation factor ensuring strict Pareto efficiency (default: 0.01).

    Returns:
        Augmented Chebyshev utility scalar.
    """
    deficits = tuple(
        p_k * (z_k - v_k)
        for p_k, z_k, v_k in zip(ratios, utopia, values, strict=True)
    )
    max_deficit = max(deficits)
    linear_term = sum(p_k * v_k for p_k, v_k in zip(ratios, values, strict=True))
    return -max_deficit + rho * linear_term - cost


def compute_ucb_values(
    values: tuple[float, ...],
    samples: int,
    total_decisions: int,
    exploration_c: float,
) -> tuple[float, ...]:
    """Apply UCB1 epistemic uncertainty exploration bonus to outcome values.

    Args:
        values: 8-D empirical outcome values.
        samples: Number of observations recorded for this skill and context (n >= 0).
        total_decisions: Total decisions made by the agent so far (N >= 0).
        exploration_c: Exploration coefficient c_explore >= 0.

    Returns:
        Upper confidence bound outcome vector clamped to [-1.0, 1.0].
    """
    if exploration_c <= 0.0:
        return values
    bonus = exploration_c * math.sqrt(math.log(max(1, total_decisions) + 1.0) / (samples + 1.0))
    return tuple(min(1.0, max(-1.0, v + bonus)) for v in values)


def mellowmax_probabilities(
    scores: tuple[float, ...],
    beta: float = 10.0,
) -> tuple[float, ...]:
    """Compute softmax exploration probabilities over candidate action scores.

    Args:
        scores: Tuple of candidate scalar utility scores.
        beta: Softmax temperature parameter (beta > 0).

    Returns:
        Probability distribution tuple summing to 1.0.
    """
    if not scores:
        return ()
    if beta <= 0.0:
        uniform_p = 1.0 / len(scores)
        return (uniform_p,) * len(scores)

    max_s = max(scores)
    exp_scores = [math.exp(min(500.0, max(-500.0, beta * (s - max_s)))) for s in scores]
    total_exp = sum(exp_scores)
    if total_exp <= 0.0:
        uniform_p = 1.0 / len(scores)
        return (uniform_p,) * len(scores)
    return tuple(p / total_exp for p in exp_scores)


def decide(
    snapshot: BrainSnapshot,
    context: tuple[float, ...],
    candidates: tuple[Candidate, ...],
    tick: int,
    *,
    seed: int | None = None,
) -> BrainSnapshot:
    """Rank legal, age-accessible candidates using motive ratios, experience, and decision policy.

    Supports Tier-0 linear scalarization (default) and Tier-1 Augmented Chebyshev scalarization
    with UCB1 exploration and Mellowmax temperature sampling when configured via
    `snapshot.config.use_tier1_decision`.

    Args:
        snapshot: Current agent developmental brain snapshot.
        context: 8-D environmental context signal.
        candidates: Tuple of declared candidate actions.
        tick: Simulation clock tick.
        seed: Optional pseudo-random seed for stochastic exploration sampling. When None,
              deterministic highest-scoring candidate selection is used.

    Returns:
        Updated BrainSnapshot with pending Decision.
    """
    stage = stage_at(snapshot, tick)
    if stage == LifeStage.DEAD or snapshot.pending is not None:
        raise ValueError("Agent is dead or already awaiting an outcome")
    if not candidates or len(candidates) > snapshot.config.max_candidates:
        raise ValueError("Candidate budget must be nonempty and bounded")
    if len({item.action_id for item in candidates}) != len(candidates):
        raise ValueError("Candidate action IDs must be unique")
    age = tick - snapshot.birth.born_at
    activation, ratios = drive_step(
        snapshot.birth.genome, context, snapshot.activation, age / snapshot.config.lifespan,
    )
    eligible = tuple(item for item in candidates if item.permitted and item.minimum_age <= age)
    if not eligible:
        raise ValueError("No legal developmental action is available")

    config = snapshot.config
    use_tier1 = config.use_tier1_decision

    def evaluate_candidate(candidate: Candidate) -> float:
        estimate = next(
            (
                item
                for item in snapshot.knowledge
                if item.context_key == candidate.context_key
                and item.skill_key == candidate.skill_key
            ),
            None,
        )
        if estimate is None:
            values = candidate.predicted
            samples = 0
            lesson = next(
                (
                    item
                    for item in reversed(snapshot.lessons)
                    if item.estimate.context_key == candidate.context_key
                    and item.estimate.skill_key == candidate.skill_key
                ),
                None,
            )
            if lesson is not None:
                weight = config.advice_weight
                values = tuple(
                    (1.0 - weight) * value + weight * advice
                    for value, advice in zip(values, lesson.estimate.values, strict=True)
                )
        else:
            values = estimate.values
            samples = estimate.samples

        if use_tier1:
            ucb_values = compute_ucb_values(
                values,
                samples=samples,
                total_decisions=snapshot.sequence,
                exploration_c=config.exploration_c,
            )
            return chebyshev_score(
                ratios,
                ucb_values,
                candidate.cost,
                rho=config.chebyshev_rho,
            )

        return linear_score(ratios, values, candidate.cost)

    scores_by_id = {c.action_id: evaluate_candidate(c) for c in eligible}

    if seed is not None and use_tier1:
        candidate_scores = tuple(scores_by_id[c.action_id] for c in eligible)
        probs = mellowmax_probabilities(candidate_scores, beta=config.mellowmax_beta)
        rng = random.Random(seed)
        r = rng.random()
        cumulative = 0.0
        chosen = eligible[-1]
        for cand, p in zip(eligible, probs, strict=True):
            cumulative += p
            if r <= cumulative:
                chosen = cand
                break
    else:
        ranked = sorted(eligible, key=lambda item: (-scores_by_id[item.action_id], item.action_id))
        chosen = ranked[0]

    chosen_score = scores_by_id[chosen.action_id]
    decision = Decision(
        agent_id=snapshot.birth.agent_id,
        sequence=snapshot.sequence + 1,
        tick=tick,
        candidate=chosen,
        activation=activation,
        ratios=ratios,
        score=chosen_score,
    )
    return updated(
        snapshot,
        tick=tick,
        activation=activation,
        sequence=decision.sequence,
        pending=decision,
    )
