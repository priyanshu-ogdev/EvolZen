# ADR 0007: DuckDB append-only rule store and JSONL audit log for `evolzen.library`

**Status:** Accepted

## Context

Phase 1.5 (`evolzen.library`) requires immutable historical rule entries, explicit supersession and deprecation links, a held-out regression bank, and an auditable event log covering spawn, route, promotion, supersession, and deprecation decisions.

Two storage alternatives were considered:

1. **Plain JSONL files only** for both rules and audit events. Simple to append, but family queries (`get_family`), latest-state deduplication per `rule_id`, and querying regression fixtures/results across rounds would require full-file scans in Python.
2. **SQLite** for rules + regression bank. Available in stdlib, but the repository's existing storage convention (`evolzen.storage.transition_log` and base dependencies in `pyproject.toml`) already standardises on **DuckDB** (`duckdb>=1.1`).

## Decision

`evolzen.library` uses:

- **DuckDB** (`LibraryStore` and `RegressionBank`) with explicit `CREATE SEQUENCE` ordering (`row_seq`) and append-only `INSERT` semantics. Rows are never updated or deleted in place; `get_by_id`, `get_all`, `get_active`, and `get_family` project the latest `row_seq` per `rule_id` via `ROW_NUMBER() OVER (PARTITION BY rule_id ORDER BY row_seq DESC)` while deserialising frozen Pydantic models (`evolzen.schemas.library`).
- **Append-only JSONL** (`AuditLog`) with cross-platform file locking (`msvcrt` on Windows, `fcntl` on POSIX) so audit records remain human-inspectable, streamable, and independent of DuckDB transactions.

## Consequences

- Zero new dependencies are introduced (DuckDB is already a base dependency).
- Full historical rule states remain queryable in `rule_entries` even after supersession or deprecation.
- Using short-lived per-call `duckdb.connect(...)` connections aligns with `evolzen.storage.transition_log` and avoids holding long-lived file locks across processes, at the cost of small per-call connection overhead.
- `RegressionBank.check_rule` stays strictly separated from executing `RuleEntry.code`; sandboxed replay remains the responsibility of Phase 2.2 (`evolzen.containment.Sandbox`).

