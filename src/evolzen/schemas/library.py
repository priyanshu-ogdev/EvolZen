"""Pydantic schemas for the Phase 1.5 verified-rule library (evolzen.library).

Every type here is **frozen** — instances are immutable after construction.
No field may be silently coerced or added beyond the declared schema
(``extra="forbid"``).  Any downstream consumer that changes these schemas
must re-run ``mypy --strict`` across all nine subsystems before merging.

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5, PRD FR-6.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class _LibraryRecord(BaseModel):
    """Shared base: immutable, closed-schema, validated defaults.

    All library schema classes inherit from this base so the ``ConfigDict``
    is defined in one place and cannot accidentally be overridden.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RuleStatus(StrEnum):
    """Lifecycle state of a :class:`RuleEntry`.

    Entries are **never** physically deleted; a status transition is recorded
    as a new row in the store while the original row remains readable.
    """

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


class ProvenanceClass(StrEnum):
    """Origin classification of a :class:`RuleEntry`.

    ``EXPLORATION_VERIFIED`` is the normal path: the rule passed the exact-match
    verifier in ``evolzen.exploration.verifier``.  The other values cover
    human-authored rules, rules ported from external sources, and cases where
    provenance cannot be determined.
    """

    EXPLORATION_VERIFIED = "exploration_verified"
    HUMAN_AUTHORED = "human_authored"
    IMPORTED_EXTERNAL = "imported_external"
    UNKNOWN = "unknown"


class AuditEventType(StrEnum):
    """Discriminant for :class:`AuditEvent` records written to the audit log."""

    SPAWN = "spawn"
    ROUTE = "route"
    PROMOTE = "promote"
    SUPERSEDE = "supersede"
    REVERT = "revert"
    DEPRECATE = "deprecate"
    REJECT = "reject"
    REGRESSION_CHECK = "regression_check"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class ValidityContext(_LibraryRecord):
    """Describes *which* world version and mechanics a rule was verified against.

    Two :class:`RuleEntry` instances in the same family may have different
    ``ValidityContext`` values when mechanics changed between world versions.

    Attributes:
        world_version: Opaque string tag for the world/environment version
            (e.g. ``"env-v1"``).
        mechanic_keys: Ordered tuple of mechanic identifiers the rule covers.
        seed_range: Inclusive ``[low, high]`` integer range of environment seeds
            over which verification was performed.
        verified_at_tick: World clock tick at which verification completed.
    """

    world_version: str
    mechanic_keys: tuple[str, ...]
    seed_range: tuple[int, int]
    verified_at_tick: int = Field(ge=0)

    @field_validator("seed_range")
    @classmethod
    def _seed_range_ordered(cls, v: tuple[int, int]) -> tuple[int, int]:
        low, high = v
        if low > high:
            raise ValueError(f"seed_range low ({low}) must be <= high ({high})")
        return v

    @field_validator("mechanic_keys")
    @classmethod
    def _mechanic_keys_non_empty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("mechanic_keys must contain at least one key")
        return v


class VerificationEvidence(_LibraryRecord):
    """Evidence linking a rule to the transitions it was verified against.

    Attributes:
        evidence_id: Unique identifier for this evidence bundle.
        transition_ids: UUIDs of transitions used as positive verification cases.
        intervention_ids: UUIDs of interventions (counterfactuals) used.
        held_out_combination_ids: UUIDs of held-out mechanic combinations reserved
            for regression testing.
        false_promotion_rate: Fraction of verification attempts that yielded a
            false positive.  Must be in ``[0.0, 1.0]``.
        resource_ceiling_hit: ``True`` if the verifier reached its resource limit
            before exhausting the full test set.
    """

    evidence_id: UUID = Field(default_factory=uuid4)
    transition_ids: tuple[UUID, ...] = ()
    intervention_ids: tuple[UUID, ...] = ()
    held_out_combination_ids: tuple[UUID, ...] = ()
    false_promotion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_ceiling_hit: bool = False

    @property
    def evidence_id_str(self) -> str:
        """String representation of evidence_id for string-based linkages."""
        return str(self.evidence_id)


# ---------------------------------------------------------------------------
# Core domain types
# ---------------------------------------------------------------------------

class RuleEntry(_LibraryRecord):
    """An immutable, versioned, append-only record of a verified rule.

    Old entries are **never** overwritten or deleted.  When a rule is superseded
    a new :class:`RuleEntry` is appended and the old one's ``status`` column is
    updated to ``RuleStatus.SUPERSEDED``; the old row remains in the store.

    Attributes:
        rule_id: Globally unique identifier for this specific rule version.
        version: Monotonically increasing integer starting at 1; incremented on
            each supersession within the same family.
        rule_family_id: Groups all versions of the same conceptual rule across
            supersessions.
        code: Python source implementing ``(State, Action) -> Emission``
            prediction.  **Never** executed outside
            ``evolzen.containment.Sandbox``.
        explains: Mechanic keys this rule was synthesized to explain.
        status: Current lifecycle state.
        provenance: Origin classification.
        validity: World version and mechanic context this rule was verified in.
        evidence: Verification evidence bundle.
        superseded_by: If ``status`` is ``SUPERSEDED``, the ``rule_id`` of the
            replacement entry; otherwise ``None``.
        deprecation_reason: Human-readable reason when ``status`` is
            ``DEPRECATED``; otherwise ``None``.
        created_at: UTC timestamp of library insertion.
    """

    rule_id: UUID
    version: int = Field(ge=1)
    rule_family_id: UUID
    code: str
    explains: tuple[str, ...]
    status: RuleStatus
    provenance: ProvenanceClass
    validity: ValidityContext
    evidence: VerificationEvidence
    superseded_by: UUID | None = None
    deprecation_reason: str | None = None
    created_at: datetime

    @field_validator("explains")
    @classmethod
    def _explains_non_empty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("explains must contain at least one mechanic key")
        return v


class SupersessionLink(_LibraryRecord):
    """Explicit link recording that one rule was superseded by another.

    Supersession requires a non-trivial documented reason so the history of
    *why* a rule was replaced is preserved.

    Attributes:
        old_rule_id: ``rule_id`` of the entry being superseded.
        new_rule_id: ``rule_id`` of the replacement entry.
        reason: Human-readable justification (minimum 10 characters).
        linked_at: UTC timestamp of the supersession event.
    """

    old_rule_id: UUID
    new_rule_id: UUID
    reason: str
    linked_at: datetime

    @field_validator("reason")
    @classmethod
    def _reason_non_trivial(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError(
                f"SupersessionLink.reason must be at least 10 characters; got {len(v.strip())!r}"
            )
        return v


class AuditEvent(_LibraryRecord):
    """Immutable audit record written to the append-only JSONL audit log.

    One event is written for each state-changing library operation
    (SPAWN, ROUTE, PROMOTE, SUPERSEDE, DEPRECATE, REJECT, REGRESSION_CHECK).

    Attributes:
        event_id: Unique identifier for this event.
        event_type: Discriminant classifying the operation.
        rule_id: The ``rule_id`` the event concerns.
        detail: Freeform mapping of additional context (serialised to JSON).
        timestamp: UTC timestamp of the event.
    """

    event_id: UUID
    event_type: AuditEventType
    rule_id: UUID
    detail: dict[str, Any]
    timestamp: datetime


class RegressionResult(_LibraryRecord):
    """Outcome of a single regression check for one rule.

    Stored in the ``regression_results`` DuckDB table so that the zero-forgetting
    metric (Phase 1.5 success criterion) can be queried at any time.

    Attributes:
        check_id: Unique identifier for this regression run.
        rule_id: The rule that was checked.
        transition_ids_checked: Transition fixture IDs that were replayed.
        all_passed: ``True`` iff every fixture produced the expected emission.
        failed_transition_ids: Subset of ``transition_ids_checked`` that failed
            (empty when ``all_passed`` is ``True``).
        checked_at: UTC timestamp of the regression run.
    """

    check_id: UUID
    rule_id: UUID
    transition_ids_checked: tuple[UUID, ...]
    all_passed: bool
    failed_transition_ids: tuple[UUID, ...]
    checked_at: datetime


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # Enumerations
    "AuditEventType",
    "ProvenanceClass",
    "RuleStatus",
    # Value objects
    "ValidityContext",
    "VerificationEvidence",
    # Domain types
    "AuditEvent",
    "RegressionResult",
    "RuleEntry",
    "SupersessionLink",
]


# ---------------------------------------------------------------------------
# Convenience type alias referenced by evolzen.library modules
# ---------------------------------------------------------------------------

#: Literal union accepted by AuditEvent.event_type — kept here for import convenience.
AuditEventTypeLiteral = Literal[
    "spawn", "route", "promote", "supersede", "revert", "deprecate", "reject", "regression_check"
]

