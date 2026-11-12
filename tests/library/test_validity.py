"""Tests for evolzen.library.validity — ValidityContext helpers (Phase 1.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from evolzen.library.validity import (
    applicable_entries,
    is_applicable,
    needs_supersession,
    validate_supersession_reason,
)
from evolzen.schemas.library import (
    ProvenanceClass,
    RuleEntry,
    RuleStatus,
    ValidityContext,
    VerificationEvidence,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _evidence() -> VerificationEvidence:
    return VerificationEvidence(
        evidence_id=uuid4(),
        transition_ids=(),
        intervention_ids=(),
        held_out_combination_ids=(),
        false_promotion_rate=0.0,
        resource_ceiling_hit=False,
    )


def _ctx(
    world: str = "env-v1",
    keys: tuple[str, ...] = ("gravity",),
    seed: tuple[int, int] = (0, 99),
) -> ValidityContext:
    return ValidityContext(
        world_version=world,
        mechanic_keys=keys,
        seed_range=seed,
        verified_at_tick=100,
    )


def _entry(
    status: RuleStatus = RuleStatus.ACTIVE,
    ctx: ValidityContext | None = None,
) -> RuleEntry:
    return RuleEntry(
        rule_id=uuid4(),
        version=1,
        rule_family_id=uuid4(),
        code="def predict(s, a): return s",
        explains=("gravity",),
        status=status,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=ctx or _ctx(),
        evidence=_evidence(),
        created_at=_now(),
    )


# ---------------------------------------------------------------------------
# is_applicable
# ---------------------------------------------------------------------------

def test_is_applicable_returns_true_for_exact_match() -> None:
    """is_applicable is True when world, mechanics, and seed_range match exactly."""
    e = _entry()
    assert is_applicable(e, _ctx()) is True


def test_is_applicable_returns_false_on_world_version_mismatch() -> None:
    """is_applicable is False when world_version differs."""
    e = _entry(ctx=_ctx(world="env-v1"))
    assert is_applicable(e, _ctx(world="env-v2")) is False


def test_is_applicable_returns_false_on_non_overlapping_mechanic_keys() -> None:
    """is_applicable is False when mechanic_keys sets are disjoint."""
    e = _entry(ctx=_ctx(keys=("gravity",)))
    assert is_applicable(e, _ctx(keys=("collision",))) is False


def test_is_applicable_returns_false_on_non_overlapping_seed_range() -> None:
    """is_applicable is False when seed_range intervals do not overlap."""
    e = _entry(ctx=_ctx(seed=(0, 49)))
    assert is_applicable(e, _ctx(seed=(50, 99))) is False


def test_is_applicable_returns_false_for_non_active_entry() -> None:
    """is_applicable is False when entry status is DEPRECATED (not ACTIVE)."""
    e = _entry(status=RuleStatus.DEPRECATED)
    assert is_applicable(e, _ctx()) is False


def test_is_applicable_returns_true_for_overlapping_seed_range() -> None:
    """is_applicable is True when seed_range intervals overlap partially."""
    e = _entry(ctx=_ctx(seed=(0, 60)))
    assert is_applicable(e, _ctx(seed=(50, 99))) is True


# ---------------------------------------------------------------------------
# applicable_entries
# ---------------------------------------------------------------------------

def test_applicable_entries_filters_correctly() -> None:
    """applicable_entries returns only entries applicable in the given context."""
    good = _entry(ctx=_ctx(world="env-v1"))
    bad = _entry(ctx=_ctx(world="env-v2"))
    result = applicable_entries([good, bad], _ctx(world="env-v1"))
    assert len(result) == 1
    assert result[0].rule_id == good.rule_id


# ---------------------------------------------------------------------------
# needs_supersession
# ---------------------------------------------------------------------------

def test_needs_supersession_returns_true_on_incompatible_context() -> None:
    """needs_supersession returns True when contexts are incompatible."""
    e = _entry(ctx=_ctx(world="env-v1"))
    assert needs_supersession(e, _ctx(world="env-v2")) is True


def test_needs_supersession_returns_false_on_compatible_context() -> None:
    """needs_supersession returns False when contexts are compatible."""
    e = _entry()
    assert needs_supersession(e, _ctx()) is False


# ---------------------------------------------------------------------------
# validate_supersession_reason
# ---------------------------------------------------------------------------

def test_validate_supersession_reason_raises_for_short_string() -> None:
    """validate_supersession_reason raises ValueError for short strings."""
    with pytest.raises(ValueError, match="at least 10"):
        validate_supersession_reason("short")


def test_validate_supersession_reason_raises_for_empty_string() -> None:
    """validate_supersession_reason raises ValueError for empty string."""
    with pytest.raises(ValueError):
        validate_supersession_reason("")


def test_validate_supersession_reason_accepts_valid_string() -> None:
    """validate_supersession_reason returns the string unchanged when valid."""
    reason = "Replaced by a more general formulation."
    result = validate_supersession_reason(reason)
    assert result == reason

