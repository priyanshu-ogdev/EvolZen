"""Transition log storage (Phase 1.1 / Phase 1.5).

DuckDB-backed by default: embedded, zero-ops, and fast enough for the transition-log volumes
the Phase 1.1 domain (a small negotiation/market/code-with-tests environment, not a
datacenter-scale simulation) actually produces. Swap `TransitionLogStore` for a different
backend without touching any calling code, since callers only depend on this interface.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evolzen.schemas.transition import Transition


class TransitionLogStore:
    """Append-only store for verified transitions.

    Phase 1.1's success metric requires every stored transition to be independently
    re-derivable from its state and action; this store does not itself verify that property
    (that's `evolzen.exploration.verifier`'s job) — it only persists what it's given.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, transition: Transition) -> None:
        """Persist one verified transition.

        Phase 0 stub: real implementation opens a DuckDB connection and inserts the transition
        as a row (state/action/emission/next_state serialized as JSON columns). Left
        unimplemented deliberately — Phase 1.1 should decide the exact table schema alongside
        the chosen environment domain.
        """
        raise NotImplementedError(
            "Implement in Phase 1.1 alongside the chosen environment domain. "
            "See docs/phases/1.1-environment.md."
        )

    def count(self) -> int:
        """Number of transitions currently stored."""
        raise NotImplementedError("See TransitionLogStore.append.")
