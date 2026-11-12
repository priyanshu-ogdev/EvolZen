"""Sparse mixture-of-experts restructuring of the verified-rule library (Phase 2.3).

Only a handful of library entries are active per query — efficient, and a good match for the
DGX Spark's memory-bandwidth-bound profile. This wraps
`evolzen.library.rule_library.RuleLibrary`, adding routing rather than replacing the underlying
verified-rule storage.
"""
from __future__ import annotations

from typing import Protocol

from evolzen.library.rule_library import RuleLibrary
from evolzen.schemas.library import RuleEntry


class ExpertRouter(Protocol):
    """Protocol for the routing function selecting which library entries are "active"."""

    def route(self, query_embedding: list[float], top_k: int) -> list[str]:
        """Return the rule_ids of the top_k most relevant library entries."""
        ...


class SparseMoELibrary:
    """Routes queries to a small active subset of a RuleLibrary's entries."""

    def __init__(self, rule_library: RuleLibrary, router: ExpertRouter, top_k: int = 4) -> None:
        self._rule_library = rule_library
        self._router = router
        self._top_k = top_k

    def active_entries(self, query_embedding: list[float]) -> list[RuleEntry]:
        rule_ids = self._router.route(query_embedding, self._top_k)
        entries = [self._rule_library.get(rid) for rid in rule_ids]
        return [e for e in entries if e is not None]
