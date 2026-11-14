import random
from pathlib import Path

import pytest

from evolzen.predictor.rehearsal_buffer import ContinualMetricsTracker, RehearsalBuffer
from evolzen.schemas.transition import Action, Emission, State, Transition
from evolzen.storage.transition_log import TransitionLogStore


def _dummy_transition(i: int) -> Transition:
    return Transition(
        state=State(data={"i": i, "tick": i}),
        action=Action(agent_id=f"agent_{i % 2}", action_type="wait" if i % 2 == 0 else "gather"),
        emission=Emission(data={"accepted": True, "rewards": [0.1 * i] * 8}),
        next_state=State(data={"i": i + 1, "tick": i + 1}),
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


def test_extend_and_clear() -> None:
    buf = RehearsalBuffer(capacity=10)
    transitions = [_dummy_transition(i) for i in range(5)]
    buf.extend(transitions)
    assert len(buf) == 5

    buf.clear()
    assert len(buf) == 0


def test_sample_clear_batch() -> None:
    buf = RehearsalBuffer(capacity=20)
    old_transitions = [_dummy_transition(i) for i in range(10)]
    buf.extend(old_transitions)

    new_transitions = [_dummy_transition(100 + i) for i in range(10)]

    rng = random.Random(42)
    # 50% replay ratio: 4 replay, 4 new
    batch = buf.sample_clear_batch(new_transitions, total_batch_size=8, replay_ratio=0.5, rng=rng)
    assert len(batch) == 8

    # Edge cases
    empty_buf = RehearsalBuffer(capacity=10)
    empty_batch = empty_buf.sample_clear_batch([], total_batch_size=5)
    assert empty_batch == []

    # All new if buffer empty
    new_only = empty_buf.sample_clear_batch(new_transitions, total_batch_size=4, replay_ratio=0.5)
    assert len(new_only) == 4

    # All replay if new transitions empty
    replay_only = buf.sample_clear_batch([], total_batch_size=4, replay_ratio=0.5)
    assert len(replay_only) == 4


def test_load_from_store(tmp_path: Path) -> None:
    db_path = tmp_path / "test_transitions.duckdb"
    store = TransitionLogStore(db_path)

    for i in range(8):
        store.append(_dummy_transition(i))

    assert store.count() == 8

    buf = RehearsalBuffer(capacity=10)
    loaded = buf.load_from_store(store, max_records=5)
    assert loaded == 5
    assert len(buf) == 5

    store.close()


def test_continual_metrics_tracker() -> None:
    tracker = ContinualMetricsTracker()

    # Baselines for tasks 1, 2, 3
    tracker.set_baseline(1, 0.2)
    tracker.set_baseline(2, 0.3)
    tracker.set_baseline(3, 0.25)

    # After training on Task 1:
    tracker.record_eval(train_task=1, eval_task=1, score=0.85)
    tracker.record_eval(train_task=1, eval_task=2, score=0.40)  # Forward transfer indicator to task 2

    # After training on Task 2:
    tracker.record_eval(train_task=2, eval_task=1, score=0.80)  # Dropped from 0.85 -> 0.80 (forgetting 0.05)
    tracker.record_eval(train_task=2, eval_task=2, score=0.90)
    tracker.record_eval(train_task=2, eval_task=3, score=0.35)  # Forward transfer indicator to task 3

    # After training on Task 3:
    tracker.record_eval(train_task=3, eval_task=1, score=0.78)  # Backward transfer: 0.78 - 0.85 = -0.07
    tracker.record_eval(train_task=3, eval_task=2, score=0.88)  # Backward transfer: 0.88 - 0.90 = -0.02
    tracker.record_eval(train_task=3, eval_task=3, score=0.92)

    # Backward transfer for Task 3: avg((-0.07) + (-0.02)) = -0.045
    bwt = tracker.backward_transfer()
    assert pytest.approx(bwt, abs=1e-4) == -0.045

    # Forward transfer:
    # Task 2: R[1, 2] - b_2 = 0.40 - 0.30 = 0.10
    # Task 3: R[2, 3] - b_3 = 0.35 - 0.25 = 0.10
    # Average FWT = 0.10
    fwt = tracker.forward_transfer()
    assert pytest.approx(fwt, abs=1e-4) == 0.10

    # Forgetting:
    # Task 1: max(0.85, 0.80) - 0.78 = 0.07
    # Task 2: max(0.90) - 0.88 = 0.02
    assert pytest.approx(tracker.forgetting(1), abs=1e-4) == 0.07
    assert pytest.approx(tracker.forgetting(2), abs=1e-4) == 0.02
    assert pytest.approx(tracker.average_forgetting(), abs=1e-4) == 0.045

    summary = tracker.summary()
    assert summary["num_tasks"] == 3
    assert "backward_transfer" in summary
    assert "forward_transfer" in summary
    assert "average_forgetting" in summary
