from evolzen.evaluation.dual_track import (
    DualTrackRunner,
    FreshTrackResult,
    PersistentTrackResult,
)
from evolzen.evaluation.report import EvaluationReport
from evolzen.predictor.dynamics import WorldDynamicsPredictor
from evolzen.predictor.planner import Planner
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.schemas.transition import Action, Emission, State, Transition


def _sample_transition(action_type: str, rewards: list[float]) -> Transition:
    s = State(data={"tick": 1, "step_index": 1, "agents": {"agent_0": {"energy": 0.5, "fatigue": 0.5, "currency": 10.0}}})
    ns = State(data={"tick": 2, "step_index": 2, "agents": {"agent_0": {"energy": 0.5, "fatigue": 0.4, "currency": 10.0}}})
    return Transition(
        state=s,
        action=Action(agent_id="agent_0", action_type=action_type),
        emission=Emission(data={"accepted": True, "reason": "ok", "rewards": rewards}),
        next_state=ns,
    )


def test_dual_track_runner_persistent_track() -> None:
    runner = DualTrackRunner(seed=42)
    p_res = runner.run_persistent_track(ticks=10)

    assert isinstance(p_res, PersistentTrackResult)
    assert p_res.total_ticks > 0
    assert 0.0 <= p_res.living_agents_ratio <= 1.0
    assert p_res.invariants_passed is True
    assert 0.0 <= p_res.gini_coefficient <= 1.0
    assert p_res.capabilities_count >= 1


def test_dual_track_runner_fresh_track() -> None:
    runner = DualTrackRunner(seed=123)
    f_res = runner.run_fresh_track(rounds=3)

    assert isinstance(f_res, FreshTrackResult)
    assert f_res.rounds_evaluated == 3
    assert f_res.mean_eae_score >= 0.0
    assert 0.0 <= f_res.solve_rate <= 1.0
    assert f_res.reused_vs_fresh_score_gap >= 0.0


def test_dual_track_full_evaluation_report() -> None:
    runner = DualTrackRunner(seed=42)
    report = runner.run_full_evaluation(persistent_ticks=10, fresh_rounds=3)

    assert isinstance(report, EvaluationReport)
    assert report.containment_verified is True
    assert report.held_out_rhae_score is not None
    assert report.reused_vs_fresh_score_gap is not None
    assert report.human_reference_rhae == 1.0
    assert len(report.negative_findings) >= 2

    # Verify summary renders without ValueError
    summary = report.summary()
    assert "Held-out RHAE score:" in summary
    assert "Reused-vs-fresh score gap:" in summary
    assert "Negative findings:" in summary


def test_dual_track_runner_fresh_track_with_planner() -> None:
    runner = DualTrackRunner(seed=42)
    buf = RehearsalBuffer(capacity=10)
    dyn = WorldDynamicsPredictor()
    planner = Planner(rehearsal_buffer=buf, dynamics=dyn)

    t1 = _sample_transition("gather", [0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    t2 = _sample_transition("wait", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.3])
    planner.train_step([t1, t2])

    f_res = runner.run_fresh_track(rounds=2, planner=planner, planning_horizon=3)
    assert isinstance(f_res, FreshTrackResult)
    assert f_res.planner_enabled is True
    assert f_res.planning_horizon == 3
    assert f_res.baseline_eae_score is not None
    assert f_res.baseline_solve_rate is not None
    assert f_res.mean_eae_score >= 0.0
    assert 0.0 <= f_res.solve_rate <= 1.0


def test_dual_track_full_evaluation_with_planner() -> None:
    runner = DualTrackRunner(seed=42)
    buf = RehearsalBuffer(capacity=10)
    dyn = WorldDynamicsPredictor()
    planner = Planner(rehearsal_buffer=buf, dynamics=dyn)

    t1 = _sample_transition("gather", [0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    planner.train_step([t1])

    report = runner.run_full_evaluation(persistent_ticks=5, fresh_rounds=2, planner=planner, planning_horizon=2)
    assert isinstance(report, EvaluationReport)
    assert report.fresh_result.planner_enabled is True
    assert report.fresh_result.planning_horizon == 2
    assert len(report.negative_findings) >= 3
    summary = report.summary()
    assert "Model-based planning (horizon=2)" in summary


def test_dual_track_runner_fresh_track_multi_tier() -> None:
    runner = DualTrackRunner(seed=42)
    buf = RehearsalBuffer(capacity=50)
    dyn = WorldDynamicsPredictor()
    planner = Planner(rehearsal_buffer=buf, dynamics=dyn)

    t_wood = _sample_transition("gather", [0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05])
    t_stone = _sample_transition("gather", [0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05])
    t_craft = _sample_transition("craft", [0.3, 0.15, 0.0, 0.0, 0.0, 0.0, -0.08, -0.05])
    t_wait = _sample_transition("wait", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.1])
    planner.train_step([t_wood, t_stone, t_craft, t_wait])

    f_res = runner.run_fresh_track(
        rounds=2,
        planner=planner,
        planning_horizon=5,
        task_tier="multi_tier",
    )
    assert isinstance(f_res, FreshTrackResult)
    assert f_res.planner_enabled is True
    assert f_res.planning_horizon == 5
    assert f_res.task_tier == "multi_tier"
    assert f_res.solve_rate == 1.0
    assert f_res.baseline_solve_rate == 0.0
    assert f_res.mean_eae_score > 0.0
    assert f_res.baseline_eae_score == 0.0


def test_dual_track_full_evaluation_multi_tier() -> None:
    runner = DualTrackRunner(seed=42)
    buf = RehearsalBuffer(capacity=50)
    dyn = WorldDynamicsPredictor()
    planner = Planner(rehearsal_buffer=buf, dynamics=dyn)

    t_wood = _sample_transition("gather", [0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05])
    t_stone = _sample_transition("gather", [0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05])
    t_craft = _sample_transition("craft", [0.3, 0.15, 0.0, 0.0, 0.0, 0.0, -0.08, -0.05])
    planner.train_step([t_wood, t_stone, t_craft])

    report = runner.run_full_evaluation(
        persistent_ticks=5,
        fresh_rounds=2,
        planner=planner,
        planning_horizon=5,
        task_tier="multi_tier",
    )
    assert isinstance(report, EvaluationReport)
    assert report.fresh_result.task_tier == "multi_tier"
    assert report.fresh_result.planning_horizon == 5
    assert report.fresh_result.solve_rate == 1.0
    assert report.fresh_result.baseline_solve_rate == 0.0
    summary = report.summary()
    assert "Model-based planning (horizon=5)" in summary
    assert "tier=multi_tier" in summary
    assert "composite crafting" in summary
    assert "planning hypothesis H4" in summary
    assert report.fresh_result.planning_superiority_summary is not None
    assert "stone_axe" in report.fresh_result.planning_superiority_summary


