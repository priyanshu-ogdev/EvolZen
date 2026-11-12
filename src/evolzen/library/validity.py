"""Validity-context helpers for the Phase 1.5 rule library.

A rule is *applicable* in a given context when its recorded
:class:`~evolzen.schemas.library.ValidityContext` is compatible with the
context being queried.  Compatibility is defined as:

- ``world_version`` must match exactly.
- ``mechanic_keys`` sets must share at least one element.
- ``seed_range`` intervals must overlap (inclusive).

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5.
"""

from __future__ import annotations

from collections.abc import Iterable

from evolzen.schemas.library import RuleEntry, RuleStatus, ValidityContext


def is_applicable(entry: RuleEntry, context: ValidityContext) -> bool:
    """Return ``True`` iff *entry* is applicable in *context*.

    Applicability conditions (all must hold):

    1. ``entry.status`` is ``ACTIVE``.
    2. ``entry.validity.world_version == context.world_version``.
    3. The ``mechanic_keys`` sets share at least one element.
    4. The ``seed_range`` intervals overlap (``[lo1, hi1] ∩ [lo2, hi2] ≠ ∅``).

    Args:
        entry: The :class:`~evolzen.schemas.library.RuleEntry` to test.
        context: The :class:`~evolzen.schemas.library.ValidityContext` to
            test applicability against.

    Returns:
        ``True`` if the entry is applicable, ``False`` otherwise.
    """
    if entry.status is not RuleStatus.ACTIVE:
        return False
    if entry.validity.world_version != context.world_version:
        return False
    if not set(entry.validity.mechanic_keys) & set(context.mechanic_keys):
        return False
    lo1, hi1 = entry.validity.seed_range
    lo2, hi2 = context.seed_range
    return not (lo1 > hi2 or lo2 > hi1)


def applicable_entries(
    entries: Iterable[RuleEntry], context: ValidityContext
) -> list[RuleEntry]:
    """Filter *entries* to those applicable in *context*.

    Args:
        entries: Iterable of :class:`~evolzen.schemas.library.RuleEntry` objects.
        context: The context to filter against.

    Returns:
        List of entries that pass :func:`is_applicable`.
    """
    return [e for e in entries if is_applicable(e, context)]


def needs_supersession(old: RuleEntry, new_context: ValidityContext) -> bool:
    """Return ``True`` iff *old* is **incompatible** with *new_context*.

    A rule that is incompatible with the new context needs to be superseded by
    a revision that is verified in that context before it can be used there.

    Args:
        old: The existing :class:`~evolzen.schemas.library.RuleEntry`.
        new_context: The new :class:`~evolzen.schemas.library.ValidityContext`.

    Returns:
        ``True`` if the rule needs supersession; ``False`` if it is still
        applicable in *new_context*.
    """
    return not is_applicable(old, new_context)


def validate_supersession_reason(reason: str) -> str:
    """Validate that *reason* is a non-trivial supersession justification.

    A reason must be at least 10 non-whitespace characters long.

    Args:
        reason: The proposed supersession reason string.

    Returns:
        The original *reason* string, unchanged.

    Raises:
        ValueError: If *reason* is empty or fewer than 10 non-whitespace chars.
    """
    stripped = reason.strip()
    if len(stripped) < 10:
        raise ValueError(
            f"Supersession reason must be at least 10 non-whitespace characters; "
            f"got {len(stripped)!r} in {reason!r}"
        )
    return reason

