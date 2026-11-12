# Storage foundation

| Module | Status and responsibility |
|---|---|
| `transition_log.py` | DuckDB-backed append-only `TransitionLogStore`: schema-versioned tables (`transitions`, `snapshots`, `growth_events`, `branches`), atomic transactions, SHA-256 hash chaining, and JSON-only Pydantic serialization. |

No executable pickle checkpoints are loaded or persisted here.
