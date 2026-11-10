# evolzen.evaluation — Phase 2.4-2.5

**Goal:** measure persistent-world growth and fresh-world adaptation, and produce a final report
where every claim traces to a measured result.

Full research design: [`docs/phases/2.4-2.5-evaluation.md`](../../../docs/phases/2.4-2.5-evaluation.md).

## What's here

| File | Purpose |
|---|---|
| [`procedural_env_gen.py`](procedural_env_gen.py) | `ProceduralEnvironmentGenerator` — produces persistent-world scenarios, held-out seeds, and held-out mechanic combinations. |
| [`rhae_scorer.py`](rhae_scorer.py) | Compatibility implementation name for the EvolZen Action Efficiency scorer; not automatically official ARC-AGI-3 RHAE. |
| [`report.py`](report.py) | `EvaluationReport` — a structured, no-free-text-headline-claim report. |

## How to build this

1. **Build both generators before running any "real" evaluation.** Persistent-world runs need
   seed-stratified longitudinal scenarios; fresh-world runs need held-out seeds and mechanic
   combinations. Record exposure, manual, replay, and seed history for every score.
2. Wire the EAE scorer to aggregate persistent-world and fresh-world results with `polars` across
   seed-stratified evaluation rounds.
3. Note that `EvaluationReport.summary()` must include exposure history, reused-vs-fresh
   performance, world-growth provenance, diversity, failure/extinction, and recovery fields — do
   not collapse persistent-world and fresh-world results into one headline.

**Success metric:** reproducible persistent-world and fresh-world results, with EAE and any human
or frontier reference reported only under matched observations, action space, and time budget.

**Depends on:** `evolzen.environment`, `evolzen.recognition` (what's being evaluated).
**Depended on by:** nothing — this is the terminal subsystem in the pipeline.
