# Storage foundation

| Module | Status and responsibility |
|---|---|
| `transition_log.py` | Legacy DuckDB transition-store interface; append/count remain stubs. |
No mock run store is included. The production transition log remains an explicit Phase 1.1
implementation task; its interface is not silently replaced by a fixture or JSON artifact.
Never load executable pickle checkpoints here. The future implementation must define versioned
rows, atomic append, replay checks, recovery semantics and integrity/provenance before the
world runner is wired into this foundation.
