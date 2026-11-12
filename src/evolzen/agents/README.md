# evolzen.agents — Phase 1.2

## Developmental design and implementation status

The new primary design is **seven sins plus Null**, randomized birth equations, childhood,
age-dependent context, personal feedback learning and living-parent teaching. Read the
[full design](../../../docs/subsystems/agents/README.md) and
[developmental source map](development/README.md) first.

`development/` implements the numerical baseline and a bounded phenotype archive. It does not
train LLMs or implement a full world/population scheduler. The existing five-drive `Agent`,
`DriveVector`, inference and QD APIs remain a separate legacy path for compatibility; they are
not silently upgraded to eight drives. Rich `AgentProfile` and neural-training APIs are planned.

**Goal:** populate the persistent world with 10–30 active cognitive agents plus optional
deterministic background population processes. Each active agent has an explicit behavioral/social
profile (needs, drives, skills, roles, affiliations, memory scope, communication, norms,
capabilities, and lineage). “All types of people” means coverage of this declared ontology, not a
claim to simulate real human demographics or psychology.

Full research design: [`docs/phases/1.2-agents.md`](../../../docs/phases/1.2-agents.md).

## What's here

| File | Purpose |
|---|---|
| [`development/`](development/README.md) | Implemented birth, motivation, lifecycle, numerical learning, teaching and validated archive. |
| [`drive_vector.py`](drive_vector.py) | Legacy `Agent`: model ID, five-drive vector, lineage and backend; no rich profile or lifecycle. |
| [`inference.py`](inference.py) | Legacy inference protocols and stubs; generation is not implemented. |
| [`qd_archive.py`](qd_archive.py) | `QualityDiversityArchive` — MAP-Elites-style selection, replacing plain fitness-based selection. |
| [`self_modification.py`](self_modification.py) | Darwin-Gödel-Machine-style validated self-modification (arXiv:2505.22954). |

## Population-design hypotheses (test rather than assume)

These are proposed population ablations, not universal empirical rules:
1. Compare a shared frozen base with private state against differently trained base models.
2. Compare sparse and dense communication/trade graphs at matched communication budgets.
3. Compare flat and hierarchical advice structures without granting teachers evaluator authority.

## How to build this

1. Validate the numerical `born -> decide -> observe` loop and live-parent teaching.
2. Wire the implemented Phase 1.1 host adapter (`evolzen.environment.adapter`, currently surfacing 7/17 `ActionType`s) and `TransitionLogStore` (`evolzen.storage`) into a population scheduler, define `AgentProfile`, reconcile the legacy five-drive stubs with the eight-drive core, and enforce living-agent resource/birth budgets.
3. Add `outlines`-constrained LLM candidate generation (`ActionType` + `params`) without converting eight drives into five silently.
4. Add private adapter updates and validation/retention rollback only after numerical baselines.
5. Measure multi-generation QD selection and cultural transfer at equal experience budgets.
6. Enable generated policy changes only through deployed containment. See the detailed
   [delivery gates](../../../docs/subsystems/agents/engineering.md).

**Success metric:** a 10–30-agent population runs stably for at least five generations, maintains
coverage across the declared behavioral/social descriptor map, and produces at least two persistent
specialization patterns without collapsing to one strategy.

**Depends on:** `evolzen.schemas.development` for the numerical core; legacy
`evolzen.schemas.drive_vector`/`transition` for the old API. Environment execution and trusted
feedback are integration dependencies, not implemented by the core.
**Depended on by:** `evolzen.economy` (agents write/read manuals),
`evolzen.exploration` (agents' behavior is what's probed and explained).
