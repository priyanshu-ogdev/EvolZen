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

---

## Audit 2026-11-12 — Library Review, `agents` Directory Relevance, and Frontier AGI / Diversity / Growth Literature

**Audit scope:** Post-Phase-1.5 code & documentation review of `evolzen.library`, full code audit of `src/evolzen/agents/`, IEEE/ML citation expansion, and audit of recent models/benchmarks making AGI, diversity, or open-ended growth claims against `PRD.md` §4 (`NG1`–`NG5`).

### 1. `evolzen.library` Review Findings & Fixes

Reviewing the completed Phase 1.5 subsystem (`src/evolzen/library/`, `src/evolzen/schemas/library.py`, `tests/library/`) identified three concrete engineering improvements that were fixed and verified:

1. **Context-aware default routing (`rule_library.py`):** `_default_confidence` previously scored `SequenceMatcher` similarity purely on `code` text. Updated `_default_confidence` to return `0.0` immediately when an existing entry is incompatible with the candidate's `ValidityContext` (`not is_applicable(b, a.validity)`), preventing cross-version routing across world changes.
2. **Windows file-lock offset alignment (`audit.py`):** `msvcrt.locking` on Windows locks 1 byte starting from the current file descriptor offset; seeking to byte `0` before locking and before unlocking (after `fh.flush()`) ensures consistent lock/unlock offset alignment across concurrent writers.
3. **Deterministic store query ordering (`persistence.py`):** Added `ORDER BY row_seq` to `LibraryStore.get_all()`.

### 2. Full `src/evolzen/agents/` Relevance Audit

`src/evolzen/agents/` currently contains **two separate, non-integrated code paths**, which remain intentionally isolated per `src/evolzen/agents/README.md` (`docs/subsystems/agents/engineering.md`):

| Path | Modules | Relevance to Phase 1.2 & Revised Goal | Status / Gap |
|---|---|---|---|
| **Implemented numerical baseline** | `agents/development/{motivation,lifecycle,brain,learning,evolution}.py` + `schemas/development.py` | **High relevance (core Phase 1.2 baseline):** deterministic seeded `BirthGenome`, eight-coordinate recurrence (`Motive`), simulation-clock `LifeStage` boundaries (`born`, `stage_at`, `advance`), greedy candidate ranking (`decide`), identity-checked EMA outcome learning (`observe`), living-parent advice (`teach`), and gated `DevelopmentArchive`. | Clean, zero unsafe `eval`/`exec`, CPU-only. **Missing:** world adapter, persistent scheduler, population budget enforcement, LLM action proposals, and multi-generation empirical runs. |
| **Legacy five-drive / LLM stub path** | `agents/{drive_vector,inference,qd_archive,self_modification}.py` + `schemas/drive_vector.py` | **Partial relevance / structural split:** `Agent`, `TransformersBackend`/`VLLMBackend` (`NotImplementedError` stubs), 5-coordinate `DriveVector`, `QualityDiversityArchive` (MAP-Elites), and `SelfModificationProposal`/`evaluate_proposal` (DGM-style gate). | Legacy path uses 5 drives (`DriveVector`) while `development/` uses 8 (`Motive`), and `self_modification.py` uses `eval` target `held_out_eval` without `Sandbox` wiring. Must stay reconciled or deprecated via explicit adapter once Phase 1.1 domain `Action` schema is frozen. |

**Key architectural gaps discovered in `agents`:**
- **No intrinsic-motivation signal vs. greedy baseline:** `agents/development/brain.py` uses purely greedy expected-outcome ranking (`score(action)`). Literature in *IEEE TEVC* (`oudeyer2007intrinsic`) and *IEEE TCDS* (`santucci2016grail`) emphasizes competence-progress / goal-discovery drives for open-ended environments.
- **2D fixed archive grid:** `DevelopmentArchive` defaults to `dimensions=2, bins=5`; scaling to richer behavioral descriptors requires Voronoi partitioning such as CVT-MAP-Elites (*IEEE TEVC* 2018, `vassiliades2018cvtmape`).
- **No unified `AgentProfile` schema yet:** PRD FR-3 requires roles, affiliations, memory scope, communication channels, and norms; only temperament, outcome estimates, and lessons exist today.

### 3. Audit of Frontier AGI, Diversity, and Open-Ended Growth Models

Recent systems and benchmarks frequently cited around AGI, self-improvement, and open-endedness were audited against EvolZen's falsifiable non-goals (`PRD.md` §4):

| System / Paper | Source Status | Claim / Breakthrough | Audit Verdict for EvolZen |
|---|---|---|---|
| **ARC-AGI-2** (`chollet2025arcagi2`, `arXiv:2505.11831`) & *On the Measure of Intelligence* (`chollet2019measure`) | Preprint (benchmark specification) | Separates memorized pretraining from compositional fluid skill acquisition; standard unassisted text-reasoning models (e.g., DeepSeek-R1 ~1.1%–1.3% baseline) diverge sharply from iterative test-time program search (e.g., o3-class search pipelines). | Reinforces EvolZen's dual-track separation (`persistent-world` vs `fresh-world` EAE) and confirms that LLM pretraining alone does not establish generalization. |
| **Voyager** (`wang2023voyager`, *TMLR* 2023) | Peer-reviewed journal | Automatic curriculum + compositional executable skill library in Minecraft + iterative self-verification reduces forgetting across tasks. | Direct precedent for coupling `evolzen.exploration` with `evolzen.library`, but EvolZen requires explicit `ValidityContext` and `Sandbox` containment because world rules can change (`env-v1` → `env-v2`). |
| **OMNI-EPIC** (`faldor2024omniepic`, `arXiv:2405.15568`) | Preprint | Foundation models synthesize both interestingness priors and code-programmed environments (unlimited auto-curriculum). | Bounded in EvolZen: ADR 0004 explicitly rejects unrestricted open-ended world invention; new mechanics must enter as typed, versioned capability packages. |
| **DGM & Hyperagents (`DGM-H`)** (`dgm2026`, `hyperagents2026`, `arXiv:2603.19461`) | `dgm2026`: ICLR 2026; `hyperagents2026`: Preprint | Extends empirical self-modification from coding-only benchmarks to metacognitive self-editing (task agent + meta-agent unified, inventing persistent memory/insight trackers). | High containment risk: self-referential meta-editing directly reinforces `SECURITY.md`'s hard rule that no self-modified code executes outside `evolzen.containment.Sandbox`. |
| **Hughes et al. — Open-Endedness for ASI** (`hughes2024openended`, *ICML* 2024) | Peer-reviewed position paper | Argues open-ended novelty/learnability is necessary for ASI. | Treated as motivation for EvolZen's diversity and world-growth metrics (`qd_archive`, `GrowthEvent`), **not** as an AGI/ASI claim (`NG1`). |
| **IEEE Continual Learning & QD Foundations** (`wang2024continualsurvey`, `oudeyer2007intrinsic`, `santucci2016grail`, `vassiliades2018cvtmape`) | Peer-reviewed IEEE journals (*TPAMI*, *TEVC*, *TCDS*) | Formalizes catastrophic-forgetting mitigations (replay, dynamic isolation, regularization), competence-progress intrinsic motivation, and CVT-scaled QD archives. | Primary peer-reviewed anchor for `evolzen.agents`, `evolzen.library`, and `evolzen.predictor` baselines and ablations. |
