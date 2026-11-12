"""Tests for evolzen.schemas.library — Phase 1.5 schema contracts.

Verifies immutability, closed-schema enforcement, field validators,
and lossless JSON roundtrips for all library schema types.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from evolzen.schemas.library import (
    AuditEvent,
    AuditEventType,
    ProvenanceClass,
    RegressionResult,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
    ValidityContext,
    VerificationEvidence,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(tz=UTC)


def _validity() -> ValidityContext:
    return ValidityContext(
        world_version="env-v1",
        mechanic_keys=("gravity", "collision"),
        seed_range=(0, 99),
        verified_at_tick=500,
    )


def _evidence() -> VerificationEvidence:
    return VerificationEvidence(
        evidence_id=uuid4(),
        transition_ids=(uuid4(), uuid4()),
        intervention_ids=(uuid4(),),
        held_out_combination_ids=(uuid4(),),
        false_promotion_rate=0.02,
        resource_ceiling_hit=False,
    )


def _rule_entry(status: RuleStatus = RuleStatus.ACTIVE) -> RuleEntry:
    return RuleEntry(
        rule_id=uuid4(),
        version=1,
        rule_family_id=uuid4(),
        code="def predict(s, a): return s",
        explains=("gravity",),
        status=status,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=_validity(),
        evidence=_evidence(),
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# 1. Immutability
# ---------------------------------------------------------------------------

def test_rule_entry_is_immutable() -> None:
    """Assignment to any field must raise ValidationError (frozen model)."""
    entry = _rule_entry()
    with pytest.raises(ValidationError):
        entry.version = 2


# ---------------------------------------------------------------------------
# 2. Closed schema — extra fields rejected
# ---------------------------------------------------------------------------

def test_rule_entry_rejects_extra_fields() -> None:
    """Extra fields must be rejected with ValidationError."""
    with pytest.raises(ValidationError):
        RuleEntry(
            rule_id=uuid4(),
            version=1,
            rule_family_id=uuid4(),
            code="...",
            explains=("gravity",),
            status=RuleStatus.ACTIVE,
            provenance=ProvenanceClass.EXPLORATION_VERIFIED,
            validity=_validity(),
            evidence=_evidence(),
            created_at=_now(),
            unknown_field="oops",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# 3. JSON roundtrip — lossless
# ---------------------------------------------------------------------------

def test_rule_entry_json_roundtrip_is_lossless() -> None:
    """model_dump_json → model_validate_json must reproduce the original object."""
    original = _rule_entry()
    restored = RuleEntry.model_validate_json(original.model_dump_json())
    assert original == restored


def test_audit_event_json_roundtrip_preserves_event_type() -> None:
    """AuditEvent roundtrip must preserve event_type as an AuditEventType member."""
    event = AuditEvent(
        event_id=uuid4(),
        event_type=AuditEventType.SPAWN,
        rule_id=uuid4(),
        detail={"candidate_code_hash": "abc123"},
        timestamp=_now(),
    )
    restored = AuditEvent.model_validate_json(event.model_dump_json())
    assert restored.event_type is AuditEventType.SPAWN
    assert isinstance(restored.event_type, AuditEventType)


# ---------------------------------------------------------------------------
# 4. Field validators
# ---------------------------------------------------------------------------

def test_false_promotion_rate_rejects_out_of_range() -> None:
    """false_promotion_rate outside [0.0, 1.0] must be rejected."""
    with pytest.raises(ValidationError):
        VerificationEvidence(
            evidence_id=uuid4(),
            transition_ids=(),
            intervention_ids=(),
            held_out_combination_ids=(),
            false_promotion_rate=1.5,  # out of range
            resource_ceiling_hit=False,
        )


def test_supersession_reason_rejects_short_string() -> None:
    """SupersessionLink.reason shorter than 10 chars must be rejected."""
    with pytest.raises(ValidationError):
        SupersessionLink(
            old_rule_id=uuid4(),
            new_rule_id=uuid4(),
            reason="too short",  # 9 chars
            linked_at=_now(),
        )


def test_supersession_reason_accepts_long_string() -> None:
    """SupersessionLink.reason of >= 10 non-whitespace chars must be accepted."""
    link = SupersessionLink(
        old_rule_id=uuid4(),
        new_rule_id=uuid4(),
        reason="Replaced by a more general formulation covering edge cases.",
        linked_at=_now(),
    )
    assert len(link.reason) >= 10


# ---------------------------------------------------------------------------
# 5. StrEnum contract
# ---------------------------------------------------------------------------

def test_rule_status_is_str_subclass() -> None:
    """RuleStatus members must be str instances (StrEnum contract)."""
    for member in RuleStatus:
        assert isinstance(member, str), f"{member!r} is not a str"


def test_all_audit_event_types_roundtrip() -> None:
    """Every AuditEventType value must roundtrip through AuditEvent serialisation."""
    for event_type in AuditEventType:
        event = AuditEvent(
            event_id=uuid4(),
            event_type=event_type,
            rule_id=uuid4(),
            detail={},
            timestamp=_now(),
        )
        raw = json.loads(event.model_dump_json())
        assert raw["event_type"] == str(event_type)
        restored = AuditEvent.model_validate(raw)
        assert restored.event_type is event_type


# ---------------------------------------------------------------------------
# 6. Optional fields default to None
# ---------------------------------------------------------------------------

def test_rule_entry_superseded_by_defaults_to_none() -> None:
    """RuleEntry without superseded_by must serialise and deserialise with None."""
    entry = _rule_entry()
    assert entry.superseded_by is None
    restored = RuleEntry.model_validate_json(entry.model_dump_json())
    assert restored.superseded_by is None


# ---------------------------------------------------------------------------
# 7. ValidityContext seed_range validator
# ---------------------------------------------------------------------------

def test_validity_context_rejects_inverted_seed_range() -> None:
    """seed_range low > high must be rejected."""
    with pytest.raises(ValidationError):
        ValidityContext(
            world_version="env-v1",
            mechanic_keys=("gravity",),
            seed_range=(99, 0),  # inverted
            verified_at_tick=1,
        )


# ---------------------------------------------------------------------------
# 8. RegressionResult roundtrip
# ---------------------------------------------------------------------------

def test_regression_result_roundtrip() -> None:
    """RegressionResult must roundtrip losslessly with failed_transition_ids empty."""
    result = RegressionResult(
        check_id=uuid4(),
        rule_id=uuid4(),
        transition_ids_checked=(uuid4(), uuid4()),
        all_passed=True,
        failed_transition_ids=(),
        checked_at=_now(),
    )
    restored = RegressionResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.all_passed is True
    assert restored.failed_transition_ids == ()

