import pytest

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.predictor.dynamics import (
    REWARD_DIMENSIONS,
    ActionDynamicsStats,
    WorldDynamicsPredictor,
)
from evolzen.schemas.transition import Action, Emission, State, Transition


def _make_transition(
    action_type: str,
    rewards: list[float],
    accepted: bool = True,
    energy_delta: float = 0.0,
    fatigue_delta: float = 0.0,
    currency_delta: float = 0.0,
    tick: int = 1,
    step_index: int = 1,
) -> Transition:
    s_data = {
        "tick": tick,
        "step_index": step_index,
        "agents": {
            "agent_0": {
                "agent_id": "agent_0",
                "energy": 0.5,
                "fatigue": 0.5,
                "currency": 10.0,
                "health": 1.0,
            }
        },
    }
    ns_data = {
        "tick": tick + 1,
        "step_index": step_index + 1,
        "agents": {
            "agent_0": {
                "agent_id": "agent_0",
                "energy": max(0.0, min(1.0, 0.5 + energy_delta)),
                "fatigue": max(0.0, min(1.0, 0.5 + fatigue_delta)),
                "currency": max(0.0, 10.0 + currency_delta),
                "health": 1.0,
            }
        },
    }
    return Transition(
        state=State(data=s_data),
        action=Action(agent_id="agent_0", action_type=action_type),
        emission=Emission(
            data={
                "accepted": accepted,
                "reason": "ok" if accepted else "rejected",
                "rewards": rewards,
            }
        ),
        next_state=State(data=ns_data),
    )


def test_action_dynamics_stats_initialization() -> None:
    stats = ActionDynamicsStats(action_type="wait")
    assert stats.action_type == "wait"
    assert stats.total_count == 0
    assert stats.acceptance_rate == 1.0
    assert stats.dominant_reason == "accepted"
    assert stats.mean_rewards == [0.0] * 8
    assert stats.mean_agent_deltas == {"energy": 0.0, "fatigue": 0.0, "currency": 0.0, "health": 0.0}


def test_world_dynamics_predictor_train_and_predict() -> None:
    predictor = WorldDynamicsPredictor()
    rewards_wait = [0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]
    t1 = _make_transition("wait", rewards_wait, accepted=True, energy_delta=0.1, fatigue_delta=-0.2)
    t2 = _make_transition("wait", rewards_wait, accepted=True, energy_delta=0.1, fatigue_delta=-0.2)

    res = predictor.train_batch([t1, t2])
    assert res["loss"] >= 0.0
    assert res["batch_size"] == 2.0
    assert predictor.total_transitions_seen == 2

    # Predict
    test_state = State(
        data={
            "tick": 10,
            "step_index": 5,
            "agents": {
                "agent_0": {
                    "agent_id": "agent_0",
                    "energy": 0.5,
                    "fatigue": 0.5,
                    "currency": 10.0,
                    "health": 1.0,
                }
            },
        }
    )
    pred_emission, pred_next_state = predictor.predict(
        state=test_state,
        action=Action(agent_id="agent_0", action_type="wait"),
        seed=42,
    )

    assert pred_emission.data["accepted"] is True
    assert pred_emission.data["action_type"] == "wait"
    assert pred_emission.data["rewards"] == rewards_wait
    assert pred_emission.data["tick"] == 11
    assert pred_emission.data["step_index"] == 6

    # Verify agent state deltas applied
    agent_data = pred_next_state.data["agents"]["agent_0"]
    assert pytest.approx(agent_data["energy"], abs=1e-5) == 0.6
    assert pytest.approx(agent_data["fatigue"], abs=1e-5) == 0.3


def test_world_dynamics_clamping() -> None:
    predictor = WorldDynamicsPredictor()
    t = _make_transition("exhaust", [0.0] * 8, accepted=True, energy_delta=-1.0, fatigue_delta=1.0)
    predictor.train_batch([t])

    state = State(
        data={
            "tick": 1,
            "step_index": 1,
            "agents": {
                "agent_0": {
                    "agent_id": "agent_0",
                    "energy": 0.1,
                    "fatigue": 0.9,
                    "currency": 0.0,
                    "health": 1.0,
                }
            },
        }
    )
    _, next_state = predictor.predict(state, Action(agent_id="agent_0", action_type="exhaust"))
    agent_data = next_state.data["agents"]["agent_0"]
    assert agent_data["energy"] == 0.0
    assert agent_data["fatigue"] == 1.0


def test_world_dynamics_evaluation_metrics() -> None:
    predictor = WorldDynamicsPredictor()
    rewards_gather = [0.0, -0.1, 0.0, 0.3, 0.0, 0.0, 0.0, 0.1]
    transitions = [
        _make_transition("gather", rewards_gather, accepted=True, energy_delta=-0.1, fatigue_delta=0.1)
        for _ in range(5)
    ]
    predictor.fit(transitions)

    eval_results = predictor.evaluate(transitions)
    assert eval_results["sample_count"] == 5.0
    assert eval_results["acceptance_accuracy"] == 1.0
    assert pytest.approx(eval_results["reward_mae"], abs=1e-5) == 0.0
    assert pytest.approx(eval_results["agent_state_mae"], abs=1e-5) == 0.0
    for dim in REWARD_DIMENSIONS:
        assert f"reward_mae_{dim}" in eval_results


def test_world_dynamics_with_real_social_sandbox_engine() -> None:
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
    state = engine.reset(seed=123)

    recorded_transitions: list[Transition] = []
    current_state = state
    for i in range(6):
        action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
        transition = engine.step(current_state, action)
        recorded_transitions.append(transition)
        current_state = transition.next_state

    predictor = WorldDynamicsPredictor()
    train_data = recorded_transitions[:4]
    test_data = recorded_transitions[4:]

    predictor.fit(train_data)
    assert predictor.total_transitions_seen == 4

    metrics = predictor.evaluate(test_data)
    assert metrics["sample_count"] == 2.0
    assert 0.0 <= metrics["acceptance_accuracy"] <= 1.0
    assert metrics["reward_mae"] >= 0.0
