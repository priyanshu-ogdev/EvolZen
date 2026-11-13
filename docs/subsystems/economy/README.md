# Economy integration

Authority: [Phase 1.3](../../phases/1.3-economy.md).
Source package: `src/evolzen/economy/`.

Own resource transfer, teaching time costs, institutions, manuals and data provenance.
Greed versus gluttony requires a distinction between retaining and consuming assets; envy uses
permitted relative information, not hidden balances. Teaching is a transfer of evidence-linked
advice, not an automatic grant of resources or competence. Full manuals-to-lessons integration
is pending; the developmental baseline transfers only numerical context/skill estimates.
Do not treat synthetic family knowledge as externally sourced data.

Implemented Phase 1.3 components:
- `Market` & `OrderBook` (`market.py`): Integer currency balances, Hayekian dynamic scarcity pricing (`quote_price`), continuous double auction order matching with institutional fee withholding, `ActionType.TRADE` action construction, and `settle_in_world` preserving exact conservation invariants;
- `ManualStore` (`manuals.py`): Falsifiable natural-language manuals, revision lineages, automated real-data provenance floor calculations (`calculate_real_fraction`), generation corpus gating (`verify_generation_corpus`), and forward knowledge transfer measurement (`measure_knowledge_transfer`);
- `EconomicMetrics` (`metrics.py`): Gini inequality index, Herfindahl-Hirschman specialization index (HHI) and entropy, shock recovery resilience tracking, and macroscopic `EconomicHealthReport` evaluation;
- Canonical schemas: `ProvenanceSource` and `ProvenanceRecord` in `evolzen.schemas.manual`.

Open downstream verification:
- Empirical multi-generation benchmarks testing specialization emergence, manual revisions under induced falsification, and macro-resilience across 5 generations on target DGX/AGX hardware remain **untested**; success metrics are **unmeasured**.
