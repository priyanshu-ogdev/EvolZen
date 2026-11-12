"""Append-only JSONL audit log for the Phase 1.5 rule library.

One :class:`AuditEvent` is written per state-changing library operation.
The log is **append-only**: events are never modified or deleted.  Reading
the log is always safe from multiple processes (file-level read; writes use
an exclusive file lock via ``fcntl`` on POSIX and ``msvcrt`` on Windows).

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from evolzen.schemas.library import AuditEvent, AuditEventType


def _lock_file(fh: Any) -> None:  # noqa: ANN401
    """Acquire an exclusive write lock on *fh* (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX)


def _unlock_file(fh: Any) -> None:  # noqa: ANN401
    """Release the write lock on *fh* (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_UN)


def make_event(
    event_type: AuditEventType,
    rule_id: UUID,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    """Factory: build an :class:`AuditEvent` with auto-generated id and timestamp.

    Args:
        event_type: One of the :class:`~evolzen.schemas.library.AuditEventType`
            members (SPAWN, ROUTE, PROMOTE, SUPERSEDE, DEPRECATE, REJECT,
            REGRESSION_CHECK).
        rule_id: UUID of the rule the event concerns.
        detail: Optional freeform mapping of additional context.  Defaults to
            an empty dict.

    Returns:
        A new, immutable :class:`AuditEvent`.
    """
    return AuditEvent(
        event_id=uuid4(),
        event_type=event_type,
        rule_id=rule_id,
        detail=detail or {},
        timestamp=datetime.now(tz=UTC),
    )


class AuditLog:
    """Append-only JSONL audit log.

    One JSON line per :class:`~evolzen.schemas.library.AuditEvent`.  Lines are
    never removed or rewritten.  The parent directory is created on first use.

    Args:
        log_path: Path to the ``.jsonl`` file.

    Example::

        log = AuditLog(Path("data/library_audit.jsonl"))
        event = make_event(AuditEventType.SPAWN, rule_id=some_uuid)
        log.record(event)
    """

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: AuditEvent) -> None:
        """Append *event* as a single JSON line.

        The write is performed under an exclusive file lock to prevent
        interleaved writes from concurrent processes.

        Args:
            event: The :class:`~evolzen.schemas.library.AuditEvent` to persist.
        """
        line = event.model_dump_json() + "\n"
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.seek(0)
            _lock_file(fh)
            try:
                fh.write(line)
                fh.flush()
            finally:
                fh.seek(0)
                _unlock_file(fh)

    def load_all(self) -> list[AuditEvent]:
        """Return all events in the log, in insertion order.

        Returns:
            List of :class:`~evolzen.schemas.library.AuditEvent` objects.
            Returns an empty list if the log file does not exist or is empty.
        """
        if not self._log_path.exists():
            return []
        events: list[AuditEvent] = []
        for raw_line in self._log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line:
                events.append(AuditEvent.model_validate_json(line))
        return events

    def load_for_rule(self, rule_id: UUID) -> list[AuditEvent]:
        """Return all events that concern *rule_id*, in insertion order.

        Args:
            rule_id: UUID of the rule to filter by.

        Returns:
            Filtered list of :class:`~evolzen.schemas.library.AuditEvent` objects.
        """
        return [e for e in self.load_all() if e.rule_id == rule_id]

    def count(self) -> int:
        """Return the total number of events recorded in the log.

        Returns:
            Integer count.
        """
        return len(self.load_all())

