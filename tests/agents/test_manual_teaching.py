"""Unit tests for intergenerational manual teaching (Phase 1.3 / Phase 1.2).

Verifies cultural transmission of falsifiable manual entries via:
- teach(parent, child, context_key, skill_key, tick, manual_entry=...)
- teach_manual(parent, child, manual_entry, tick)
- Agent.teach(..., manual_entry=...) and Agent.teach_manual(...)
Validates invariants: recorded parent check, parent maturity check, living child check,
active hypothesis check (no falsified entries), pending actions, and non-stacking constraints.
"""
from __future__ import annotations

import pytest

from evolzen.agents.agent import Agent
from evolzen.agents.development import advance, born, decide, observe, stage_at, teach, teach_manual
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import (
    ZERO,
    BrainSnapshot,
    Candidate,
    DevelopmentConfig,
    LifeStage,
    Outcome,
)
from evolzen.schemas.manual import ManualEntry, ManualEntryStatus
from evolzen.schemas.provenance import ProvenanceCategory, ProvenanceRecord


def make_mature_parent_with_knowledge(agent_id: str = "parent-1", seed: int = 42) -> BrainSnapshot:
    """Create an adult parent with grounded experience for 'forest'/'gather'."""
    cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=1500)
    parent = advance(born(agent_id, seed, tick=0, config=cfg), 300)
    waiting = decide(
        parent,
        ZERO,
        (Candidate(action_id="gather", context_key="forest", skill_key="gather"),),
        300,
    )
    return observe(
        waiting,
        Outcome(
            agent_id=agent_id,
            sequence=1,
            tick=301,
            action_id="gather",
            evidence_id="parent-ev-1",
            rewards=(0.8,) * 8,
            verified=True,
        ),
    )


def make_child(parent: BrainSnapshot, child_id: str = "child-1", seed: int = 101, tick: int = 302) -> BrainSnapshot:
    """Create a newborn child of `parent`."""
    return born(child_id, seed, tick=tick, config=parent.config, parents=(parent,))


def make_manual_entry(
    text: str = "Boiling river water prevents stomach distress",
    status: ManualEntryStatus = ManualEntryStatus.HYPOTHESIS,
    author: str = "parent-1",
) -> ManualEntry:
    """Create a valid ManualEntry with optional provenance."""
    prov = ProvenanceRecord(
        provenance_id="prov-1",
        category=ProvenanceCategory.SIMULATOR_TRACE,
        uri_or_source="sim://env-1/run-42",
        description="Simulator observation trace",
        created_tick=300,
        sampling_weight=1.0,
    ).with_computed_digest()
    return ManualEntry(
        text=text,
        status=status,
        written_by=author,
        evidence_ids=("ev-manual-1",),
        provenance=prov,
    )


def test_teach_with_manual_entry_attaches_entry() -> None:
    parent = make_mature_parent_with_knowledge()
    child = make_child(parent, tick=302)

    entry = make_manual_entry("Berries with bitter rind are poisonous")
    taught = teach(parent, child, "forest", "gather", 302, manual_entry=entry)

    assert len(taught.lessons) == 1
    lesson = taught.lessons[0]
    assert lesson.teacher_id == parent.birth.agent_id
    assert lesson.learner_id == child.birth.agent_id
    assert lesson.taught_at == 302
    assert lesson.estimate.context_key == "forest"
    assert lesson.estimate.skill_key == "gather"
    assert lesson.manual_entry is not None
    assert lesson.manual_entry.text == "Berries with bitter rind are poisonous"
    assert lesson.manual_entry.status == ManualEntryStatus.HYPOTHESIS
    assert taught.knowledge == ()
    assert taught.recent == ()


def test_teach_manual_with_parent_knowledge_uses_top_skill() -> None:
    parent = make_mature_parent_with_knowledge()
    # Add a second skill with higher rewards to test top selection
    waiting = decide(
        parent,
        ZERO,
        (Candidate(action_id="hunt", context_key="forest", skill_key="hunt"),),
        302,
    )
    parent = observe(
        waiting,
        Outcome(
            agent_id=parent.birth.agent_id,
            sequence=2,
            tick=303,
            action_id="hunt",
            evidence_id="parent-ev-2",
            rewards=(1.0,) * 8,
            verified=True,
        ),
    )
    assert len(parent.knowledge) == 2

    child = make_child(parent, tick=304)
    entry = make_manual_entry("Heavy stones sharpen spear tips reliably")

    taught = teach_manual(parent, child, entry, tick=304)
    assert len(taught.lessons) == 1
    lesson = taught.lessons[0]
    assert lesson.teacher_id == parent.birth.agent_id
    assert lesson.learner_id == child.birth.agent_id
    assert lesson.taught_at == 304
    # Should use the higher reward estimate ("hunt", rewards=(1.0,)*8)
    assert lesson.estimate.skill_key == "hunt"
    assert lesson.manual_entry is not None
    assert lesson.manual_entry.text == entry.text


def test_teach_manual_without_parent_knowledge_uses_zero_placeholder() -> None:
    cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=1500)
    # Adult parent with no empirical knowledge
    parent = advance(born("parent-inexperienced", 42, tick=0, config=cfg), 300)
    assert len(parent.knowledge) == 0

    child = make_child(parent, tick=300)
    entry = make_manual_entry("Fires deter nocturnal predators")

    taught = teach_manual(parent, child, entry, tick=300)
    assert len(taught.lessons) == 1
    lesson = taught.lessons[0]
    assert lesson.estimate.context_key == "manual"
    assert lesson.estimate.skill_key == "hypothesis"
    assert lesson.estimate.values == ZERO
    assert lesson.estimate.samples == 1
    assert lesson.estimate.evidence_id == "placeholder:manual"
    assert lesson.manual_entry is not None
    assert lesson.manual_entry.text == entry.text


def test_parent_maturity_check_enforced() -> None:
    cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=1500)
    entry = make_manual_entry()

    # 1. Child parent (age 50 < adolescence 100)
    child_parent = advance(born("p-child", 1, tick=0, config=cfg), 50)
    assert stage_at(child_parent, 50) == LifeStage.CHILD
    base_c1 = born("c1", 2, tick=50, config=cfg)
    c1 = base_c1.model_copy(
        update={
            "birth": base_c1.birth.model_copy(update={"parents": ("p-child",), "generation": 1})
        }
    )
    with pytest.raises(ValueError, match="Teacher must be alive and mature"):
        teach_manual(child_parent, c1, entry, tick=50)

    # 2. Adolescent parent (age 150; adolescence 100 <= age < adulthood 300)
    adolescent_parent = advance(born("p-adol", 3, tick=0, config=cfg), 150)
    assert stage_at(adolescent_parent, 150) == LifeStage.ADOLESCENT
    base_c2 = born("c2", 4, tick=150, config=cfg)
    c2 = base_c2.model_copy(
        update={
            "birth": base_c2.birth.model_copy(update={"parents": ("p-adol",), "generation": 1})
        }
    )
    with pytest.raises(ValueError, match="Teacher must be alive and mature"):
        teach_manual(adolescent_parent, c2, entry, tick=150)

    # 3. Adult parent succeeds
    adult_parent = advance(born("p-adult", 5, tick=0, config=cfg), 300)
    assert stage_at(adult_parent, 300) == LifeStage.ADULT
    c3 = born("c3", 6, tick=300, config=cfg, parents=(adult_parent,))
    taught_adult = teach_manual(adult_parent, c3, entry, tick=300)
    assert len(taught_adult.lessons) == 1

    # 4. Elder parent succeeds
    elder_parent = advance(born("p-elder", 7, tick=0, config=cfg), 1000)
    assert stage_at(elder_parent, 1000) == LifeStage.ELDER
    c4 = born("c4", 8, tick=1000, config=cfg, parents=(elder_parent,))
    taught_elder = teach_manual(elder_parent, c4, entry, tick=1000)
    assert len(taught_elder.lessons) == 1

    # 5. Dead parent (age 1500 >= lifespan 1500)
    dead_parent = advance(born("p-dead", 9, tick=0, config=cfg), 1500)
    assert stage_at(dead_parent, 1500) == LifeStage.DEAD
    c5_cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=3000)
    living_parent_for_birth = advance(born("p-dead", 9, tick=0, config=cfg), 300)
    c5 = born("c5", 10, tick=300, config=c5_cfg, parents=(living_parent_for_birth,))
    # At tick 1500, c5 is alive (age = 1500 - 300 = 1200 < lifespan 3000) but parent is dead
    with pytest.raises(ValueError, match="Teacher must be alive and mature"):
        teach_manual(dead_parent, c5, entry, tick=1500)


def test_living_child_check_enforced() -> None:
    parent = make_mature_parent_with_knowledge()
    # Child with short lifespan so child dies while parent is still adult
    short_cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=30, lifespan=50)
    child = born("child-short", 101, tick=302, config=short_cfg, parents=(parent,))
    entry = make_manual_entry()

    # At tick 355:
    # Parent age is 355 (Adult: 300 <= age < 1000)
    # Child age is 355 - 302 = 53 >= lifespan 50 -> DEAD
    dead_child = advance(child, 355)
    assert stage_at(dead_child, 355) == LifeStage.DEAD
    assert stage_at(parent, 355) == LifeStage.ADULT

    with pytest.raises(ValueError, match="Learner must be alive"):
        teach_manual(parent, dead_child, entry, tick=355)

    with pytest.raises(ValueError, match="Learner must be alive"):
        teach(parent, dead_child, "forest", "gather", 355, manual_entry=entry)


def test_recorded_parent_check_enforced() -> None:
    cfg = DevelopmentConfig(adolescence=100, adulthood=300, elderhood=1000, lifespan=1500)
    unrelated_adult = advance(born("unrelated", 1, tick=0, config=cfg), 300)
    parent = advance(born("real-parent", 2, tick=0, config=cfg), 300)
    child = born("child", 3, tick=300, config=cfg, parents=(parent,))
    entry = make_manual_entry()

    with pytest.raises(ValueError, match="Teacher must be a recorded parent"):
        teach_manual(unrelated_adult, child, entry, tick=300)

    with pytest.raises(ValueError, match="Teacher must be a recorded parent"):
        teach(unrelated_adult, child, "forest", "gather", 300, manual_entry=entry)


def test_pending_action_check_enforced() -> None:
    parent = make_mature_parent_with_knowledge()
    child = make_child(parent, tick=302)
    entry = make_manual_entry()

    # Pending on parent
    parent_pending = decide(
        parent,
        ZERO,
        (Candidate(action_id="gather", context_key="forest", skill_key="gather"),),
        302,
    )
    with pytest.raises(ValueError, match="Settle pending actions before teaching"):
        teach_manual(parent_pending, child, entry, tick=302)

    # Pending on child
    child_pending = decide(
        child,
        ZERO,
        (Candidate(action_id="rest", context_key="forest", skill_key="rest"),),
        302,
    )
    with pytest.raises(ValueError, match="Settle pending actions before teaching"):
        teach_manual(parent, child_pending, entry, tick=302)


def test_falsified_manual_entry_rejected() -> None:
    parent = make_mature_parent_with_knowledge()
    child = make_child(parent, tick=302)
    falsified_entry = make_manual_entry(
        "Mud cures venomous bites",
        status=ManualEntryStatus.FALSIFIED,
    )

    with pytest.raises(ValueError, match="Cannot teach a falsified manual entry"):
        teach_manual(parent, child, falsified_entry, tick=302)

    with pytest.raises(ValueError, match="Cannot teach a falsified manual entry"):
        teach(parent, child, "forest", "gather", 302, manual_entry=falsified_entry)


def test_non_stacking_lesson_constraints() -> None:
    parent = make_mature_parent_with_knowledge()
    child = make_child(parent, tick=302)

    entry1 = make_manual_entry("Boil water to eliminate impurities")
    entry2 = make_manual_entry("Salt preserves dried fish across seasons")

    # 1. Repeated teaching of identical manual entry does NOT stack lessons
    t1 = teach_manual(parent, child, entry1, tick=302)
    assert len(t1.lessons) == 1

    t2 = teach_manual(parent, t1, entry1, tick=303)
    assert len(t2.lessons) == 1
    assert t2.lessons[0].taught_at == 303

    # 2. Teaching a second distinct manual entry adds a second lesson
    t3 = teach_manual(parent, t2, entry2, tick=304)
    assert len(t3.lessons) == 2
    entries_in_lessons = {
        lesson.manual_entry.text for lesson in t3.lessons if lesson.manual_entry is not None
    }
    assert entries_in_lessons == {entry1.text, entry2.text}

    # 3. Repeated teach with skill advice and manual entry does not stack
    s1 = teach(parent, t3, "forest", "gather", 305, manual_entry=entry1)
    # Entry1 was already present, teach with same entry updates it
    assert len(s1.lessons) == 2

    s2 = teach(parent, s1, "forest", "gather", 306, manual_entry=entry1)
    assert len(s2.lessons) == 2
    assert s2.lessons[-1].taught_at == 306


def test_agent_teach_and_teach_manual_api() -> None:
    cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=50, lifespan=100)
    p_profile = AgentProfile(agent_id="agent-parent", lineage_id="lineage-teach")
    c_profile = AgentProfile(agent_id="agent-child", lineage_id="lineage-teach", parents=("agent-parent",))

    parent_agent = Agent.create(p_profile, seed=1, tick=0, config=cfg)
    parent_agent.advance(20)
    assert parent_agent.stage == LifeStage.ADULT

    # Ground some experience on the parent
    cand = Candidate(action_id="forage", context_key="forest", skill_key="forage", permitted=True)
    parent_agent.decide(ZERO, (cand,), 20)
    parent_agent.observe(
        Outcome(
            agent_id="agent-parent",
            sequence=1,
            tick=20,
            action_id="forage",
            evidence_id="ev-parent-agent",
            rewards=(0.7,) * 8,
            verified=True,
        )
    )

    parent_agent.advance(25)
    child_agent = Agent.create(c_profile, seed=2, tick=25, config=cfg, parents=(parent_agent,))
    assert child_agent.stage == LifeStage.CHILD
    assert len(child_agent.development.lessons) == 0

    entry = make_manual_entry("Smoke keeps wasps away from honeycomb", author="agent-parent")

    # Call parent_agent.teach with manual_entry
    parent_agent.teach(child_agent, "forest", "forage", 25, manual_entry=entry)
    assert len(child_agent.development.lessons) == 1
    assert child_agent.development.lessons[0].manual_entry is not None
    assert child_agent.development.lessons[0].manual_entry.text == entry.text

    # Call parent_agent.teach_manual
    entry2 = make_manual_entry("Dry wood produces less choking smoke", author="agent-parent")
    parent_agent.teach_manual(child_agent, entry2, 26)
    assert len(child_agent.development.lessons) == 2
    assert child_agent.development.lessons[1].manual_entry is not None
    assert child_agent.development.lessons[1].manual_entry.text == entry2.text
