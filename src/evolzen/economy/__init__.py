"""Phase 1.3 — Economy & Knowledge Layer.

Includes Hayekian scarcity pricing, continuous double auction order books,
falsifiable natural-language manuals with real-data provenance floors,
and macroscopic economic health / specialization metrics.

Design authority: `docs/phases/1.3-economy.md`.
"""
from evolzen.economy.manuals import (
    KnowledgeTransferReport,
    ManualStore,
    RealDataFloorViolation,
)
from evolzen.economy.market import (
    Market,
    Order,
    OrderBook,
    OrderSide,
    TradeSettlement,
)
from evolzen.economy.metrics import (
    EconomicHealthReport,
    compute_gini_coefficient,
    compute_shock_recovery,
    compute_specialization_index,
    compute_wealth_gini,
    evaluate_economic_health,
    measure_shock_recovery,
    verify_currency_conservation,
)

__all__ = [
    # Market & Order Book
    "Market",
    "Order",
    "OrderBook",
    "OrderSide",
    "TradeSettlement",
    # Manuals & Provenance
    "ManualStore",
    "RealDataFloorViolation",
    "KnowledgeTransferReport",
    # Economic Metrics
    "EconomicHealthReport",
    "compute_gini_coefficient",
    "compute_shock_recovery",
    "compute_specialization_index",
    "compute_wealth_gini",
    "evaluate_economic_health",
    "measure_shock_recovery",
    "verify_currency_conservation",
]
