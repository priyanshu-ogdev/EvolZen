"""Phase 1.1 / Phase 1.5 — Transition log and world-state storage.

DuckDB-backed by default: embedded, zero-ops, schema-versioned, JSON-only (no pickle),
and hash-chained for integrity checks. Swap `TransitionLogStore` for a different backend
without changing callers that depend on `append` / `count` or the snapshot/growth methods.

Design authority: docs/phases/1.1-environment.md, ADR 0004
(docs/adr/0004-persistent-growing-world.md), and ADR 0005
(docs/adr/0005-transition-semantics-and-dual-track-evaluation.md).
Citations: Tycho (arXiv:2607.28287) for complete transition logging enabling active
environment identification. Multi-run rig-scale persistence throughput and long-horizon
retention remain empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb

from evolzen.schemas.transition import Action, Emission, ExogenousInput, State, Transition
from evolzen.schemas.world import (
    BranchRecord,
    GrowthAttribution,
    GrowthCategory,
    GrowthEvent,
    WorldSnapshot,
)

if TYPE_CHECKING:
    from types import TracebackType

SCHEMA_VERSION = 1
_GENESIS_HASH = "0" * 64


def _transition_digest(
    prev_hash: str,
    transition_id: str,
    run_id: str,
    branch_id: str,
    tick: int,
    seed: int,
    state_json: str,
    action_json: str,
    exogenous_json: str,
    emission_json: str,
    next_state_json: str,
) -> str:
    payload = json.dumps(
        [
            prev_hash,
            transition_id,
            run_id,
            branch_id,
            tick,
            seed,
            state_json,
            action_json,
            exogenous_json,
            emission_json,
            next_state_json,
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TransitionLogStore:
    """Append-only DuckDB store for transitions, snapshots, growth events, and branches.

    Every record is serialized strictly as JSON (never pickle). Appends run inside
    explicit DuckDB transactions and extend a per-store SHA-256 hash chain.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection = duckdb.connect(str(self._db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("BEGIN TRANSACTION")
        try:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    schema_version INTEGER PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transitions (
                    seq_no BIGINT NOT NULL,
                    transition_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR NOT NULL,
                    branch_id VARCHAR NOT NULL,
                    tick BIGINT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    seed BIGINT NOT NULL,
                    state_json VARCHAR NOT NULL,
                    action_json VARCHAR NOT NULL,
                    exogenous_json VARCHAR NOT NULL,
                    emission_json VARCHAR NOT NULL,
                    next_state_json VARCHAR NOT NULL,
                    prev_hash VARCHAR NOT NULL,
                    entry_hash VARCHAR NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR NOT NULL,
                    branch_id VARCHAR NOT NULL,
                    tick BIGINT NOT NULL,
                    parent_snapshot_id VARCHAR,
                    world_version VARCHAR NOT NULL,
                    snapshot_json VARCHAR NOT NULL,
                    snapshot_hash VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS growth_events (
                    seq_no BIGINT NOT NULL,
                    event_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR NOT NULL,
                    branch_id VARCHAR NOT NULL,
                    tick BIGINT NOT NULL,
                    category VARCHAR NOT NULL,
                    attribution VARCHAR NOT NULL,
                    actor_id VARCHAR NOT NULL,
                    entity_id VARCHAR NOT NULL,
                    summary VARCHAR NOT NULL,
                    transition_id VARCHAR NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS branches (
                    branch_id VARCHAR NOT NULL,
                    run_id VARCHAR NOT NULL,
                    parent_branch_id VARCHAR NOT NULL,
                    fork_tick BIGINT NOT NULL,
                    fork_snapshot_id VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (run_id, branch_id)
                )
                """
            )
            existing_version = self._conn.execute(
                "SELECT schema_version FROM schema_meta WHERE schema_version = ?",
                [SCHEMA_VERSION],
            ).fetchone()
            if existing_version is None:
                self._conn.execute(
                    "INSERT INTO schema_meta (schema_version, created_at) VALUES (?, ?)",
                    [SCHEMA_VERSION, datetime.now(UTC).replace(tzinfo=None)],
                )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def close(self) -> None:
        """Close the underlying DuckDB connection."""
        self._conn.close()

    def __enter__(self) -> TransitionLogStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def schema_version(self) -> int:
        """Return the active persisted schema version."""
        row = self._conn.execute("SELECT MAX(schema_version) FROM schema_meta").fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def append(
        self,
        transition: Transition,
        *,
        run_id: str | None = None,
        branch_id: str | None = None,
    ) -> None:
        """Persist one transition atomically with hash-chain linkage."""
        resolved_run = run_id or str(transition.state.data.get("run_id", "default-run"))
        resolved_branch = branch_id or str(transition.state.data.get("branch_id", "main"))
        tick = int(transition.state.data.get("tick", transition.exogenous_input.tick))
        state_json = transition.state.model_dump_json()
        action_json = transition.action.model_dump_json()
        exogenous_json = transition.exogenous_input.model_dump_json()
        emission_json = transition.emission.model_dump_json()
        next_state_json = transition.next_state.model_dump_json()
        transition_id = str(transition.transition_id)
        ts = transition.timestamp.astimezone(UTC).replace(tzinfo=None)

        self._conn.execute("BEGIN TRANSACTION")
        try:
            last = self._conn.execute(
                "SELECT seq_no, entry_hash FROM transitions ORDER BY seq_no DESC LIMIT 1"
            ).fetchone()
            seq_no = int(last[0]) + 1 if last is not None else 1
            prev_hash = str(last[1]) if last is not None else _GENESIS_HASH
            entry_hash = _transition_digest(
                prev_hash,
                transition_id,
                resolved_run,
                resolved_branch,
                tick,
                transition.seed,
                state_json,
                action_json,
                exogenous_json,
                emission_json,
                next_state_json,
            )
            self._conn.execute(
                """
                INSERT INTO transitions (
                    seq_no, transition_id, run_id, branch_id, tick, timestamp, seed,
                    state_json, action_json, exogenous_json, emission_json, next_state_json,
                    prev_hash, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    seq_no,
                    transition_id,
                    resolved_run,
                    resolved_branch,
                    tick,
                    ts,
                    transition.seed,
                    state_json,
                    action_json,
                    exogenous_json,
                    emission_json,
                    next_state_json,
                    prev_hash,
                    entry_hash,
                ],
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def count(self, *, run_id: str | None = None, branch_id: str | None = None) -> int:
        """Number of transitions currently stored, optionally filtered by run/branch."""
        clauses: list[str] = []
        params: list[Any] = []
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if branch_id is not None:
            clauses.append("branch_id = ?")
            params.append(branch_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self._conn.execute(f"SELECT COUNT(*) FROM transitions{where}", params).fetchone()
        return int(row[0]) if row is not None else 0

    def list_transitions(
        self,
        *,
        run_id: str | None = None,
        branch_id: str | None = None,
        from_tick: int | None = None,
        to_tick: int | None = None,
    ) -> list[Transition]:
        """Load transitions in append order, optionally filtered by run/branch/ticks."""
        clauses: list[str] = []
        params: list[Any] = []
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if branch_id is not None:
            clauses.append("branch_id = ?")
            params.append(branch_id)
        if from_tick is not None:
            clauses.append("tick >= ?")
            params.append(from_tick)
        if to_tick is not None:
            clauses.append("tick <= ?")
            params.append(to_tick)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT transition_id, timestamp, seed, state_json, action_json,
                   exogenous_json, emission_json, next_state_json
            FROM transitions{where}
            ORDER BY seq_no ASC
            """,
            params,
        ).fetchall()
        results: list[Transition] = []
        for row in rows:
            ts_val = row[1]
            if isinstance(ts_val, datetime) and ts_val.tzinfo is None:
                ts_val = ts_val.replace(tzinfo=UTC)
            results.append(
                Transition(
                    transition_id=row[0],
                    timestamp=ts_val,
                    seed=int(row[2]),
                    state=State.model_validate_json(row[3]),
                    action=Action.model_validate_json(row[4]),
                    exogenous_input=ExogenousInput.model_validate_json(row[5]),
                    emission=Emission.model_validate_json(row[6]),
                    next_state=State.model_validate_json(row[7]),
                )
            )
        return results

    def verify_integrity(self) -> bool:
        """Verify the SHA-256 hash chain across all persisted transitions."""
        rows = self._conn.execute(
            """
            SELECT seq_no, transition_id, run_id, branch_id, tick, seed,
                   state_json, action_json, exogenous_json, emission_json, next_state_json,
                   prev_hash, entry_hash
            FROM transitions
            ORDER BY seq_no ASC
            """
        ).fetchall()
        expected_prev = _GENESIS_HASH
        for row in rows:
            if row[11] != expected_prev:
                return False
            recomputed = _transition_digest(
                str(row[11]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                int(row[4]),
                int(row[5]),
                str(row[6]),
                str(row[7]),
                str(row[8]),
                str(row[9]),
                str(row[10]),
            )
            if recomputed != row[12]:
                return False
            expected_prev = str(row[12])
        return True

    def _insert_snapshot(self, snapshot: WorldSnapshot) -> None:
        payload = snapshot.model_dump_json()
        self._conn.execute(
            """
            INSERT INTO snapshots (
                snapshot_id, run_id, branch_id, tick, parent_snapshot_id,
                world_version, snapshot_json, snapshot_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                snapshot.snapshot_id,
                snapshot.run_id,
                snapshot.branch_id,
                snapshot.tick,
                snapshot.parent_snapshot_id,
                snapshot.world_version,
                payload,
                snapshot.state_hash,
                datetime.now(UTC).replace(tzinfo=None),
            ],
        )

    def _insert_branch(self, branch: BranchRecord) -> None:
        self._conn.execute(
            """
            INSERT INTO branches (
                branch_id, run_id, parent_branch_id, fork_tick, fork_snapshot_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                branch.branch_id,
                branch.run_id,
                branch.parent_branch_id,
                branch.fork_tick,
                branch.fork_snapshot_id,
                datetime.now(UTC).replace(tzinfo=None),
            ],
        )

    def save_snapshot(self, snapshot: WorldSnapshot) -> None:
        """Persist an immutable `WorldSnapshot` record atomically."""
        self._conn.execute("BEGIN TRANSACTION")
        try:
            self._insert_snapshot(snapshot)
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def save_snapshot_and_branch(self, snapshot: WorldSnapshot, branch: BranchRecord) -> None:
        """Persist a fork `WorldSnapshot` and its `BranchRecord` in one atomic transaction."""
        self._conn.execute("BEGIN TRANSACTION")
        try:
            self._insert_snapshot(snapshot)
            self._insert_branch(branch)
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def load_snapshot(self, snapshot_id: str) -> WorldSnapshot:
        """Load and validate a persisted `WorldSnapshot` by ID."""
        row = self._conn.execute(
            "SELECT snapshot_json, snapshot_hash FROM snapshots WHERE snapshot_id = ?",
            [snapshot_id],
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown snapshot_id: {snapshot_id}")
        snapshot = WorldSnapshot.model_validate_json(row[0])
        if snapshot.state.state_hash() != row[1]:
            raise ValueError(f"Snapshot hash mismatch for {snapshot_id}")
        return snapshot

    def latest_snapshot(
        self,
        run_id: str,
        branch_id: str = "main",
        *,
        max_tick: int | None = None,
    ) -> WorldSnapshot | None:
        """Return the latest snapshot for `(run_id, branch_id)` at or below `max_tick`."""
        clauses = ["run_id = ?", "branch_id = ?"]
        params: list[Any] = [run_id, branch_id]
        if max_tick is not None:
            clauses.append("tick <= ?")
            params.append(max_tick)
        row = self._conn.execute(
            f"""
            SELECT snapshot_json, snapshot_hash
            FROM snapshots
            WHERE {' AND '.join(clauses)}
            ORDER BY tick DESC, rowid DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        if row is None:
            return None
        snapshot = WorldSnapshot.model_validate_json(row[0])
        if snapshot.state.state_hash() != row[1]:
            raise ValueError(f"Snapshot hash mismatch for {snapshot.snapshot_id}")
        return snapshot

    def append_growth_events(
        self,
        events: list[GrowthEvent] | tuple[GrowthEvent, ...],
        *,
        run_id: str,
        branch_id: str = "main",
    ) -> None:
        """Persist attributable world-growth events atomically."""
        if not events:
            return
        self._conn.execute("BEGIN TRANSACTION")
        try:
            row = self._conn.execute("SELECT COALESCE(MAX(seq_no), 0) FROM growth_events").fetchone()
            seq = int(row[0]) if row is not None else 0
            for event in events:
                seq += 1
                self._conn.execute(
                    """
                    INSERT INTO growth_events (
                        seq_no, event_id, run_id, branch_id, tick, category,
                        attribution, actor_id, entity_id, summary, transition_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        seq,
                        event.event_id,
                        run_id,
                        branch_id,
                        event.tick,
                        event.category.value,
                        event.attribution.value,
                        event.actor_id,
                        event.entity_id,
                        event.summary,
                        event.transition_id,
                    ],
                )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def list_growth_events(
        self,
        *,
        run_id: str | None = None,
        branch_id: str | None = None,
    ) -> list[GrowthEvent]:
        """Retrieve growth events in append order."""
        clauses: list[str] = []
        params: list[Any] = []
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if branch_id is not None:
            clauses.append("branch_id = ?")
            params.append(branch_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT event_id, tick, category, attribution, actor_id, entity_id, summary, transition_id
            FROM growth_events{where}
            ORDER BY seq_no ASC
            """,
            params,
        ).fetchall()
        return [
            GrowthEvent(
                event_id=row[0],
                tick=int(row[1]),
                category=GrowthCategory(row[2]),
                attribution=GrowthAttribution(row[3]),
                actor_id=row[4],
                entity_id=row[5],
                summary=row[6],
                transition_id=row[7],
            )
            for row in rows
        ]

    def record_branch(self, branch: BranchRecord) -> None:
        """Persist branch lineage metadata atomically."""
        self._conn.execute("BEGIN TRANSACTION")
        try:
            self._insert_branch(branch)
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def list_branches(self, *, run_id: str | None = None) -> list[BranchRecord]:
        """List recorded world branches."""
        where = " WHERE run_id = ?" if run_id is not None else ""
        params = [run_id] if run_id is not None else []
        rows = self._conn.execute(
            f"""
            SELECT branch_id, run_id, parent_branch_id, fork_tick, fork_snapshot_id
            FROM branches{where}
            ORDER BY rowid ASC
            """,
            params,
        ).fetchall()
        return [
            BranchRecord(
                branch_id=row[0],
                run_id=row[1],
                parent_branch_id=row[2],
                fork_tick=int(row[3]),
                fork_snapshot_id=row[4],
            )
            for row in rows
        ]
