import pytest

from evolzen.agents.development import advance, born, decide, observe, teach
from evolzen.schemas.development import ZERO, BrainSnapshot, Candidate, DevelopmentConfig, Outcome


def experienced_parent() -> BrainSnapshot:
    parent = advance(born("p", 1), 300)
    waiting = decide(parent, ZERO, (
        Candidate(action_id="gather", context_key="forest", skill_key="gather"),
    ), 300)
    return observe(waiting, Outcome(
        agent_id="p", sequence=1, tick=301, action_id="gather",
        evidence_id="parent-outcome", rewards=(1.0,) * 8, verified=True,
    ))


def test_living_parent_teaches_advice_not_mastery() -> None:
    parent = experienced_parent()
    child = born("c", 2, 301, parents=(parent,))
    taught = teach(parent, child, "forest", "gather", 302)
    assert taught.knowledge == () and taught.recent == ()
    assert len(taught.lessons) == 1
    assert parent.knowledge[0].samples == 1
    assert child.lessons == ()
    taught_twice = teach(parent, taught, "forest", "gather", 303)
    assert len(taught_twice.lessons) == 1


def test_advice_can_change_choice_but_own_evidence_supersedes_it() -> None:
    parent = experienced_parent()
    child = born("c", 2, 301, parents=(parent,))
    rest = Candidate(action_id="a-rest", context_key="forest", skill_key="rest")
    gather = Candidate(action_id="gather", context_key="forest", skill_key="gather")
    cold = decide(child, ZERO, (rest, gather), 302)
    assert cold.pending is not None and cold.pending.candidate == rest
    taught = teach(parent, child, "forest", "gather", 302)
    waiting = decide(taught, ZERO, (rest, gather), 302)
    assert waiting.pending is not None and waiting.pending.candidate == gather
    learned = observe(waiting, Outcome(
        agent_id="c", sequence=1, tick=303, action_id="gather",
        evidence_id="child-outcome", rewards=(-1.0,) * 8, verified=True,
    ))
    retry = decide(learned, ZERO, (rest, gather), 304)
    assert retry.pending is not None and retry.pending.candidate == rest


def test_dead_parent_cannot_teach_and_unrelated_agent_is_rejected() -> None:
    parent = experienced_parent()
    child = born("c", 2, 301, parents=(parent,))
    with pytest.raises(ValueError):
        teach(parent, child, "forest", "gather", 1500)
    with pytest.raises(ValueError):
        teach(parent, born("unrelated", 3, 301), "forest", "gather", 302)


def test_feedback_validation_and_bounded_memory() -> None:
    state = born("c", 1, config=DevelopmentConfig(memory_limit=1, knowledge_limit=1))
    for index in range(2):
        candidate = Candidate(action_id=str(index), context_key="x", skill_key=str(index))
        waiting = decide(state, ZERO, (candidate,), index * 2)
        receipt = Outcome(
            agent_id="c", sequence=index + 1, tick=index * 2 + 1,
            action_id=str(index), evidence_id=str(index), rewards=(0.5,) * 8,
        )
        with pytest.raises(ValueError):
            observe(waiting, receipt)
        data = receipt.model_dump()
        data["verified"] = True
        state = observe(waiting, Outcome.model_validate(data))
    assert len(state.recent) == len(state.knowledge) == 1
    assert state.sequence == 2


def test_receipt_identity_must_match_pending_action() -> None:
    candidate = Candidate(action_id="rest", context_key="x", skill_key="rest")
    waiting = decide(born("c", 1), ZERO, (candidate,), 0)
    with pytest.raises(ValueError):
        observe(waiting, Outcome(
            agent_id="other", sequence=1, tick=1, action_id="rest",
            evidence_id="x", rewards=ZERO, verified=True,
        ))
