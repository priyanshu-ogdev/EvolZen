"""Phase 1.5 — Growing Rule Library.

Public surface of the ``evolzen.library`` subsystem.  Import from here rather
than from individual submodules.

Modules
-------
- :mod:`evolzen.library.persistence`   — DuckDB append-only store
- :mod:`evolzen.library.rule_library`  — :class:`RuleLibrary` orchestrator
- :mod:`evolzen.library.validity`      — Validity-context helpers
- :mod:`evolzen.library.audit`         — Append-only JSONL audit log
- :mod:`evolzen.library.regression_bank` — Held-out regression fixture bank
"""

from evolzen.library.audit import AuditLog, make_event
from evolzen.library.persistence import SCHEMA_VERSION, LibraryStore
from evolzen.library.regression_bank import RegressionBank
from evolzen.library.rule_library import RoutingConfidenceFn, RuleLibrary
from evolzen.library.validity import (
    applicable_entries,
    is_applicable,
    needs_supersession,
    validate_supersession_reason,
)

__all__ = [
    # Audit
    "AuditLog",
    "make_event",
    # Persistence
    "LibraryStore",
    "SCHEMA_VERSION",
    # Regression bank
    "RegressionBank",
    # Library orchestrator
    "RuleLibrary",
    "RoutingConfidenceFn",
    # Validity helpers
    "applicable_entries",
    "is_applicable",
    "needs_supersession",
    "validate_supersession_reason",
]
