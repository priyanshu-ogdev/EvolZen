import pytest

from evolzen.evaluation.report import EvaluationReport


def test_summary_requires_held_out_score() -> None:
    report = EvaluationReport()
    with pytest.raises(ValueError):
        report.summary()


def test_summary_requires_reused_vs_fresh_gap() -> None:
    report = EvaluationReport(held_out_rhae_score=0.5)
    with pytest.raises(ValueError):
        report.summary()


def test_summary_renders_when_complete() -> None:
    report = EvaluationReport(
        held_out_rhae_score=0.45,
        human_reference_rhae=0.95,
        frontier_model_reference_rhae=0.30,
        reused_vs_fresh_score_gap=0.12,
        containment_verified=True,
    )
    text = report.summary()
    assert "0.450" in text
    assert "Containment verified: True" in text
