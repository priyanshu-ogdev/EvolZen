"""Tests for evolzen.library.persistence — LibraryStore (Phase 1.5).

Verifies the append-only DuckDB store: writes, reads, status updates,
family queries, and count methods.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from evolzen.library.persistence import LibraryStore
from evolzen.schemas.library import (
    ProvenanceClass,
    RegressionResult,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
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


def _make_entry(
    status: RuleStatus = RuleStatus.ACTIVE,
    rule_family_id: UUID | None = None,
    version: int = 1,
) -> RuleEntry:
    fid = rule_family_id if rule_family_id is not None else uuid4()
    return RuleEntry(
        rule_id=uuid4(),
        version=version,
        rule_family_id=fid,
        code="def predict(s, a): return s",
        explains=("gravity",),
        status=status,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_append_rule_and_get_by_id(tmp_path: Path) -> None:
    """append_rule persists; get_by_id retrieves correct payload."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    entry = _make_entry()
    store.append_rule(entry)
    retrieved = store.get_by_id(entry.rule_id)
    assert retrieved is not None
    assert retrieved.rule_id == entry.rule_id
    assert retrieved.code == entry.code


def test_get_all_returns_correct_count(tmp_path: Path) -> None:
    """get_all returns one entry per distinct rule_id after multiple appends."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    entries = [_make_entry() for _ in range(5)]
    for e in entries:
        store.append_rule(e)
    all_entries = store.get_all()
    assert len(all_entries) == 5


def test_update_status_superseded_reflects_in_get_by_id(tmp_path: Path) -> None:
    """update_status to SUPERSEDED is visible in get_by_id without deleting original."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    entry = _make_entry()
    store.append_rule(entry)
    new_id = uuid4()
    store.update_status(
        entry.rule_id,
        RuleStatus.SUPERSEDED,
        superseded_by=new_id,
        reason=None,
    )
    updated = store.get_by_id(entry.rule_id)
    assert updated is not None
    assert updated.status is RuleStatus.SUPERSEDED
    assert updated.superseded_by == new_id


def test_original_row_survives_status_update(tmp_path: Path) -> None:
    """After update_status, the DuckDB table still has the original row (append-only)."""
    import duckdb
    store = LibraryStore(tmp_path / "lib.duckdb")
    entry = _make_entry()
    store.append_rule(entry)
    store.update_status(entry.rule_id, RuleStatus.DEPRECATED, superseded_by=None, reason="old")
    with duckdb.connect(str(tmp_path / "lib.duckdb")) as con:
        rows = con.execute(
            "SELECT COUNT(*) FROM rule_entries WHERE rule_id = ?", [str(entry.rule_id)]
        ).fetchone()
    assert rows is not None and rows[0] == 2  # original + status update


def test_get_active_excludes_superseded_and_deprecated(tmp_path: Path) -> None:
    """get_active returns only ACTIVE entries."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    active = _make_entry(RuleStatus.ACTIVE)
    superseded = _make_entry(RuleStatus.ACTIVE)
    deprecated = _make_entry(RuleStatus.ACTIVE)
    for e in (active, superseded, deprecated):
        store.append_rule(e)
    store.update_status(superseded.rule_id, RuleStatus.SUPERSEDED, superseded_by=uuid4(), reason=None)
    store.update_status(deprecated.rule_id, RuleStatus.DEPRECATED, superseded_by=None, reason="done")
    result = store.get_active()
    assert len(result) == 1
    assert result[0].rule_id == active.rule_id


def test_append_supersession_stores_link(tmp_path: Path) -> None:
    """append_supersession writes a row; original rule unchanged."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    old = _make_entry()
    new = _make_entry()
    store.append_rule(old)
    store.append_rule(new)
    link = SupersessionLink(
        old_rule_id=old.rule_id,
        new_rule_id=new.rule_id,
        reason="Replaced by a more general formulation.",
        linked_at=_now(),
    )
    store.append_supersession(link)
    # Original entry unchanged
    orig = store.get_by_id(old.rule_id)
    assert orig is not None
    assert orig.status is RuleStatus.ACTIVE  # not changed by append_supersession alone


def test_append_regression_result(tmp_path: Path) -> None:
    """append_regression_result persists a RegressionResult row."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    entry = _make_entry()
    store.append_rule(entry)
    result = RegressionResult(
        check_id=uuid4(),
        rule_id=entry.rule_id,
        transition_ids_checked=(uuid4(),),
        all_passed=True,
        failed_transition_ids=(),
        checked_at=_now(),
    )
    store.append_regression_result(result)
    import duckdb
    with duckdb.connect(str(tmp_path / "lib.duckdb")) as con:
        rows = con.execute("SELECT COUNT(*) FROM regression_results").fetchone()
    assert rows is not None and rows[0] == 1


def test_count_and_count_active(tmp_path: Path) -> None:
    """count() counts all; count_active() counts only ACTIVE entries."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    active = _make_entry()
    deprecated = _make_entry()
    store.append_rule(active)
    store.append_rule(deprecated)
    store.update_status(deprecated.rule_id, RuleStatus.DEPRECATED, superseded_by=None, reason="retired")
    assert store.count() == 2
    assert store.count_active() == 1


def test_get_family_returns_all_versions_ordered(tmp_path: Path) -> None:
    """get_family returns all entries sharing rule_family_id, ordered by version."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    fid = uuid4()
    v1 = _make_entry(rule_family_id=fid, version=1)
    v2 = RuleEntry(
        rule_id=uuid4(),
        version=2,
        rule_family_id=fid,
        code="def predict(s, a): return a",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )
    store.append_rule(v1)
    store.append_rule(v2)
    family = store.get_family(fid)
    assert len(family) == 2
    assert family[0].version == 1
    assert family[1].version == 2


def test_get_by_id_returns_none_for_unknown(tmp_path: Path) -> None:
    """get_by_id returns None for a rule_id that was never added."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    result = store.get_by_id(uuid4())
    assert result is None


def test_get_supersession_links_all_and_filtered(tmp_path: Path) -> None:
    """get_supersession_links returns all links or filters by rule_id."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    r1, r2, r3 = uuid4(), uuid4(), uuid4()
    link1 = SupersessionLink(
        old_rule_id=r1,
        new_rule_id=r2,
        reason="Updated rule formulation for edge conditions.",
        linked_at=_now(),
    )
    link2 = SupersessionLink(
        old_rule_id=r2,
        new_rule_id=r3,
        reason="Further refinement for multi-step dynamics.",
        linked_at=_now(),
    )
    store.append_supersession(link1)
    store.append_supersession(link2)
    assert len(store.get_supersession_links()) == 2
    assert store.get_supersession_links(r1) == [link1]
    assert store.get_supersession_links(r2) == [link1, link2]


def test_update_status_and_evidence_raise_for_missing_rule(tmp_path: Path) -> None:
    """update_status and update_evidence raise KeyError for unknown rule_id."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    missing = uuid4()
    with pytest.raises(KeyError):
        store.update_status(missing, RuleStatus.DEPRECATED, None, "missing")
    with pytest.raises(KeyError):
        store.update_evidence(missing, _evidence())

