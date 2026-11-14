from evolzen.evaluation.dual_track import (
    DualTrackRunner,
    FreshTrackResult,
    PersistentTrackResult,
)
from evolzen.evaluation.report import EvaluationReport


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
