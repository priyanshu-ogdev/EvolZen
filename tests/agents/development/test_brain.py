import pytest

from evolzen.agents.development import advance, born, decide, observe
from evolzen.schemas.development import ZERO, BrainSnapshot, Candidate, Outcome


def test_action_feedback_changes_next_choice() -> None:
    a = Candidate(action_id="a", context_key="room", skill_key="a", predicted=(0.5,) * 8)
    b = Candidate(action_id="b", context_key="room", skill_key="b", predicted=(0.1,) * 8)
    initial = born("learner", 10)
    waiting = decide(initial, ZERO, (a, b), 0)
    assert waiting.pending is not None and waiting.pending.candidate == a
    outcome = Outcome(
        agent_id="learner", sequence=1, tick=1, action_id="a",
        evidence_id="transition-1", rewards=(-1.0,) * 8, verified=True,
    )
    learned = observe(waiting, outcome)
    next_step = decide(learned, ZERO, (a, b), 2)
    assert next_step.pending is not None and next_step.pending.candidate == b
    assert initial.knowledge == ()
    assert learned.knowledge[0].samples == 1
    with pytest.raises(ValueError):
        observe(learned, outcome)


def test_permission_and_age_masks_override_preference() -> None:
    forbidden = Candidate(action_id="forbidden", context_key="x", skill_key="x",
                          predicted=(1.0,) * 8, permitted=False)
    adult_only = Candidate(action_id="adult", context_key="x", skill_key="y",
                          predicted=(1.0,) * 8, minimum_age=300)
    rest = Candidate(action_id="rest", context_key="x", skill_key="rest")
    waiting = decide(born("c", 1), ZERO, (forbidden, adult_only, rest), 0)
    assert waiting.pending is not None and waiting.pending.candidate.action_id == "rest"
    with pytest.raises(ValueError):
        decide(born("c", 1), ZERO, (forbidden,), 0)


def test_pending_state_is_serializable_and_expiry_cancels_it() -> None:
    candidate = Candidate(action_id="rest", context_key="x", skill_key="rest")
    waiting = decide(born("c", 1), ZERO, (candidate,), 0)
    restored = BrainSnapshot.model_validate_json(waiting.model_dump_json())
    assert restored == waiting
    with pytest.raises(ValueError):
        decide(restored, ZERO, (candidate,), 1)
    dead = advance(restored, 1500)
    assert dead.pending is None
    with pytest.raises(ValueError):
        decide(dead, ZERO, (candidate,), 1500)


def test_candidate_ids_are_unique_and_ties_are_stable() -> None:
    a = Candidate(action_id="a", context_key="x", skill_key="a")
    b = Candidate(action_id="b", context_key="x", skill_key="b")
    state = born("c", 1)
    assert decide(state, ZERO, (a, b), 0) == decide(state, ZERO, (b, a), 0)
    with pytest.raises(ValueError):
        decide(state, ZERO, (a, a), 0)
