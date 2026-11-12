"""Tests for evolzen.library.audit — AuditLog and make_event (Phase 1.5)."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from uuid import uuid4

from evolzen.library.audit import AuditLog, make_event
from evolzen.schemas.library import AuditEventType

# ---------------------------------------------------------------------------
# make_event
# ---------------------------------------------------------------------------

def test_make_event_fills_event_id_as_uuid() -> None:
    """make_event must produce an AuditEvent with a valid UUID event_id."""
    event = make_event(AuditEventType.SPAWN, rule_id=uuid4())
    assert event.event_id is not None
    # UUID from uuid4 — just check it's not the nil UUID
    from uuid import UUID
    assert event.event_id != UUID(int=0)


def test_make_event_fills_timestamp_as_utc() -> None:
    """make_event must produce an AuditEvent with a UTC-aware timestamp."""
    event = make_event(AuditEventType.SPAWN, rule_id=uuid4())
    assert event.timestamp.tzinfo == UTC


def test_make_event_defaults_detail_to_empty_dict() -> None:
    """make_event with no detail argument must produce an empty dict."""
    event = make_event(AuditEventType.ROUTE, rule_id=uuid4())
    assert event.detail == {}


def test_make_event_includes_provided_detail() -> None:
    """make_event must pass through the detail dict unchanged."""
    detail = {"candidate_rule_id": "abc", "similarity_score": 0.95}
    event = make_event(AuditEventType.SPAWN, rule_id=uuid4(), detail=detail)
    assert event.detail == detail


# ---------------------------------------------------------------------------
# AuditLog.record and load_all
# ---------------------------------------------------------------------------

def test_record_appends_valid_json_line(tmp_path: Path) -> None:
    """record must append one JSON line per event."""
    log = AuditLog(tmp_path / "audit.jsonl")
    event = make_event(AuditEventType.SPAWN, rule_id=uuid4())
    log.record(event)
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    # Must be valid JSON
    import json
    json.loads(lines[0])


def test_load_all_deserialises_all_events(tmp_path: Path) -> None:
    """load_all must return all recorded events in insertion order."""
    log = AuditLog(tmp_path / "audit.jsonl")
    events = [
        make_event(AuditEventType.SPAWN, rule_id=uuid4()),
        make_event(AuditEventType.PROMOTE, rule_id=uuid4()),
        make_event(AuditEventType.DEPRECATE, rule_id=uuid4()),
    ]
    for e in events:
        log.record(e)
    loaded = log.load_all()
    assert len(loaded) == 3
    assert [e.event_type for e in loaded] == [
        AuditEventType.SPAWN, AuditEventType.PROMOTE, AuditEventType.DEPRECATE
    ]


def test_load_for_rule_returns_only_matching_events(tmp_path: Path) -> None:
    """load_for_rule returns only events whose rule_id matches."""
    log = AuditLog(tmp_path / "audit.jsonl")
    r1 = uuid4()
    r2 = uuid4()
    log.record(make_event(AuditEventType.SPAWN, rule_id=r1))
    log.record(make_event(AuditEventType.SPAWN, rule_id=r2))
    log.record(make_event(AuditEventType.PROMOTE, rule_id=r1))
    result = log.load_for_rule(r1)
    assert len(result) == 2
    assert all(e.rule_id == r1 for e in result)


def test_count_matches_number_of_record_calls(tmp_path: Path) -> None:
    """count() must equal the number of times record() was called."""
    log = AuditLog(tmp_path / "audit.jsonl")
    for _ in range(7):
        log.record(make_event(AuditEventType.SPAWN, rule_id=uuid4()))
    assert log.count() == 7


def test_record_called_twice_with_same_event_grows_file(tmp_path: Path) -> None:
    """Calling record twice with the same event appends two lines (idempotency not guaranteed)."""
    log = AuditLog(tmp_path / "audit.jsonl")
    event = make_event(AuditEventType.SPAWN, rule_id=uuid4())
    log.record(event)
    log.record(event)
    assert log.count() == 2


def test_audit_log_creates_parent_directories(tmp_path: Path) -> None:
    """AuditLog must create missing parent directories automatically."""
    deep_path = tmp_path / "a" / "b" / "c" / "audit.jsonl"
    log = AuditLog(deep_path)
    log.record(make_event(AuditEventType.SPAWN, rule_id=uuid4()))
    assert deep_path.exists()


def test_load_all_on_empty_file_returns_empty_list(tmp_path: Path) -> None:
    """load_all on a fresh (empty) AuditLog returns []."""
    log = AuditLog(tmp_path / "audit.jsonl")
    assert log.load_all() == []


def test_all_audit_event_types_roundtrip_through_audit_log(tmp_path: Path) -> None:
    """Every AuditEventType value must survive record → load_all → event_type check."""
    log = AuditLog(tmp_path / "audit.jsonl")
    rule_id = uuid4()
    for event_type in AuditEventType:
        log.record(make_event(event_type, rule_id=rule_id))
    loaded = log.load_all()
    loaded_types = {e.event_type for e in loaded}
    assert loaded_types == set(AuditEventType)

