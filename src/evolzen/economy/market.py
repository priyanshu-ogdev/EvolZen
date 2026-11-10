"""Specialization and market dynamics (Phase 1.3).

Scoped to whatever Phase 1.1 domain is chosen — currency, specialization incentives, and
price/scarcity dynamics. See arXiv:2606.02859 ("Economy of Minds") for a closely related
result worth reading against this module's eventual design.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Market:
    """Tracks agent balances and simple supply/demand pricing for one resource pool."""

    balances: dict[str, float] = field(default_factory=dict)
    prices: dict[str, float] = field(default_factory=dict)

    def balance_of(self, agent_id: str) -> float:
        return self.balances.get(agent_id, 0.0)

    def transfer(self, from_agent: str, to_agent: str, amount: float) -> None:
        """Move `amount` from one agent's balance to another's.

        Phase 0 stub keeps the bookkeeping trivial and synchronous; Phase 1.3 should decide
        whether transfers need to be logged as Transitions (probably yes, for verifiability).
        """
        if self.balance_of(from_agent) < amount:
            raise ValueError(f"{from_agent} cannot transfer {amount}: insufficient balance")
        self.balances[from_agent] = self.balance_of(from_agent) - amount
        self.balances[to_agent] = self.balance_of(to_agent) + amount
