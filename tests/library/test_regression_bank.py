"""Tests for evolzen.library.regression_bank — RegressionBank (Phase 1.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from evolzen.library.audit import AuditLog
from evolzen.library.persistence import LibraryStore
from evolzen.library.regression_bank import RegressionBank
from evolzen.library.rule_library import RuleLibrary
from evolzen.schemas.library import (
    ProvenanceClass,
    RuleEntry,
    RuleStatus,
    ValidityContext,
    VerificationEvidence,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=UTC)


def _validity() -> ValidityContext:
    return ValidityContext(
        world_version="env-v1",
        mechanic_keys=("gravity",),
        seed_range=(0, 99),
        verified_at_tick=100,
    )


def _evidence() -> VerificationEvidence:
    return VerificationEvidence(
        evidence_id=uuid4(),
        transition_ids=(uuid4(),),
        intervention_ids=(),
        held_out_combination_ids=(),
        false_promotion_rate=0.0,
        resource_ceiling_hit=False,
    )


def _make_entry(rule_id: UUID | None = None) -> RuleEntry:
    return RuleEntry(
        rule_id=rule_id or uuid4(),
        version=1,
        rule_family_id=uuid4(),
        code="def predict(s, a): return s",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )


def _fixture(tid: UUID | None = None, expected: str = "emission_A") -> dict[str, Any]:
    t = tid or uuid4()
    return {"transition_id": str(t), "expected_emission": expected, "actual_emission": expected}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_register_persists_fixtures(tmp_path: Path) -> None:
    """register stores fixtures; cases_for_rule returns them."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    tid = uuid4()
    bank.register(rule_id, [tid], [_fixture(tid)])
    cases = bank.cases_for_rule(rule_id)
    assert len(cases) == 1
    assert cases[0]["transition_id"] == str(tid)


def test_cases_for_rule_returns_multiple_fixtures(tmp_path: Path) -> None:
    """cases_for_rule returns all registered fixtures in insertion order."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    tids = [uuid4() for _ in range(3)]
    fixtures = [_fixture(t) for t in tids]
    bank.register(rule_id, tids, fixtures)
    cases = bank.cases_for_rule(rule_id)
    assert len(cases) == 3


def test_register_is_append_only_does_not_delete_old_fixtures(tmp_path: Path) -> None:
    """Re-registering for the same rule_id appends; existing fixtures remain."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    t1, t2 = uuid4(), uuid4()
    bank.register(rule_id, [t1], [_fixture(t1)])
    bank.register(rule_id, [t2], [_fixture(t2)])
    cases = bank.cases_for_rule(rule_id)
    assert len(cases) == 2  # both rounds preserved


def test_check_rule_returns_all_passed_true_for_matching_fixtures(tmp_path: Path) -> None:
    """check_rule returns all_passed=True when expected==actual for all fixtures."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    entry = _make_entry(rule_id=rule_id)
    tids = [uuid4() for _ in range(3)]
    fixtures = [_fixture(t, expected="emission_A") for t in tids]
    bank.register(rule_id, tids, fixtures)
    result = bank.check_rule(rule_id, entry)
    assert result.all_passed is True
    assert result.failed_transition_ids == ()


def test_check_rule_returns_all_passed_false_on_mismatch(tmp_path: Path) -> None:
    """check_rule returns all_passed=False when expected != actual for any fixture."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    entry = _make_entry(rule_id=rule_id)
    t1, t2 = uuid4(), uuid4()
    # t1 passes, t2 fails (actual != expected)
    fixtures = [
        {"transition_id": str(t1), "expected_emission": "A", "actual_emission": "A"},
        {"transition_id": str(t2), "expected_emission": "A", "actual_emission": "B"},
    ]
    bank.register(rule_id, [t1, t2], fixtures)
    result = bank.check_rule(rule_id, entry)
    assert result.all_passed is False
    assert len(result.failed_transition_ids) == 1


def test_check_all_active_runs_checks_for_all_active_rules(tmp_path: Path) -> None:
    """check_all_active returns one RegressionResult per active rule with fixtures."""
    from evolzen.exploration.synthesizer import CandidateRule
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit, routing_threshold=0.85)
    bank = RegressionBank(tmp_path / "lib.duckdb")

    e1 = lib.spawn_if_novel(
        CandidateRule(
            rule_id=str(uuid4()),
            code="def gravity_step(state, action): return state.y - 9.81 * state.dt",
            explains=["gravity"],
        ),
        _validity(), _evidence(),
    )
    e2 = lib.spawn_if_novel(
        CandidateRule(
            rule_id=str(uuid4()),
            code="def elastic_collision(state, action): return -state.vx * state.restitution",
            explains=["collision"],
        ),
        _validity(), _evidence(),
    )
    assert e1 is not None and e2 is not None

    for entry in [e1, e2]:
        t = uuid4()
        bank.register(entry.rule_id, [t], [_fixture(t)])

    results = bank.check_all_active(lib)
    assert len(results) == 2


def test_any_regression_returns_true_if_any_failed(tmp_path: Path) -> None:
    """any_regression returns True when at least one result has all_passed=False."""
    from evolzen.schemas.library import RegressionResult
    good = RegressionResult(
        check_id=uuid4(), rule_id=uuid4(), transition_ids_checked=(),
        all_passed=True, failed_transition_ids=(), checked_at=_now(),
    )
    bad = RegressionResult(
        check_id=uuid4(), rule_id=uuid4(), transition_ids_checked=(uuid4(),),
        all_passed=False, failed_transition_ids=(uuid4(),), checked_at=_now(),
    )
    assert RegressionBank.any_regression([good, bad]) is True


def test_any_regression_returns_false_when_all_passed(tmp_path: Path) -> None:
    """any_regression returns False when all results have all_passed=True."""
    from evolzen.schemas.library import RegressionResult
    results = [
        RegressionResult(
            check_id=uuid4(), rule_id=uuid4(), transition_ids_checked=(),
            all_passed=True, failed_transition_ids=(), checked_at=_now(),
        )
        for _ in range(3)
    ]
    assert RegressionBank.any_regression(results) is False


def test_load_results_returns_stored_results(tmp_path: Path) -> None:
    """load_results returns all stored RegressionResult rows for a rule_id."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()
    entry = _make_entry(rule_id=rule_id)
    t = uuid4()
    bank.register(rule_id, [t], [_fixture(t)])
    bank.check_rule(rule_id, entry)
    results = bank.load_results(rule_id)
    assert len(results) == 1
    assert results[0].rule_id == rule_id


def test_cases_for_rule_returns_empty_for_unknown_rule(tmp_path: Path) -> None:
    """cases_for_rule returns [] for a rule_id that was never registered."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    assert bank.cases_for_rule(uuid4()) == []


def test_check_rule_does_not_use_eval_on_code(tmp_path: Path) -> None:
    """check_rule must not call eval/exec on entry.code (security contract)."""
    import inspect

    from evolzen.library import regression_bank as rb_module
    # Read the source of check_rule and verify no eval/exec calls on entry.code
    source = inspect.getsource(rb_module.RegressionBank.check_rule)
    # It's acceptable to reference the word 'eval' in comments/docstrings,
    # but it must not appear as a function call on 'code' or 'entry'
    assert "eval(entry" not in source
    assert "exec(entry" not in source


def test_register_raises_on_length_mismatch(tmp_path: Path) -> None:
    """register raises ValueError when transition_ids and fixtures lengths differ."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    with pytest.raises(ValueError, match="same length"):
        bank.register(uuid4(), [uuid4(), uuid4()], [_fixture()])


def test_check_rule_records_audit_event_when_audit_log_provided(tmp_path: Path) -> None:
    """check_rule writes REGRESSION_CHECK when audit_log is passed."""
    from evolzen.schemas.library import AuditEventType

    bank = RegressionBank(tmp_path / "bank.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    rule_id = uuid4()
    entry = _make_entry(rule_id=rule_id)
    tid = uuid4()
    bank.register(rule_id, [tid], [_fixture(tid)])
    bank.check_rule(rule_id, entry, audit_log=audit)
    events = audit.load_for_rule(rule_id)
    assert len(events) == 1
    assert events[0].event_type is AuditEventType.REGRESSION_CHECK

