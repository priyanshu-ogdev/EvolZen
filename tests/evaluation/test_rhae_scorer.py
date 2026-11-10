import pytest

from evolzen.evaluation.rhae_scorer import RHAEResult, RHAEScorer


def test_rhae_score_matches_human_reference() -> None:
    r = RHAEResult(system_actions=10, human_reference_actions=10, solved=True)
    assert r.score == 1.0


def test_rhae_score_zero_when_unsolved() -> None:
    r = RHAEResult(system_actions=10, human_reference_actions=10, solved=False)
    assert r.score == 0.0


def test_scorer_aggregates_mean_and_solve_rate() -> None:
    scorer = RHAEScorer()
    scorer.record(RHAEResult(system_actions=10, human_reference_actions=10, solved=True))
    scorer.record(RHAEResult(system_actions=20, human_reference_actions=10, solved=True))
    scorer.record(RHAEResult(system_actions=5, human_reference_actions=10, solved=False))
    assert scorer.solve_rate() == pytest.approx(2 / 3)
    assert scorer.mean_rhae() == pytest.approx((1.0 + 0.5 + 0.0) / 3)
