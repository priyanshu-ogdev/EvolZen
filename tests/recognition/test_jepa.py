import numpy as np
import pytest

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.recognition.jepa import (
    FEATURE_DIM,
    GroundedJEPAEncoder,
    extract_state_features,
)
from evolzen.schemas.transition import State


def test_extract_state_features_empty_and_minimal() -> None:
    empty_state = State(data={})
    f = extract_state_features(empty_state)
    assert len(f) == FEATURE_DIM
    assert np.all(f == 0.0)

    test_state = State(data={"i": 10, "tick": 50, "step_index": 20})
    f2 = extract_state_features(test_state)
    assert f2[0] == pytest.approx(50 / 2000.0)
    assert f2[1] == pytest.approx(20 / 2000.0)
    assert f2[2] == pytest.approx(10 / 100.0)


def test_extract_state_features_from_engine_world() -> None:
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=100)
    state = engine.reset(seed=42)

    features = extract_state_features(state)
    assert len(features) == FEATURE_DIM
    assert 0.0 <= features[2] <= 1.0  # agent count
    assert 0.0 <= features[4] <= 1.0  # mean energy
    assert 0.0 <= features[5] <= 1.0  # mean fatigue


def test_grounded_jepa_encode_and_similarity() -> None:
    encoder = GroundedJEPAEncoder(embedding_dim=16, seed=123)

    s1 = State(data={"tick": 10, "step_index": 5, "i": 2})
    s2 = State(data={"tick": 10, "step_index": 5, "i": 2})
    s3 = State(data={"tick": 1000, "step_index": 500, "i": 90})

    z1 = encoder.encode(s1)
    z2 = encoder.encode(s2)
    z3 = encoder.encode(s3)

    assert len(z1) == 16
    assert len(z2) == 16
    assert len(z3) == 16
    assert pytest.approx(float(np.linalg.norm(z1)), abs=1e-5) == 1.0

    # Identical states have similarity ~ 1.0
    sim_identical = encoder.similarity(s1, s2)
    assert pytest.approx(sim_identical, abs=1e-4) == 1.0

    # Distinct states have lower similarity
    sim_distinct = encoder.similarity(s1, s3)
    assert sim_distinct < 0.99


def test_grounded_jepa_train_step() -> None:
    encoder = GroundedJEPAEncoder(embedding_dim=16, learning_rate=0.05, seed=42)

    batch = [
        State(data={"tick": i * 10, "step_index": i * 5, "i": i})
        for i in range(1, 6)
    ]

    metrics = encoder.train_step(batch)
    assert metrics["sample_count"] == 5.0
    assert metrics["loss"] >= 0.0
    assert metrics["invariance_loss"] >= 0.0
    assert metrics["variance_loss"] >= 0.0
    assert encoder.step_count == 1

    # Empty batch handling
    empty_res = encoder.train_step([])
    assert empty_res["loss"] == 0.0
