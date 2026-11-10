# Design Audit — Supplied Blueprints vs. Repository and Revised Goal

**Audit date:** 2026-10-21  
**Scope:** the supplied master overview, segmented plan, PRDs, voxel-engine appendix, and
technical summary, compared with the repository's `docs/`, `AGENTS.md`, `SECURITY.md`, and the
revised goal: **an independently growing game world populated by diverse synthetic agents**.

No code or tests are required for this audit. The repository remains a Phase 0 scaffold.

## Executive verdict

The repository is internally coherent as a Phase 0 scaffold for a bounded multi-agent research
testbed. The supplied documents are not yet a feasible end-to-end specification for the original
voxel civilization or for a general intelligence system.

After the documentation upgrade, the feasible research target is:

> A persistent, event-sourced, discrete social sandbox in which a small heterogeneous population
> can produce durable, attributable world growth, while a contained learning system is evaluated
> separately for longitudinal adaptation and fresh-world action efficiency.

This is feasible as a research prototype if the project accepts four limits:

1. the world is discrete and bounded, not a physically faithful universe;
2. “all types of people” means a declared behavioral/social ontology, not realistic human
   demographics, consciousness, or emotional life;
3. world growth is extensible but typed, versioned, and bounded rather than unrestricted;
4. the predictor/recognition components are measurable learning modules, not an AGI claim.

## Section-by-section audit

| Supplied section | Verdict against repository docs | Required correction |
|---|---|---|
| Executive overview | Direction is compatible after removing AGI language. The repository's real contribution is narrower than “general intelligence combined with emotional intelligence.” | Use two research questions: independent world growth and efficient adaptation. Keep them analytically separate. |
| Research landscape | Useful motivation, but benchmark numbers and “leading/default” wording are date-sensitive and source-sensitive. | Date every benchmark claim, label source status, and treat ARC-AGI-3 as a motivation for action-efficient evaluation rather than the project's definition of AGI. |
| System architecture | The nine-subsystem structure matches the repository. The supplied “Segment 1 / Segment 2” framing conflicts with ADR 0003 when used as the active architecture. | Keep the nine sibling subsystems. Use data-flow diagrams only; do not make “world/observer” a second architecture. |
| Hardware topology | Device roles are plausible as a starting hypothesis, not a feasibility result. | Add capacity gates for model memory, tokens/sec, world ticks/sec, storage, sandbox density, and training throughput. |
| Phase 1.1 voxel engine | Conventional systems engineering is possible, but the complete 5-layer voxel/DEM design is not justified by the research question or hardware plan. | Replace it with the persistent event-sourced social sandbox in ADR 0004. Treat voxel/physics work as a future optional domain, not Phase 1.1. |
| Phase 1.2 growing LLMs | Rank-by-age LoRA growth and literal weight crossover are speculative and conflict with the repository's current drive-vector/QD design. | Use typed agent profiles, drive vectors, QD descriptors, lineage, and optional sandboxed self-modification. Measure capacity before scaling population. |
| Phase 1.3 society | Currency and specialization are feasible as toy mechanisms. “Books” as serialized policy embeddings are not a sufficient inspectable knowledge contract. | Use provenance-tracked, falsifiable manuals plus institutions, norms, contracts, and world-health metrics. Define the provenance floor. |
| Phase 1.4 technology discovery | Pure RL discovery of bridges, water wheels, latches, and CPUs is not supported by the supplied evidence. | Use bounded actor/synthesizer/verifier exploration. Require replay, held-out combinations, interventions, and containment. |
| Phase 1.5 growing library | A non-overwriting library matches the repository, but frozen rules alone cannot express legitimate world changes. | Add validity context, supersession, versioning, and audit trails. |
| Bridge / data pipeline | “Causal traces” and “central AGI” overstate what exact replay provides. | Say “mechanistically generated and verifiable transition data”; reserve causal claims for intervention-tested findings. |
| Phase 2.1 observer | A predictor over agent/world transitions is feasible as a baseline. A fixed >90% long-horizon target is not justified. | Start with supervised/action-prediction baselines, then test policy-gradient planning and rehearsal. Report transfer, forgetting, latency, and cost. |
| Phase 2.2 causal gate and constitution | A differentiable causal gate and mathematically verified open-ended ethics layer are unspecified research problems. | Use promotion checks, interventions, explicit behavioral constraints, and fail-closed containment. Do not call this solved alignment. |
| Phase 2.3 internet/Oracle API | Querying a knowledge base and seeding answers into the world bypasses the intended generalization test. | Keep retrieval as a documented experimental condition, not hidden assistance. Promotion still requires verification. |
| Phase 2.4 1,000 worlds | The scale target is neither required nor supported by the hardware evidence. | Use held-out world seeds and mechanic combinations plus a persistent-world longitudinal track. |
| Phase 2.5 graduation | Transfer to bridge design, real code, or human empathy is not established by synthetic social simulation. | Remove graduation claims. Report bounded within-family results and limitations. |
| Timeline | The original 24–36 month AGI schedule is not defensible; the earlier 7–10.5 month prototype estimate omitted world-growth and containment gates. | Use a 9–14 month planning range for a tested prototype, explicitly contingent on pilot measurements. |
| Upgrade log | Valuable historical record, but it sometimes presents proposed mechanisms as validated contributions. | Preserve the history while marking proposals, replications, vendor reports, and unverified references. |

## Repository mismatches found

### 1. Formal semantics

The repository called the environment a Moore machine while requiring outputs to be re-derived from
`(state, action)`. The normative contract is now explicitly:

```text
(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})
```

This makes stochasticity reproducible and prevents hidden mutable state. `moore_machine.py` remains
a compatibility filename, not the authority for causal semantics.

### 2. “Causal data” versus verified transitions

Exact replay proves that a candidate mechanism reproduces the recorded transitions. It does not by
itself prove an identifiable causal graph, counterfactual correctness outside the observed support,
or correct inference of agent intent. The upgraded docs therefore require interventions and
held-out transition combinations before causal language is used.

### 3. World growth versus library growth

The previous design had a growing rule library, manuals, and agent variants, but no explicit
contract for a world that grows. The upgraded architecture adds a persistent world, growth ledger,
snapshots, branching, world invariants, and allowed growth categories.

### 4. Diversity versus “all types of people”

Drive-vector diversity is not an ontology of people. The upgraded design defines observable agent
profiles and reports occupancy, persistence, extinction, replacement, specialization, communication,
and lineage diversity. It does not claim to model actual human populations.

### 5. Evaluation mismatch

A fresh mini-environment test is useful for adaptation, but it cannot substitute for a longitudinal
world-growth evaluation. EvolZen now has two tracks: persistent-world growth and fresh-world EAE.
The tracks are reported separately.

### 6. Containment mismatch

The repository's sandbox is an interface, while the supplied blueprint assumes a deployed secure
runtime. The upgraded docs separate interface, backend, and target-host acceptance. A backend name
is not evidence of a security property.

### 7. Documentation hygiene

The previous docs index promised phase sections that were not present, the research index omitted
existing landscape/design-evolution files, and `PAPER.md` claimed bibliography completeness while
several cited sources were absent from `references.bib`. The indexes and citation-status policy
were updated; missing references still need verification before publication.

## Feasibility verdict by phase

| Phase | Prototype feasibility | Research risk | Gate before proceeding |
|---|---|---|---|
| 1.1 Environment | Medium-high for a discrete persistent sandbox | World-growth semantics may degenerate into scripted milestones | Replay, growth ledger, snapshots, invariants, shock recovery, hardware pilot |
| 1.2 Agents | Medium for 10–30 active agents | LLM throughput, descriptor validity, diversity collapse | Capacity envelope and five-generation diversity report |
| 1.3 Economy | Medium | Institutions and norms may be prompt artifacts or unstable | Durable institution/norm plus provenance and world-health report |
| 1.4 Exploration | Medium for bounded rules | Transfer from clean tasks to social dynamics; false promotion | Intervention and held-out-combination verification |
| 1.5 Library | High for immutable versioned storage | Contextual validity and supersession policy | Historical replay and auditability |
| 2.1 Predictor | Medium for baselines | Continual learning under a moving population | Transfer/forgetting/cost curves |
| 2.2 Containment | Medium for interface; low until deployed | Backend support and threat-model coverage on target hardware | Backend and host acceptance tests |
| 2.3 Recognition | Low-to-medium | JEPA/wake-sleep fusion is unproven and may be unnecessary for typed state | Baseline-first ablation matrix |
| 2.4–2.5 Evaluation | High for instrumentation | Metric leakage and conflating growth with transfer | Two-track, seed-stratified report |

## Paper feasibility

A research paper is feasible if it claims one of these bounded results:

- whether a declared population ontology and QD selection produce more persistent behavioral/type
  diversity than specified baselines;
- whether the population and economy produce durable world growth under a fixed world contract;
- whether verified exploration improves held-out transition/intervention performance;
- whether the recognition components improve EAE or adaptation latency under matched exposure; or
- a negative result showing that a proposed component fails to transfer from clean discrete tasks to
  a persistent social sandbox.

The paper is not feasible as evidence that the system has learned general human psychology,
emotional intelligence, universal civilizational laws, or AGI.

## Required order of work

1. Freeze the persistent-world contract and agent ontology.
2. Build replay, snapshots, growth ledger, and invariants before adding LLM agents.
3. Run a small deterministic population and establish world-growth metrics.
4. Add QD diversity and economy/institution mechanisms.
5. Add sandboxed exploration and versioned rule promotion.
6. Run hardware and containment acceptance gates.
7. Add predictor and recognition ablations only after the world produces nontrivial data.
8. Run persistent-world and fresh-world evaluations separately.
