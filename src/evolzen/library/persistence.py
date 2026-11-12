"""DuckDB-backed append-only persistence layer for the Phase 1.5 rule library.

All writes are **append-only**: no row is ever physically overwritten or deleted.
Status updates and supersession links are recorded as new rows; the retrieval
methods return the most-recent state per ``rule_id`` via a window function.

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5, PRD FR-6.
Persistence pattern adapted from evolzen.storage.transition_log (DuckDB context-
manager-per-call convention).
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import duckdb

from evolzen.schemas.library import (
    RegressionResult,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
    VerificationEvidence,
)


class LibraryStore:
    """Append-only DuckDB store for :class:`~evolzen.schemas.library.RuleEntry` objects.

    Each public method opens its own short-lived DuckDB connection so that the
    store is safe to call from multiple processes that share the same file
    (DuckDB WAL handles concurrency).

    Args:
        db_path: Filesystem path to the ``.duckdb`` file.  Parent directories
            are created on first use.

    Example::

        store = LibraryStore(Path("data/library.duckdb"))
        store.append_rule(entry)
        retrieved = store.get_by_id(entry.rule_id)
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        """Create all sequences and tables if they do not already exist."""
        with duckdb.connect(str(self._db_path)) as con:
            con.execute("CREATE SEQUENCE IF NOT EXISTS rule_entries_seq START 1")
            con.execute("""
                CREATE TABLE IF NOT EXISTS rule_entries (
                    row_seq      BIGINT PRIMARY KEY DEFAULT nextval('rule_entries_seq'),
                    rule_id      TEXT NOT NULL,
                    version      INTEGER NOT NULL,
                    payload      TEXT NOT NULL
                )
            """)
            con.execute("CREATE SEQUENCE IF NOT EXISTS ss_links_seq START 1")
            con.execute("""
                CREATE TABLE IF NOT EXISTS supersession_links (
                    row_seq     BIGINT PRIMARY KEY DEFAULT nextval('ss_links_seq'),
                    old_rule_id TEXT NOT NULL,
                    new_rule_id TEXT NOT NULL,
                    payload     TEXT NOT NULL
                )
            """)
            con.execute("CREATE SEQUENCE IF NOT EXISTS reg_results_seq START 1")
            con.execute("""
                CREATE TABLE IF NOT EXISTS regression_results (
                    row_seq  BIGINT PRIMARY KEY DEFAULT nextval('reg_results_seq'),
                    check_id TEXT NOT NULL,
                    rule_id  TEXT NOT NULL,
                    payload  TEXT NOT NULL
                )
            """)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append_rule(self, entry: RuleEntry) -> None:
        """Append a new :class:`RuleEntry` row.

        Never overwrites an existing row.  Caller is responsible for
        ensuring ``rule_id`` uniqueness (checked via
        :meth:`get_by_id` before calling).

        Args:
            entry: The rule entry to persist.
        """
        payload = entry.model_dump_json()
        with duckdb.connect(str(self._db_path)) as con:
            con.execute(
                "INSERT INTO rule_entries (rule_id, version, payload) VALUES (?, ?, ?)",
                [str(entry.rule_id), entry.version, payload],
            )

    def update_status(
        self,
        rule_id: UUID,
        status: RuleStatus,
        superseded_by: UUID | None,
        reason: str | None,
    ) -> None:
        """Record a status change by appending an updated row.

        The original row is **never** modified; this appends a new row
        carrying the updated payload so the full history is preserved.

        Args:
            rule_id: Identifier of the rule whose status is changing.
            status: New lifecycle status.
            superseded_by: If ``status`` is ``SUPERSEDED``, the replacing
                rule's id; otherwise ``None``.
            reason: Deprecation reason when ``status`` is ``DEPRECATED``.
        """
        existing = self.get_by_id(rule_id)
        if existing is None:
            raise KeyError(f"No rule entry found for rule_id={rule_id}")
        updated = existing.model_copy(
            update={
                "status": status,
                "superseded_by": superseded_by,
                "deprecation_reason": reason,
            }
        )
        payload = updated.model_dump_json()
        with duckdb.connect(str(self._db_path)) as con:
            con.execute(
                "INSERT INTO rule_entries (rule_id, version, payload) VALUES (?, ?, ?)",
                [str(rule_id), updated.version, payload],
            )

    def update_evidence(
        self,
        rule_id: UUID,
        evidence: VerificationEvidence,
    ) -> RuleEntry:
        """Record updated verification evidence by appending a new row.

        The original row is preserved intact (append-only).

        Args:
            rule_id: Identifier of the rule whose evidence is updated.
            evidence: New :class:`VerificationEvidence` bundle.

        Returns:
            The updated :class:`RuleEntry`.

        Raises:
            KeyError: If *rule_id* does not exist in the store.
        """
        existing = self.get_by_id(rule_id)
        if existing is None:
            raise KeyError(f"No rule entry found for rule_id={rule_id}")
        updated = existing.model_copy(update={"evidence": evidence})
        self.append_rule(updated)
        return updated

    def append_supersession(self, link: SupersessionLink) -> None:
        """Persist a :class:`SupersessionLink` record.

        Args:
            link: The supersession link to append.
        """
        payload = link.model_dump_json()
        with duckdb.connect(str(self._db_path)) as con:
            con.execute(
                "INSERT INTO supersession_links (old_rule_id, new_rule_id, payload) "
                "VALUES (?, ?, ?)",
                [str(link.old_rule_id), str(link.new_rule_id), payload],
            )

    def append_regression_result(self, result: RegressionResult) -> None:
        """Persist a :class:`RegressionResult` record.

        Args:
            result: The regression check outcome to store.
        """
        payload = result.model_dump_json()
        with duckdb.connect(str(self._db_path)) as con:
            con.execute(
                "INSERT INTO regression_results (check_id, rule_id, payload) VALUES (?, ?, ?)",
                [str(result.check_id), str(result.rule_id), payload],
            )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_by_id(self, rule_id: UUID) -> RuleEntry | None:
        """Return the latest state of a rule entry, or ``None`` if not found.

        "Latest" is defined by highest ``row_seq`` for the given ``rule_id``.

        Args:
            rule_id: UUID of the rule to look up.

        Returns:
            The most-recent :class:`RuleEntry` row, or ``None``.
        """
        with duckdb.connect(str(self._db_path)) as con:
            rows = con.execute(
                "SELECT payload FROM rule_entries WHERE rule_id = ? "
                "ORDER BY row_seq DESC LIMIT 1",
                [str(rule_id)],
            ).fetchall()
        if not rows:
            return None
        return RuleEntry.model_validate_json(rows[0][0])

    def get_all(self) -> list[RuleEntry]:
        """Return the latest state of every rule entry in the store.

        Uses a window function to deduplicate: only the row with the highest
        ``row_seq`` per ``rule_id`` is returned.

        Returns:
            List of latest :class:`RuleEntry` objects (all statuses).
        """
        with duckdb.connect(str(self._db_path)) as con:
            rows = con.execute("""
                SELECT payload
                FROM (
                    SELECT row_seq, payload, ROW_NUMBER() OVER (
                        PARTITION BY rule_id ORDER BY row_seq DESC
                    ) AS rn
                    FROM rule_entries
                ) sub
                WHERE rn = 1
                ORDER BY row_seq
            """).fetchall()
        return [RuleEntry.model_validate_json(row[0]) for row in rows]

    def get_active(self) -> list[RuleEntry]:
        """Return only entries whose current status is ``ACTIVE``.

        Returns:
            List of active :class:`RuleEntry` objects.
        """
        return [e for e in self.get_all() if e.status == RuleStatus.ACTIVE]

    def get_family(self, rule_family_id: UUID) -> list[RuleEntry]:
        """Return all versions sharing the given ``rule_family_id``.

        Returns one entry per ``rule_id`` (latest state of each), ordered by
        ascending ``version``.

        Args:
            rule_family_id: Family UUID to filter by.

        Returns:
            Ordered list of :class:`RuleEntry` objects in the family.
        """
        all_entries = self.get_all()
        family = [e for e in all_entries if e.rule_family_id == rule_family_id]
        return sorted(family, key=lambda e: e.version)

    def get_supersession_links(
        self, rule_id: UUID | None = None
    ) -> list[SupersessionLink]:
        """Return persisted :class:`SupersessionLink` records in insertion order.

        Args:
            rule_id: If provided, filter to links where *rule_id* appears as
                either ``old_rule_id`` or ``new_rule_id``.

        Returns:
            List of :class:`SupersessionLink` objects.
        """
        with duckdb.connect(str(self._db_path)) as con:
            if rule_id is None:
                rows = con.execute(
                    "SELECT payload FROM supersession_links ORDER BY row_seq"
                ).fetchall()
            else:
                rid = str(rule_id)
                rows = con.execute(
                    "SELECT payload FROM supersession_links "
                    "WHERE old_rule_id = ? OR new_rule_id = ? ORDER BY row_seq",
                    [rid, rid],
                ).fetchall()
        return [SupersessionLink.model_validate_json(row[0]) for row in rows]

    def count(self) -> int:
        """Total number of distinct rule IDs in the store (all statuses).

        Returns:
            Integer count of distinct ``rule_id`` values.
        """
        with duckdb.connect(str(self._db_path)) as con:
            result = con.execute(
                "SELECT COUNT(DISTINCT rule_id) FROM rule_entries"
            ).fetchone()
        return int(result[0]) if result else 0

    def count_active(self) -> int:
        """Number of rules whose current status is ``ACTIVE``.

        Returns:
            Integer count of active rule IDs.
        """
        return len(self.get_active())

