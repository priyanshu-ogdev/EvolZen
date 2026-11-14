"""Phase 1.2 empirical learning and living-parent teaching.

Implements contextual outcome estimation from verified environment receipts and
intergenerational cultural transmission (parental skill advice and recipe manual sharing).

Citations:
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392, 2024) for
  separating cultural transmission from genetic inheritance, living-parent advice without
  birth-time mastery copying, and bounded intergenerational blending.

Note on continual learning: This runtime module provides a verified contextual EMA
outcome estimator and living manual transmission. Full neural continual experience replay
(Rolnick et al., CLEAR, NeurIPS 2019, arXiv:1811.11682) is housed in the predictor subsystem
(`evolzen.predictor.rehearsal`).

This contextual outcome estimator is an untested baseline, not an LLM fine-tuner or a
full replication of cited papers.
"""

from __future__ import annotations

from evolzen.agents.development.lifecycle import stage_at
from evolzen.schemas.development import (
    ZERO,
    BrainSnapshot,
    Lesson,
    LifeStage,
    Outcome,
    SkillEstimate,
)
from evolzen.schemas.manual import ManualEntry, ManualEntryStatus


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
    manual_entry: ManualEntry | None = None,
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
    if manual_entry is not None and manual_entry.status == ManualEntryStatus.FALSIFIED:
        raise ValueError("Cannot teach a falsified manual entry")
    estimate = next((item for item in parent.knowledge
                     if item.context_key == context_key and item.skill_key == skill_key), None)
    if estimate is None:
        raise ValueError("Teacher lacks grounded experience for that skill and context")
    lesson = Lesson(
        teacher_id=parent.birth.agent_id, learner_id=child.birth.agent_id,
        taught_at=tick, estimate=estimate, manual_entry=manual_entry,
    )
    # One latest advice item per parent/context/skill; repeated teaching cannot stack authority.
    lessons = tuple(item for item in child.lessons if not (
        item.teacher_id == lesson.teacher_id
        and (
            (manual_entry is not None and item.manual_entry is not None and item.manual_entry.text == manual_entry.text)
            or (manual_entry is None and item.manual_entry is None and item.estimate.context_key == context_key and item.estimate.skill_key == skill_key)
            or (manual_entry is not None and item.manual_entry is None and item.estimate.context_key == context_key and item.estimate.skill_key == skill_key)
        )
    ))
    return updated(
        child, tick=tick, lessons=(lessons + (lesson,))[-child.config.lesson_limit:],
    )


def teach_manual(
    parent: BrainSnapshot,
    child: BrainSnapshot,
    manual_entry: ManualEntry,
    tick: int,
) -> BrainSnapshot:
    """Transfer an active hypothesis from an adult/elder parent to a living child as a Lesson.

    Uses the teacher's top skill estimate (by sum of values and sample count) or a zero
    estimate placeholder when the parent has no grounded empirical knowledge.
    """
    if parent.birth.agent_id not in child.birth.parents:
        raise ValueError("Teacher must be a recorded parent")
    if parent.pending is not None or child.pending is not None:
        raise ValueError("Settle pending actions before teaching")
    if stage_at(parent, tick) not in (LifeStage.ADULT, LifeStage.ELDER):
        raise ValueError("Teacher must be alive and mature")
    if stage_at(child, tick) == LifeStage.DEAD:
        raise ValueError("Learner must be alive")
    if manual_entry.status == ManualEntryStatus.FALSIFIED:
        raise ValueError("Cannot teach a falsified manual entry")

    if parent.knowledge:
        estimate = max(parent.knowledge, key=lambda item: (sum(item.values), item.samples))
    else:
        estimate = SkillEstimate(
            context_key="manual",
            skill_key="hypothesis",
            values=ZERO,
            samples=1,
            evidence_id="placeholder:manual",
        )

    lesson = Lesson(
        teacher_id=parent.birth.agent_id,
        learner_id=child.birth.agent_id,
        taught_at=tick,
        estimate=estimate,
        manual_entry=manual_entry,
    )

    # One latest advice item per parent and manual entry; repeated teaching cannot stack authority.
    lessons = tuple(item for item in child.lessons if not (
        item.teacher_id == lesson.teacher_id
        and item.manual_entry is not None
        and item.manual_entry.text == manual_entry.text
    ))
    return updated(
        child, tick=tick, lessons=(lessons + (lesson,))[-child.config.lesson_limit:],
    )
