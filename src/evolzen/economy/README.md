# evolzen.economy — Phase 1.3

**Goal:** introduce specialization and inter-agent knowledge transfer without letting that
transfer become a closed, collapsing loop.

Full research design: [`docs/phases/1.3-economy.md`](../../../docs/phases/1.3-economy.md).

## What's here

| File | Purpose |
|---|---|
| [`market.py`](market.py) | `Market`, `OrderBook`, `Order`, `TradeSettlement` — integer balances, Hayekian dynamic scarcity pricing, double auction clearing, and state settlement. |
| [`manuals.py`](manuals.py) | `ManualStore` — falsifiable, revisable natural-language knowledge transfer with provenance records, real-data floor enforcement, and capability transfer measurement. |
| [`metrics.py`](metrics.py) | `EconomicHealthReport`, `compute_gini_coefficient`, `compute_specialization_index`, `compute_shock_recovery`, and `evaluate_economic_health`. |

## How to build this

1. Scope `Market` to the persistent world's resource, contract, and institution model; record
   durable institutions and norms as world-growth events.
2. Wire the provenance-floor check in from the start — call it before every generation's training
   pass starts, and label human-authored, external, simulator, and model-generated sources
   separately.
3. Use the A6000/DGX Spark to generate manuals for hard/novel situations only as a declared
   experimental condition; have cheaper local models consume them under matched exposure and
   measure transfer rather than importing a vendor-reported benefit as a guarantee.

**Success metric:** two distinct specialization patterns and at least one durable institution or
norm emerge across five generations; manuals are revised after induced falsifications; the
configured provenance floor remains satisfied; and population/world diversity does not collapse.

**Depends on:** `evolzen.schemas.manual`.
**Depended on by:** `evolzen.recognition` (manuals are a fast, cheap memory tier consulted
before the JEPA + wake-sleep model).
