from pathlib import Path
from uuid import uuid4

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.audit import AuditLog
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.recognition.jepa import GroundedJEPAEncoder
from evolzen.recognition.wake_sleep import FantasyCase, WakeSleepLearner
from evolzen.schemas.library import ValidityContext, VerificationEvidence
from evolzen.schemas.transition import State


def _make_library(tmp_path: Path) -> RuleLibrary:
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    return RuleLibrary(store, audit)


def test_wake_propose_synthesizes_when_library_empty(tmp_path: Path) -> None:
    lib = _make_library(tmp_path)
    learner = WakeSleepLearner(rule_library=lib)

    obs = {"actor_id": "agent_0", "tick": 5}
    candidate = learner.wake_propose(observation=obs, action_type="wait", gap="test_gap")

    assert isinstance(candidate, CandidateRule)
    assert "def predict" in candidate.code
    assert candidate.explains == ["test_gap"]


def test_wake_propose_reuses_existing_rule(tmp_path: Path) -> None:
    lib = _make_library(tmp_path)
    learner = WakeSleepLearner(rule_library=lib)

    # Spawn an active rule in the library with 'wait'
    existing_rule = CandidateRule(
        rule_id="rule_wait_existing",
        code="def predict(state, action, ex_input, seed):\n    return {'accepted': True, 'action_type': 'wait'}",
        explains=["prev_gap"],
    )
    val = ValidityContext(world_version="env-v1", mechanic_keys=("gravity",), seed_range=(0, 99), verified_at_tick=10)
    ev = VerificationEvidence(evidence_id=uuid4(), transition_ids=(uuid4(),), intervention_ids=(), held_out_combination_ids=())
    entry = lib.spawn_if_novel(existing_rule, val, ev)
    assert entry is not None

    candidate = learner.wake_propose(observation={"tick": 1}, action_type="wait", gap="new_gap")
    assert str(entry.rule_id) in candidate.rule_id
    assert "def predict" in candidate.code


def test_sleep_step_compression_and_fantasy_cases(tmp_path: Path) -> None:
    lib = _make_library(tmp_path)
    jepa = GroundedJEPAEncoder(embedding_dim=16, seed=42)
    learner = WakeSleepLearner(rule_library=lib, jepa_encoder=jepa)

    # Spawn two rules with shared header syntax
    val = ValidityContext(world_version="env-v1", mechanic_keys=("gravity",), seed_range=(0, 99), verified_at_tick=10)
    ev = VerificationEvidence(evidence_id=uuid4(), transition_ids=(uuid4(),), intervention_ids=(), held_out_combination_ids=())

    rule1 = CandidateRule(
        rule_id="r1",
        code="def predict(state, action, ex_input, seed):\n    emission = {'accepted': True}\n    return emission",
        explains=["g1"],
    )
    rule2 = CandidateRule(
        rule_id="r2",
        code="def predict(state, action, ex_input, seed):\n    emission = {'accepted': False}\n    return emission",
        explains=["g2"],
    )
    lib.spawn_if_novel(rule1, val, ev)
    lib.spawn_if_novel(rule2, val, ev)

    real_cases = [
        {"tick": 10, "state": State(data={"tick": 10, "step_index": 5})},
        {"tick": 20, "state": State(data={"tick": 20, "step_index": 10})},
    ]
    fantasy_cases = [
        FantasyCase(synthetic_context={"tick": 100}, target_rule_id="r1"),
    ]

    metrics = learner.sleep_step(real_cases=real_cases, fantasy_cases=fantasy_cases)
    assert metrics["sleep_cycles"] == 1.0
    assert metrics["reconstructed_cases"] == 3.0
    assert metrics["compression_ratio"] > 0.0
    assert "primitives_abstracted" in metrics
    assert "jepa_loss" in metrics
