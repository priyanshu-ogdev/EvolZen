import pytest

from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.schemas.transition import Action, Emission, State, Transition


def _dummy_transition(i: int) -> Transition:
    return Transition(
        state=State(data={"i": i}),
        action=Action(agent_id="a", action_type="noop"),
        emission=Emission(data={}),
        next_state=State(data={"i": i + 1}),
    )


def test_buffer_respects_capacity() -> None:
    buf = RehearsalBuffer(capacity=3)
    for i in range(5):
        buf.add(_dummy_transition(i))
    assert len(buf) == 3


def test_sample_raises_when_batch_too_large() -> None:
    buf = RehearsalBuffer(capacity=5)
    buf.add(_dummy_transition(0))
    with pytest.raises(ValueError):
        buf.sample(batch_size=2)
