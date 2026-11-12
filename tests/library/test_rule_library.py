"""Tests for evolzen.library.rule_library — RuleLibrary (Phase 1.5).

Covers spawn/routing, lifecycle transitions, audit events, and query methods.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.audit import AuditLog
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.schemas.library import (
    AuditEventType,
    ProvenanceClass,
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


def _validity(world: str = "env-v1") -> ValidityContext:
    return ValidityContext(
        world_version=world,
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


def _candidate(code: str = "def predict(s, a): return s") -> CandidateRule:
    return CandidateRule(rule_id=str(uuid4()), code=code, explains=["gravity"])


def _make_library(tmp_path: Path, threshold: float = 0.85) -> RuleLibrary:
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    return RuleLibrary(store, audit, routing_threshold=threshold)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_spawn_if_novel_returns_entry_for_novel_candidate(tmp_path: Path) -> None:
    """spawn_if_novel returns a RuleEntry for a genuinely novel candidate."""
    lib = _make_library(tmp_path)
    candidate = _candidate()
    entry = lib.spawn_if_novel(candidate, _validity(), _evidence())
    assert entry is not None
    assert isinstance(entry, RuleEntry)
    assert entry.status is RuleStatus.ACTIVE


def test_spawn_if_novel_returns_none_for_duplicate(tmp_path: Path) -> None:
    """spawn_if_novel returns None when a very similar rule already exists."""
    lib = _make_library(tmp_path, threshold=0.5)
    code = "def predict(s, a): return s"
    # Spawn the first entry
    lib.spawn_if_novel(_candidate(code), _validity(), _evidence())
    # Identical code should trigger routing
    result = lib.spawn_if_novel(_candidate(code), _validity(), _evidence())
    assert result is None


def test_spawn_records_spawn_audit_event(tmp_path: Path) -> None:
    """spawn_if_novel writes a SPAWN audit event when a new entry is created."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    lib.spawn_if_novel(_candidate(), _validity(), _evidence())
    events = audit.load_all()
    assert any(e.event_type is AuditEventType.SPAWN for e in events)


def test_routing_records_route_audit_event_and_does_not_add_to_store(tmp_path: Path) -> None:
    """Routing writes a ROUTE event and does NOT append to the store."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit, routing_threshold=0.5)
    code = "def predict(s, a): return s"
    lib.spawn_if_novel(_candidate(code), _validity(), _evidence())
    before_count = store.count()
    result = lib.spawn_if_novel(_candidate(code), _validity(), _evidence())
    assert result is None
    assert store.count() == before_count  # no new row added
    events = audit.load_all()
    assert any(e.event_type is AuditEventType.ROUTE for e in events)


def test_promote_updates_evidence_and_records_audit(tmp_path: Path) -> None:
    """promote records a PROMOTE audit event."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    entry = lib.spawn_if_novel(_candidate(), _validity(), _evidence())
    assert entry is not None
    new_ev = VerificationEvidence(
        evidence_id=uuid4(),
        transition_ids=(uuid4(), uuid4()),
        intervention_ids=(),
        held_out_combination_ids=(),
        false_promotion_rate=0.01,
        resource_ceiling_hit=False,
    )
    promoted = lib.promote(entry.rule_id, new_ev)
    assert promoted.evidence.evidence_id == new_ev.evidence_id
    events = audit.load_all()
    assert any(e.event_type is AuditEventType.PROMOTE for e in events)


def test_supersede_creates_link_and_records_audit(tmp_path: Path) -> None:
    """supersede appends a new entry, marks old as SUPERSEDED, records audit event."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    old_entry = lib.spawn_if_novel(_candidate("def predict(s, a): return s"), _validity(), _evidence())
    assert old_entry is not None

    new_entry = RuleEntry(
        rule_id=uuid4(),
        version=2,
        rule_family_id=old_entry.rule_family_id,
        code="def predict(s, a): return a",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )
    link = SupersessionLink(
        old_rule_id=old_entry.rule_id,
        new_rule_id=new_entry.rule_id,
        reason="Replaced by a more general formulation covering edge cases.",
        linked_at=_now(),
    )
    lib.supersede(old_entry.rule_id, new_entry, link)

    old_state = store.get_by_id(old_entry.rule_id)
    assert old_state is not None
    assert old_state.status is RuleStatus.SUPERSEDED
    events = audit.load_all()
    assert any(e.event_type is AuditEventType.SUPERSEDE for e in events)


def test_deprecate_sets_deprecated_status_and_records_audit(tmp_path: Path) -> None:
    """deprecate sets DEPRECATED status and records a DEPRECATE audit event."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    entry = lib.spawn_if_novel(_candidate(), _validity(), _evidence())
    assert entry is not None
    deprecated = lib.deprecate(entry.rule_id, reason="No longer valid in env-v2")
    assert deprecated.status is RuleStatus.DEPRECATED
    events = audit.load_all()
    assert any(e.event_type is AuditEventType.DEPRECATE for e in events)


def test_get_active_excludes_non_active(tmp_path: Path) -> None:
    """get_active only returns ACTIVE entries."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    e1 = lib.spawn_if_novel(
        _candidate("def gravity_step(s, a): return s.y - 9.8"), _validity(), _evidence()
    )
    e2 = lib.spawn_if_novel(
        _candidate("def friction_drag(s, a): return s.vx * 0.92"), _validity(), _evidence()
    )
    assert e1 is not None and e2 is not None
    lib.deprecate(e2.rule_id, reason="Retired for testing purposes.")
    active = lib.get_active()
    assert len(active) == 1
    assert active[0].rule_id == e1.rule_id


def test_len_counts_all_statuses_active_count_counts_active(tmp_path: Path) -> None:
    """__len__ counts all entries; active_count counts only ACTIVE."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    e1 = lib.spawn_if_novel(
        _candidate("def gravity_step(s, a): return s.y - 9.8"), _validity(), _evidence()
    )
    e2 = lib.spawn_if_novel(
        _candidate("def friction_drag(s, a): return s.vx * 0.92"), _validity(), _evidence()
    )
    assert e1 is not None and e2 is not None
    lib.deprecate(e2.rule_id, "Retired.")
    assert len(lib) == 2
    assert lib.active_count() == 1


def test_get_family_returns_all_versions(tmp_path: Path) -> None:
    """get_family returns both v1 and v2 entries of the same family."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    old_entry = lib.spawn_if_novel(_candidate("def v1(): pass"), _validity(), _evidence())
    assert old_entry is not None

    new_entry = RuleEntry(
        rule_id=uuid4(),
        version=2,
        rule_family_id=old_entry.rule_family_id,
        code="def v2(): pass",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )
    link = SupersessionLink(
        old_rule_id=old_entry.rule_id,
        new_rule_id=new_entry.rule_id,
        reason="v2 generalises v1 to cover additional transition patterns.",
        linked_at=_now(),
    )
    lib.supersede(old_entry.rule_id, new_entry, link)
    family = lib.get_family(old_entry.rule_family_id)
    assert len(family) == 2
    assert {e.version for e in family} == {1, 2}


def test_reject_records_audit_event_without_persisting_rule(tmp_path: Path) -> None:
    """reject logs AuditEventType.REJECT without appending to rule_entries."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    candidate = _candidate("def bad_rule(s, a): return s")
    ev = _evidence()
    event = lib.reject(candidate, reason="Failed held-out intervention check.", evidence=ev)
    assert event.event_type is AuditEventType.REJECT
    assert len(lib) == 0
    assert audit.count() == 1

    with pytest.raises(ValueError, match="non-empty"):
        lib.reject(candidate, reason="   ")


def test_revert_supersession_restores_old_rule_and_deprecates_new(tmp_path: Path) -> None:
    """revert_supersession restores old rule to ACTIVE and preserves append-only lineage."""
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    lib = RuleLibrary(store, audit)
    old_entry = lib.spawn_if_novel(_candidate("def v1(s, a): return s"), _validity(), _evidence())
    assert old_entry is not None

    new_entry = RuleEntry(
        rule_id=uuid4(),
        version=2,
        rule_family_id=old_entry.rule_family_id,
        code="def v2(s, a): return a",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )
    link = SupersessionLink(
        old_rule_id=old_entry.rule_id,
        new_rule_id=new_entry.rule_id,
        reason="Tentative v2 formulation for world change.",
        linked_at=_now(),
    )
    lib.supersede(old_entry.rule_id, new_entry, link)
    assert lib.get_supersession_links(old_entry.rule_id) == [link]

    restored = lib.revert_supersession(
        old_entry.rule_id, reason="Reverting after v2 failed held-out replay."
    )
    assert restored.status is RuleStatus.ACTIVE
    assert restored.superseded_by is None
    new_after = lib.get(new_entry.rule_id)
    assert new_after is not None and new_after.status is RuleStatus.DEPRECATED
    assert any(e.event_type is AuditEventType.REVERT for e in audit.load_all())


def test_get_accepts_uuid_string_and_invalid_string(tmp_path: Path) -> None:
    """get accepts a UUID string and returns None for malformed UUID strings."""
    lib = _make_library(tmp_path)
    entry = lib.spawn_if_novel(_candidate(), _validity(), _evidence())
    assert entry is not None
    fetched = lib.get(str(entry.rule_id))
    assert fetched is not None and fetched.rule_id == entry.rule_id
    assert lib.get("not-a-uuid") is None


def test_lifecycle_error_guards(tmp_path: Path) -> None:
    """promote, supersede, deprecate, and revert_supersession enforce precondition errors."""
    lib = _make_library(tmp_path)
    missing = uuid4()
    with pytest.raises(KeyError):
        lib.promote(missing, _evidence())
    with pytest.raises(KeyError):
        lib.deprecate(missing, "does not exist")
    with pytest.raises(KeyError):
        lib.revert_supersession(missing, "No such rule exists to revert.")

    entry = lib.spawn_if_novel(_candidate(), _validity(), _evidence())
    assert entry is not None
    with pytest.raises(ValueError, match="Only SUPERSEDED"):
        lib.revert_supersession(entry.rule_id, "Cannot revert an active rule.")

    lib.deprecate(entry.rule_id, "retired")
    with pytest.raises(ValueError, match="Only ACTIVE"):
        lib.promote(entry.rule_id, _evidence())

    other_id = uuid4()
    bad_link = SupersessionLink(
        old_rule_id=other_id,
        new_rule_id=uuid4(),
        reason="Mismatched link for error check.",
        linked_at=_now(),
    )
    with pytest.raises(ValueError, match="old_rule_id"):
        lib.supersede(entry.rule_id, entry, bad_link)


def test_default_routing_respects_validity_context(tmp_path: Path) -> None:
    """Identical code in a different world_version must spawn, not route."""
    lib = _make_library(tmp_path, threshold=0.85)
    code = "def predict(s, a): return s"
    e1 = lib.spawn_if_novel(_candidate(code), _validity("env-v1"), _evidence())
    e2 = lib.spawn_if_novel(_candidate(code), _validity("env-v2"), _evidence())
    assert e1 is not None and e2 is not None
    assert e1.rule_id != e2.rule_id
    assert len(lib) == 2
