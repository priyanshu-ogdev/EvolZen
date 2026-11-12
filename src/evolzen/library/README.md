# evolzen.library — Phase 1.5

**Goal:** store verified rules and capability packages as immutable historical entries while
supporting explicit validity context and supersession when the world changes.

Full research design: [`docs/phases/1.5-library.md`](../../../docs/phases/1.5-library.md) and [`docs/subsystems/library/README.md`](../../../docs/subsystems/library/README.md).

## What's here

| File | Purpose |
|---|---|
| [`__init__.py`](__init__.py) | Public subsystem API exporting store, library orchestrator, validity predicates, audit log, and regression bank. |
| [`persistence.py`](persistence.py) | `LibraryStore` — append-only DuckDB persistence for `RuleEntry`, `SupersessionLink`, and `RegressionResult`. |
| [`rule_library.py`](rule_library.py) | `RuleLibrary` — spawn/route heuristic, `promote`, `supersede`, `deprecate`, and family/status queries. |
| [`validity.py`](validity.py) | `is_applicable`, `applicable_entries`, `needs_supersession`, `validate_supersession_reason`. |
| [`audit.py`](audit.py) | `AuditLog` and `make_event` — cross-platform file-locked append-only JSONL audit trail. |
| [`regression_bank.py`](regression_bank.py) | `RegressionBank` — append-only held-out transition fixtures and regression result persistence (no unsafe code execution). |

Shared Pydantic contracts live in [`src/evolzen/schemas/library.py`](../schemas/library.py), and subsystem configuration lives in `evolzen.config.LibrarySettings` / [`configs/library.yaml`](../../../configs/library.yaml).

**Depends on:** `evolzen.exploration.synthesizer` (`CandidateRule`), `evolzen.schemas.library`.
**Depended on by:** `evolzen.recognition` (`SparseMoELibrary` queries `RuleLibrary.get` and returns `RuleEntry`), `evolzen.containment` (Phase 2.2 promotion gate writes here under the same verification standard).
