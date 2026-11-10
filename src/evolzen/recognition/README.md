# evolzen.recognition — Phase 2.3

**Goal:** test whether a proposed JEPA-style state representation plus DreamCoder-style
wake-sleep operator learning improves fresh-world adaptation beyond simpler baselines. This is a
research hypothesis, not an established or pre-declared novel contribution.

Full research design: [`docs/phases/2.3-recognition.md`](../../../docs/phases/2.3-recognition.md).

## What's here

| File | Purpose |
|---|---|
| [`jepa.py`](jepa.py) | `JEPAEncoder` protocol — candidate continuous state representation (LeJEPA, arXiv:2511.08544). |
| [`wake_sleep.py`](wake_sleep.py) | `WakeSleepLearner` — discrete "how states transform" (DreamCoder, PLDI 2021). |
| [`moe_library.py`](moe_library.py) | `SparseMoELibrary` — restructures `evolzen.library.RuleLibrary` for efficient sparse routing. |
| [`embedding_router.py`](embedding_router.py) | `EmbeddingRouter` — the one **complete** reference implementation in this subsystem: concrete FAISS + sentence-transformers routing. |

## How to build this

1. Build a simple representation baseline, then the JEPA encoder and wake-sleep learner separately.
   Confirm each works in isolation on a clean, discrete case before attempting the fusion. Any
   similar 2026 preprint is a hypothesis source, not validation of this implementation.
2. Wire `embedding_router.py::EmbeddingRouter` against `evolzen.library` as it's populated by
   Phase 1.4/1.5 — this component is already fully specified; start here to get something
   real running quickly.
3. Layer manuals (`evolzen.economy.manuals`) above both the frozen library and the JEPA/wake-
   sleep components as a fast, cheap third memory tier consulted first.
4. Evaluate with the full ablation matrix: with/without recognition model x with/without manual
   layer x JEPA-only / wake-sleep-only / combined.

**Success metric:** the recognition condition improves adaptation latency or success on at least
one pre-registered persistent-world or fresh-world track without unacceptable regression on the
other. All ablation cells, including null or negative results, are reported.

**Depends on:** `evolzen.library`, `evolzen.economy.manuals`.
**Depended on by:** `evolzen.predictor` (the planner is guided by this model),
`evolzen.evaluation` (the ablation matrix is scored here).
