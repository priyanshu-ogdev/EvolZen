import pytest

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.predictor.dynamics import WorldDynamicsPredictor
from evolzen.predictor.planner import Planner, PredictionResult
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.schemas.transition import Action, Emission, State, Transition


def _dummy_transition(action_type: str, rewards: list[float], i: int = 1) -> Transition:
    s = State(data={"tick": i, "step_index": i, "agents": {"agent_0": {"energy": 0.5, "fatigue": 0.5, "currency": 10.0}}})
    ns = State(data={"tick": i + 1, "step_index": i + 1, "agents": {"agent_0": {"energy": 0.5, "fatigue": 0.5, "currency": 10.0}}})
    return Transition(
        state=s,
        action=Action(agent_id="agent_0", action_type=action_type),
        emission=Emission(data={"accepted": True, "reason": "ok", "rewards": rewards}),
        next_state=ns,
    )


def test_planner_predict_empty_context() -> None:
    buf = RehearsalBuffer(capacity=10)
    planner = Planner(rehearsal_buffer=buf)
    res = planner.predict([])
    assert isinstance(res, PredictionResult)
    assert res.confidence == 0.1
    assert res.predicted_emission["accepted"] is True


def test_planner_predict_with_context() -> None:
    buf = RehearsalBuffer(capacity=10)
    planner = Planner(rehearsal_buffer=buf)

    t1 = _dummy_transition("wait", [0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], i=1)
    t2 = _dummy_transition("gather", [0.0, -0.1, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0], i=2)
    planner.train_step([t1, t2])

    res = planner.predict([t1, t2])
    assert isinstance(res, PredictionResult)
    assert res.confidence > 0.0
    assert res.action is not None
    assert res.predicted_next_state is not None
    assert "health" in res.reward_decomposition
    assert "resource" in res.reward_decomposition


def test_planner_plan_action_selects_optimal() -> None:
    buf = RehearsalBuffer(capacity=10)
    dynamics = WorldDynamicsPredictor()
    planner = Planner(rehearsal_buffer=buf, dynamics=dynamics)

    # Train dynamics with high reward for 'craft' and low for 'wait'
    craft_t = _dummy_transition("craft", [0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0])
    wait_t = _dummy_transition("wait", [0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    dynamics.train_batch([craft_t] * 5 + [wait_t] * 5)

    state = State(data={"tick": 1, "step_index": 1, "agents": {"agent_0": {"energy": 0.5}}})
    candidates = [
        Action(agent_id="agent_0", action_type="wait"),
        Action(agent_id="agent_0", action_type="craft"),
    ]

    best_action, best_res = planner.plan_action(state, "agent_0", candidates)
    assert best_action.action_type == "craft"
    assert best_res.predicted_emission["action_type"] == "craft"
    assert best_res.reward_decomposition["resource"] == pytest.approx(0.8, abs=1e-5)


def test_planner_train_step_grpo() -> None:
    buf = RehearsalBuffer(capacity=20)
    planner = Planner(rehearsal_buffer=buf, lr=0.1)

    batch = [
        _dummy_transition("gather", [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0], i=1),
        _dummy_transition("wait", [0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], i=2),
        _dummy_transition("craft", [0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0], i=3),
    ]

    metrics = planner.train_step(batch, replay_ratio=0.5)
    assert metrics["update_count"] == 1.0
    assert metrics["sample_count"] == 3.0
    assert "grpo_advantage_mean" in metrics
    assert "policy_entropy" in metrics
    assert len(buf) == 3

    # Policy probabilities should favor higher reward actions (craft, gather)
    probs = planner.policy_probabilities(["wait", "gather", "craft"])
    assert probs["craft"] > probs["wait"]


def test_planner_with_real_engine_rollout() -> None:
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
    state = engine.reset(seed=42)

    transitions: list[Transition] = []
    current_state = state
    for i in range(8):
        action_type = "wait" if i % 2 == 0 else "gather"
        action = Action(agent_id="agent_0", action_type=action_type)
        t = engine.step(current_state, action)
        transitions.append(t)
        current_state = t.next_state

    buf = RehearsalBuffer(capacity=50)
    planner = Planner(rehearsal_buffer=buf)

    train_batch = transitions[:5]
    test_batch = transitions[5:]

    train_metrics = planner.train_step(train_batch, replay_ratio=0.5)
    assert train_metrics["update_count"] == 1.0
    assert train_metrics["loss"] >= 0.0

    pred = planner.predict(test_batch)
    assert pred.confidence > 0.0
    assert pred.predicted_next_state is not None

    # Test continual metrics tracker tracking
    planner.metrics_tracker.set_baseline(1, 0.1)
    planner.metrics_tracker.record_eval(train_task=1, eval_task=1, score=0.8)
    assert planner.metrics_tracker.get_score(1, 1) == 0.8
