"""Phase 1.2 empirical learning and living-parent teaching.

Cook et al. (arXiv:2406.00392) motivates separating cultural transmission
from inheritance. This contextual outcome estimator is an untested baseline,
not an LLM fine-tuner or a replication of that paper.
"""

from __future__ import annotations

from evolzen.agents.development.lifecycle import stage_at
from evolzen.schemas.development import (
    BrainSnapshot,
    Lesson,
    LifeStage,
    Outcome,
    SkillEstimate,
)


def updated(snapshot: BrainSnapshot, **changes: object) -> BrainSnapshot:
    """Construct a fully revalidated immutable snapshot instead of mutating fields."""
    data = snapshot.model_dump()
    data.update(changes)
    return BrainSnapshot.model_validate(data)


def observe(snapshot: BrainSnapshot, outcome: Outcome) -> BrainSnapshot:
    """Consume one trusted verified receipt matching the sole pending action.

    A host-side verifier must construct receipts. Passing self-reported LLM
    rewards here violates the caller contract even if the schema validates.
    """
    pending = snapshot.pending
    if pending is None or not outcome.verified:
        raise ValueError("Learning needs a pending decision and verified outcome")
    if (outcome.agent_id != snapshot.birth.agent_id
            or outcome.sequence != pending.sequence
            or outcome.action_id != pending.candidate.action_id):
        raise ValueError("Outcome does not match the pending decision")
    if stage_at(snapshot, outcome.tick) == LifeStage.DEAD:
        raise ValueError("Dead agents cannot learn")
    if any(item.evidence_id == outcome.evidence_id for item in snapshot.recent):
        raise ValueError("Duplicate recent evidence")
    candidate = pending.candidate
    remaining = tuple(
        item for item in snapshot.knowledge
        if (item.context_key, item.skill_key) != (candidate.context_key, candidate.skill_key)
    )
    prior = next((item for item in snapshot.knowledge if item not in remaining), None)
    rate = snapshot.config.learning_rate
    values = outcome.rewards if prior is None else tuple(
        (1.0 - rate) * old + rate * new
        for old, new in zip(prior.values, outcome.rewards, strict=True)
    )
    estimate = SkillEstimate(
        context_key=candidate.context_key, skill_key=candidate.skill_key,
        values=values, samples=1 if prior is None else prior.samples + 1,
        evidence_id=outcome.evidence_id,
    )
    return updated(
        snapshot, tick=outcome.tick, pending=None,
        knowledge=(remaining + (estimate,))[-snapshot.config.knowledge_limit:],
        recent=(snapshot.recent + (outcome,))[-snapshot.config.memory_limit:],
    )


def teach(
    parent: BrainSnapshot,
    child: BrainSnapshot,
    context_key: str,
    skill_key: str,
    tick: int,
) -> BrainSnapshot:
    """Transfer one bounded advice item from a living mature parent to its child.

    Parent knowledge is retained. The child receives no verified samples or
    competence credit until its own environment feedback arrives.
    """
    if parent.birth.agent_id not in child.birth.parents:
        raise ValueError("Teacher must be a recorded parent")
    if parent.pending is not None or child.pending is not None:
        raise ValueError("Settle pending actions before teaching")
    if stage_at(parent, tick) not in (LifeStage.ADULT, LifeStage.ELDER):
        raise ValueError("Teacher must be alive and mature")
    if stage_at(child, tick) == LifeStage.DEAD:
        raise ValueError("Learner must be alive")
    estimate = next((item for item in parent.knowledge
                     if item.context_key == context_key and item.skill_key == skill_key), None)
    if estimate is None:
        raise ValueError("Teacher lacks grounded experience for that skill and context")
    lesson = Lesson(
        teacher_id=parent.birth.agent_id, learner_id=child.birth.agent_id,
        taught_at=tick, estimate=estimate,
    )
    # One latest advice item per parent/context/skill; repeated teaching cannot stack authority.
    lessons = tuple(item for item in child.lessons if not (
        item.teacher_id == lesson.teacher_id
        and item.estimate.context_key == context_key
        and item.estimate.skill_key == skill_key
    ))
    return updated(
        child, tick=tick, lessons=(lessons + (lesson,))[-child.config.lesson_limit:],
    )
