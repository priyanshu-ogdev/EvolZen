from pathlib import Path

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.library.audit import AuditLog
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.recognition.ablations import (
    AblationCondition,
    AblationResult,
    AblationRunner,
)
from evolzen.schemas.transition import Action, Transition


def test_ablation_conditions_enum() -> None:
    assert AblationCondition.BASELINE.value == "baseline"
    assert AblationCondition.JEPA_ONLY.value == "jepa_only"
    assert AblationCondition.WAKE_SLEEP_ONLY.value == "wake_sleep_only"
    assert AblationCondition.COMBINED.value == "combined"


def test_ablation_runner_empty() -> None:
    runner = AblationRunner(seed=42)
    res = runner.run_condition(AblationCondition.BASELINE, [])
    assert isinstance(res, AblationResult)
    assert res.compute_samples == 0
    assert res.prediction_accuracy == 0.0


def test_ablation_runner_individual_condition() -> None:
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
    state = engine.reset(seed=42)

    transitions: list[Transition] = []
    current_state = state
    for i in range(10):
        action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
        t = engine.step(current_state, action)
        transitions.append(t)
        current_state = t.next_state

    runner = AblationRunner(seed=42)
    res = runner.run_condition(AblationCondition.JEPA_ONLY, transitions)

    assert isinstance(res, AblationResult)
    assert res.condition == AblationCondition.JEPA_ONLY
    assert res.compute_samples == 10
    assert 0.0 <= res.prediction_accuracy <= 1.0
    assert res.ci_95_low <= res.ci_95_high
    assert res.adaptation_latency > 0.0
    assert "untested" in res.untested_notice


def test_ablation_runner_full_matrix() -> None:
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
    state = engine.reset(seed=123)

    transitions: list[Transition] = []
    current_state = state
    for i in range(10):
        action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
        t = engine.step(current_state, action)
        transitions.append(t)
        current_state = t.next_state

    runner = AblationRunner(seed=123)
    matrix = runner.run_full_matrix(transitions)

    assert len(matrix) == 4
    for cond in AblationCondition:
        assert cond.value in matrix
        cell = matrix[cond.value]
        assert cell.condition == cond
        assert cell.compute_samples == 10
        assert 0.0 <= cell.prediction_accuracy <= 1.0

    report = runner.format_report(matrix)
    assert "| Condition |" in report
    assert "| baseline |" in report
    assert "| combined |" in report


def test_ablation_runner_with_custom_library(tmp_path: Path) -> None:
    store = LibraryStore(tmp_path / "custom_lib.duckdb")
    audit = AuditLog(tmp_path / "custom_audit.jsonl")
    lib = RuleLibrary(store, audit)

    runner = AblationRunner(library=lib, seed=99)
    res = runner.run_condition(AblationCondition.BASELINE, [])
    assert res.compute_samples == 0
