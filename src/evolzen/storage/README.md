# Storage foundation

| Module | Status and responsibility |
|---|---|
| `transition_log.py` | DuckDB-backed append-only `TransitionLogStore` (`SCHEMA_VERSION = 1`): schema-versioned tables (`transitions`, `snapshots`, `growth_events`, `branches`), atomic transactions, SHA-256 hash chaining, and JSON-only Pydantic serialization. |

Open hardening item: `_init_schema()` currently executes `CREATE TABLE IF NOT EXISTS` in a transaction without validating or migrating mismatched `schema_version` values on open; an explicit version-mismatch guard and migration hook remain planned.

No executable pickle checkpoints are loaded or persisted here.
