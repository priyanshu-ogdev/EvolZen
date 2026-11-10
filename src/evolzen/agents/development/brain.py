"""Phase 1.2 deterministic developmental decision core; untested as research.

The implemented learning loop ranks declared candidate actions and learns their
observed outcome vectors. It does not execute actions, create thoughts, train
LLM weights, or run agent-generated code.
"""

from __future__ import annotations

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


def decide(
    snapshot: BrainSnapshot,
    context: tuple[float, ...],
    candidates: tuple[Candidate, ...],
    tick: int,
) -> BrainSnapshot:
    """Rank legal, age-accessible candidates using all eight ratios and experience.

    The caller supplies and independently checks domain permissions; motivated
    preference can never grant host privileges. A no-option result raises rather
    than inventing an action. Rest/wait must be explicitly supplied by the domain.
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

    def score(candidate: Candidate) -> float:
        estimate = next((item for item in snapshot.knowledge
                         if item.context_key == candidate.context_key
                         and item.skill_key == candidate.skill_key), None)
        values = candidate.predicted if estimate is None else estimate.values
        # Own experience takes precedence over inherited advice.
        if estimate is None:
            lesson = next((item for item in reversed(snapshot.lessons)
                           if item.estimate.context_key == candidate.context_key
                           and item.estimate.skill_key == candidate.skill_key), None)
            if lesson is not None:
                weight = snapshot.config.advice_weight
                values = tuple((1.0 - weight) * value + weight * advice
                               for value, advice in zip(values, lesson.estimate.values, strict=True))
        return sum(ratio * value for ratio, value in zip(ratios, values, strict=True)) - candidate.cost

    ranked = sorted(eligible, key=lambda item: (-score(item), item.action_id))
    candidate = ranked[0]
    decision = Decision(
        agent_id=snapshot.birth.agent_id, sequence=snapshot.sequence + 1, tick=tick,
        candidate=candidate, activation=activation, ratios=ratios, score=score(candidate),
    )
    return updated(
        snapshot, tick=tick, activation=activation,
        sequence=decision.sequence, pending=decision,
    )
