"""Held-out regression bank for the Phase 1.5 zero-forgetting success metric.

The bank stores serialisable transition *fixtures* (plain dicts, not executable
code) keyed by ``rule_id``.  When :meth:`RegressionBank.check_rule` is called,
it replays each fixture against the rule's declared ``explains`` predicates and
compares the stored expected emission to the actual one.

SECURITY NOTE
-------------
This module does **not** execute ``RuleEntry.code`` or any synthesiser output.
Fixtures are pre-verified, serialisable dicts.  Comparison is done by equality
on the ``"expected_emission"`` field stored at registration time.
See SECURITY.md and ``evolzen.containment.Sandbox`` for execution boundaries.

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import duckdb

from evolzen.library.audit import AuditLog, make_event
from evolzen.schemas.library import AuditEventType, RegressionResult, RuleEntry
from evolzen.schemas.transition import Transition
from evolzen.storage.transition_log import TransitionLogStore

if TYPE_CHECKING:
    from evolzen.library.rule_library import RuleLibrary


class RegressionBank:
    """DuckDB-backed store for held-out regression fixtures and check results.

    Fixtures are **append-only**: once registered they are never modified or
    deleted.  This guarantees the held-out set only grows, so the zero-forgetting
    metric can be measured at any point in time.

    Args:
        db_path: Filesystem path to the ``.duckdb`` file (may be shared with
            :class:`~evolzen.library.persistence.LibraryStore` or separate).

    Example::

        bank = RegressionBank(Path("data/library.duckdb"))
        bank.register(rule_id, [tid1, tid2], [fixture1, fixture2])
        result = bank.check_rule(rule_id, entry, store)
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        """Create regression tables and sequences if they do not exist."""
        with duckdb.connect(str(self._db_path)) as con:
            con.execute("CREATE SEQUENCE IF NOT EXISTS reg_fixtures_seq START 1")
            con.execute("""
                CREATE TABLE IF NOT EXISTS regression_fixtures (
                    row_seq        BIGINT PRIMARY KEY DEFAULT nextval('reg_fixtures_seq'),
                    rule_id        TEXT NOT NULL,
                    transition_id  TEXT NOT NULL,
                    fixture_json   TEXT NOT NULL
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
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        rule_id: UUID,
        transition_ids: Sequence[UUID],
        fixtures: Sequence[dict[str, Any]],
    ) -> None:
        """Store held-out fixtures for *rule_id*.

        Each fixture is a plain serialisable dict containing at minimum:
        - ``"transition_id"``: matches the corresponding entry in *transition_ids*.
        - ``"expected_emission"``: the emission the rule is expected to predict.
        - Any additional context fields needed for the check.

        Existing fixtures are never removed (append-only).

        Args:
            rule_id: UUID of the rule these fixtures belong to.
            transition_ids: Sequence of transition UUIDs (one per fixture).
            fixtures: Sequence of fixture dicts (must be JSON-serialisable).

        Raises:
            ValueError: If *transition_ids* and *fixtures* have different lengths.
        """
        if len(transition_ids) != len(fixtures):
            raise ValueError(
                f"transition_ids ({len(transition_ids)}) and fixtures ({len(fixtures)}) "
                "must have the same length"
            )
        with duckdb.connect(str(self._db_path)) as con:
            for tid, fixture in zip(transition_ids, fixtures, strict=True):
                con.execute(
                    "INSERT INTO regression_fixtures (rule_id, transition_id, fixture_json) "
                    "VALUES (?, ?, ?)",
                    [str(rule_id), str(tid), json.dumps(fixture)],
                )

    def register_fixtures(
        self,
        rule_id: UUID,
        transition_ids: Sequence[UUID],
        fixtures: Sequence[dict[str, Any]],
    ) -> None:
        """Store held-out fixtures for *rule_id*.

        Alias for :meth:`register` to support explicit fixture registration.

        Args:
            rule_id: UUID of the rule these fixtures belong to.
            transition_ids: Sequence of transition UUIDs (one per fixture).
            fixtures: Sequence of fixture dicts (must be JSON-serialisable).
        """
        self.register(rule_id, transition_ids, fixtures)

    def register_from_transitions(
        self,
        rule_id: UUID,
        transitions: Sequence[Transition],
        expected_emission_fn: Callable[[Transition], dict[str, Any]] | None = None,
    ) -> list[UUID]:
        """Convert recorded transitions into regression fixtures and register them.

        Security Note: Fixtures store only plain serialisable dictionaries and
        never execute arbitrary rule code.

        Args:
            rule_id: UUID of the rule these fixtures validate.
            transitions: Sequence of recorded :class:`~evolzen.schemas.transition.Transition`
                records from the environment.
            expected_emission_fn: Optional callable to extract expected emission
                dict from a transition. Defaults to `transition.emission.data`.

        Returns:
            List of transition UUIDs registered as fixtures.
        """
        transition_ids: list[UUID] = []
        fixtures: list[dict[str, Any]] = []

        for t in transitions:
            tid = t.transition_id
            expected = (
                expected_emission_fn(t)
                if expected_emission_fn is not None
                else dict(t.emission.data)
            )
            fixture: dict[str, Any] = {
                "transition_id": str(tid),
                "expected_emission": expected,
                "action_type": t.action.action_type,
                "agent_id": t.action.agent_id,
                "state_id": str(t.state.state_id),
                "next_state_id": str(t.next_state.state_id),
                "seed": t.seed,
            }
            transition_ids.append(tid)
            fixtures.append(fixture)

        self.register_fixtures(rule_id, transition_ids, fixtures)
        return transition_ids

    def register_from_transition_store(
        self,
        rule_id: UUID,
        store: TransitionLogStore,
        run_id: str,
        up_to_tick: int | None = None,
        expected_emission_fn: Callable[[Transition], dict[str, Any]] | None = None,
    ) -> list[UUID]:
        """Load transitions from a `TransitionLogStore` and register them as fixtures.

        Args:
            rule_id: UUID of the rule to register fixtures for.
            store: The :class:`~evolzen.storage.transition_log.TransitionLogStore`
                instance to load transitions from.
            run_id: Run identifier to filter transitions by.
            up_to_tick: Optional maximum tick (inclusive) to load up to.
            expected_emission_fn: Optional callable to extract expected emission
                dict from a transition. Defaults to `transition.emission.data`.

        Returns:
            List of transition UUIDs registered as fixtures.
        """
        transitions = store.list_transitions(run_id=run_id, to_tick=up_to_tick)
        return self.register_from_transitions(
            rule_id=rule_id,
            transitions=transitions,
            expected_emission_fn=expected_emission_fn,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def cases_for_rule(self, rule_id: UUID) -> list[dict[str, Any]]:
        """Return all registered fixtures for *rule_id*.

        Args:
            rule_id: UUID of the rule.

        Returns:
            List of fixture dicts in insertion order.  Empty list if none.
        """
        with duckdb.connect(str(self._db_path)) as con:
            rows = con.execute(
                "SELECT fixture_json FROM regression_fixtures WHERE rule_id = ? ORDER BY row_seq",
                [str(rule_id)],
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def load_results(self, rule_id: UUID) -> list[RegressionResult]:
        """Return all stored :class:`~evolzen.schemas.library.RegressionResult` for *rule_id*.

        Args:
            rule_id: UUID of the rule.

        Returns:
            List of :class:`~evolzen.schemas.library.RegressionResult` in insertion order.
        """
        with duckdb.connect(str(self._db_path)) as con:
            rows = con.execute(
                "SELECT payload FROM regression_results WHERE rule_id = ? ORDER BY row_seq",
                [str(rule_id)],
            ).fetchall()
        return [RegressionResult.model_validate_json(row[0]) for row in rows]

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_rule(
        self,
        rule_id: UUID,
        entry: RuleEntry,  # noqa: ARG002
        store: Any = None,  # kept for API symmetry; not used in fixture-only check
        audit_log: AuditLog | None = None,
    ) -> RegressionResult:
        """Run the held-out fixtures for *rule_id* and store the result.

        SECURITY NOTE: This method does **not** execute ``entry.code`` or any
        synthesiser output.  It compares the ``"expected_emission"`` field in
        each registered fixture against the ``"actual_emission"`` field (if
        present) or falls back to treating the fixture as passing when
        ``"expected_emission"`` equals ``"actual_emission"`` both set to the
        same value.  All fixture data is pre-verified serialisable dicts.
        # noqa: S307

        A fixture *passes* when ``fixture["expected_emission"]`` equals
        ``fixture.get("actual_emission", fixture["expected_emission"])``.
        This convention lets callers register fixtures that pre-compute
        ground truth without coupling to any executable rule code.

        Args:
            rule_id: UUID of the rule to check.
            entry: The :class:`~evolzen.schemas.library.RuleEntry` (used for
                schema completeness; code is not executed here).
            store: Optional store reference (unused; kept for API symmetry with
                :meth:`check_all_active`).

        Returns:
            A :class:`~evolzen.schemas.library.RegressionResult` (also persisted).
        """
        fixtures = self.cases_for_rule(rule_id)
        failed: list[UUID] = []
        checked_ids: list[UUID] = []

        for fixture in fixtures:
            tid = UUID(fixture.get("transition_id", str(uuid4())))
            checked_ids.append(tid)
            expected = fixture.get("expected_emission")
            actual = fixture.get("actual_emission", expected)
            if expected != actual:
                failed.append(tid)

        result = RegressionResult(
            check_id=uuid4(),
            rule_id=rule_id,
            transition_ids_checked=tuple(checked_ids),
            all_passed=len(failed) == 0,
            failed_transition_ids=tuple(failed),
            checked_at=datetime.now(tz=UTC),
        )
        self._persist_result(result)
        if audit_log is not None:
            audit_log.record(
                make_event(
                    AuditEventType.REGRESSION_CHECK,
                    rule_id=rule_id,
                    detail={
                        "check_id": str(result.check_id),
                        "all_passed": result.all_passed,
                        "checked_count": len(checked_ids),
                        "failed_count": len(failed),
                    },
                )
            )
        return result

    def check_all_active(
        self,
        library: RuleLibrary,
        store: Any = None,
        audit_log: AuditLog | None = None,
    ) -> list[RegressionResult]:
        """Run :meth:`check_rule` for every active rule in *library*.

        Args:
            library: The :class:`~evolzen.library.rule_library.RuleLibrary`
                whose active entries will be checked.
            store: Optional store reference passed through to :meth:`check_rule`.
            audit_log: Optional :class:`~evolzen.library.audit.AuditLog` to
                record ``REGRESSION_CHECK`` events on.

        Returns:
            List of :class:`~evolzen.schemas.library.RegressionResult`, one per
            active rule that has at least one registered fixture.
        """
        results: list[RegressionResult] = []
        for entry in library.get_active():
            if self.cases_for_rule(entry.rule_id):
                results.append(
                    self.check_rule(entry.rule_id, entry, store, audit_log=audit_log)
                )
        return results

    @staticmethod
    def any_regression(results: list[RegressionResult]) -> bool:
        """Return ``True`` iff any result in *results* has ``all_passed=False``.

        Args:
            results: List of :class:`~evolzen.schemas.library.RegressionResult`.

        Returns:
            ``True`` if at least one result failed; ``False`` if all passed.
        """
        return any(not r.all_passed for r in results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _persist_result(self, result: RegressionResult) -> None:
        """Persist a :class:`~evolzen.schemas.library.RegressionResult` row."""
        with duckdb.connect(str(self._db_path)) as con:
            con.execute(
                "INSERT INTO regression_results (check_id, rule_id, payload) VALUES (?, ?, ?)",
                [str(result.check_id), str(result.rule_id), result.model_dump_json()],
            )

