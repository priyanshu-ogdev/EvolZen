# EvolZen — Architecture

**Companion document:** [`PRD.md`](PRD.md) specifies *what* and *why*; this document specifies
*how*.

---

## 1. System overview

EvolZen is **one Python package** (`evolzen`) organized into nine subsystems on top of a shared
foundation. It is a persistent, event-sourced social sandbox plus learning and evaluation
components; it is not a voxel-physics stack and it is not a two-part “world/observer” product.

```
src/evolzen/
├── config.py, logging.py, tracking.py, schemas/, storage/   # shared foundation
├── environment/    # Phase 1.1
├── agents/         # Phase 1.2
├── economy/        # Phase 1.3
├── exploration/     # Phase 1.4
├── library/         # Phase 1.5
├── predictor/        # Phase 2.1
├── containment/      # Phase 2.2
├── recognition/      # Phase 2.3
└── evaluation/       # Phase 2.4-2.5
```

The diagram below is a data-flow view, not a package or lifecycle boundary. The nine subsystems
jointly maintain a persistent world, a heterogeneous population, executable hypotheses, and
measured learning components:

```
[environment] -> [agents] -> [economy] -> [exploration] -> [library]
                                                                 |
                              verified transitions + rule library + manuals
                                                                 |
                                                                 v
     [predictor] -> [containment] -> [recognition] -> [evaluation]
```

`evolzen.containment` is drawn separately because it is a cross-cutting boundary. Every subsystem
that executes agent-originated or synthesized code (`exploration` hypotheses, `agents`
self-modification proposals, `library` capability packages, and any code-backed environment rule)
must route execution through it.

## 2. Design principles

Enforced by structure, not convention:

1. **Verifiability over plausibility.** Every transition is replayable from complete state,
   action, exogenous input, and seed. Every promoted rule must pass exact replay plus the
   intervention checks required by its claim. Exact replay is not itself proof of causal
   identification.
2. **One package, nine subsystems, shared foundation.** Every subsystem imports the same
   schemas from `evolzen.schemas` — there is no package boundary between subsystems to
   accidentally drift across. See [ADR 0003](adr/0003-nine-subsystems-not-two-packages.md) for
   why this is stated as a principle rather than assumed: it was violated twice by earlier
   scaffolding revisions.
3. **CPU-runnable by default, GPU-accelerated by extra.** The base dependency set installs and
   passes tests on a CPU-only machine. Heavy, platform-specific acceleration (vLLM, DeepSpeed,
   bitsandbytes, flash-attn, faiss-gpu) is an opt-in extra — see
   [ADR 0002](adr/0002-dependency-stack-and-optional-extras.md).
4. **Growth, diversity, and forgetting are measured, not assumed.** World growth, agent-type
   coverage, lineage diversity, manual provenance, forward/backward transfer, and forgetting each
   have explicit metrics and stop/rollback conditions.
5. **Every design choice traces to a citation or an explicit flag.** Citation status is recorded
   as peer-reviewed, preprint, vendor report, or unverified. See
   `docs/research/references.bib`.

## 3. Subsystem architecture

### 3.1 `evolzen.environment` — Phase 1.1

A persistent, event-sourced, discrete social sandbox with typed entities for agents, locations,
resources, artifacts/capabilities, contracts/markets, institutions, norms/beliefs, manuals, and
exogenous events. The normative transition contract is:

```text
(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})
```

The transition is deterministic for a fixed complete input record. `moore_machine.py` remains a
compatibility-oriented module name from Phase 0, but the formal object is a seeded, typed
interactive transition system, not a claim that exact replay identifies a causal graph. The world
supports snapshots, branching, append-only event logs, and a growth ledger attributing durable
changes to endogenous processes, agent actions, or declared exogenous inputs.

World growth is bounded and typed. New mechanics arrive as versioned capability packages; they are
not arbitrary executable mutations of the engine. Packages must pass containment, replay, held-out
combination, intervention, and resource-bound checks before promotion.

**Implementation status (baseline implemented; hardening & empirical pilots pending):**

- **Implemented baseline:** `SocialSandboxEngine` implements `Environment` and
  `PersistentEnvironment` across all 17 `ActionType` handlers (`environment/engine.py`), backed
  by typed `WorldState`/`WorldSnapshot` schemas (`schemas/world.py`), `Transition` +
  `ExogenousInput` (`schemas/transition.py`), invariant checking (`check_invariants` in
  `environment/invariants.py`), growth-ledger extraction (`extract_growth_events` /
  `summarize_growth` in `environment/growth.py`), DuckDB hash-chained persistence
  (`TransitionLogStore` in `storage/transition_log.py`), replay & branching (`replay_transitions`,
  `replay_from_store`, `branch_from_snapshot` in `environment/replay.py`), controlled
  interventions (`apply_intervention` in `environment/interventions.py`), the agent-facing
  `adapter` (`observe_features`, `legal_candidates`, `action_from_candidate`, `execute_decision`
  in `environment/adapter.py`), PettingZoo AEC compatibility (`SocialSandboxAECEnv` in
  `environment/pettingzoo_env.py`), and local CPU smoke benchmarking (`run_environment_pilot` in
  `environment/pilot.py`).
- **Open Phase 1.1 hardening items:**
  - `replay_transitions` must propagate `current_state` rather than passing `recorded.state` to
    `engine.step`, and `replay_from_store` must include `same_tick=True` transitions at
    `tick == up_to_tick`.
  - `apply_intervention` needs sequence indexing and `ResourceAccounting.initial_currency`
    reconciliation, and `SocialSandboxAECEnv.step` lacks `exogenous_input`/`seed` and
    `TransitionLogStore` hooks.
  - Bounded world growth requires enforcing `max_agents` on *living* agents (dead records
    currently block reproduction permanently at 64), adding capacity bounds on `WorldState`
    collections (`artifacts`, `contracts`, `institutions`, `norms`, `capabilities`, `inventory`)
    and an upper bound on `WorldAgentState.status`, and wiring partial mechanics
    (`ContractRecord.status="cancelled"`, `InstitutionRecord.contribution_rate`,
    `ArtifactRecord.durability`, `NormRecord` effects, and reachable `ENDOGENOUS_PROCESS`
    emissions).
  - `adapter.legal_candidates` currently surfaces 7 of 17 `ActionType`s (and `SocialSandboxAECEnv`
    exposes `Discrete(10)`).
  - `State.data`, `Action.params`, `ExogenousInput`, and `Emission.data` remain untyped
    `dict[str, Any]` boundaries across subsystem callers.
  - Failure-branch, Hypothesis property-based, and long-horizon multi-generation tests, plus
    empirical long-horizon shock-recovery runs and target-rig hardware pilots, remain **untested**.

**Success metrics (untested empirically):** replay determinism; zero hidden mutable state; durable
growth across at least three allowed categories (for example artifacts, institutions, and roles);
and recovery from a declared environmental shock without evaluator-injected milestones.

### 3.2 `evolzen.agents` — Phase 1.2

**Current design authority:** [developmental agents](subsystems/agents/README.md).
The implemented `agents/development/` numerical baseline uses eight birth-time equations
(seven sins plus Null), age/context/momentum dynamics, bounded outcome learning, living-parent
teaching and `DevelopmentArchive`. Existing `Agent`/`DriveVector` inference and QD APIs still
use five coordinates and remain legacy interfaces, not adapters for the new path.
The richer profile, LLM proposal, neural-update and population-scheduler descriptions below are
target architecture; they are not implemented by the existing `Agent` dataclass.

Each active cognitive agent (`agents.drive_vector.Agent`) pairs a small quantized local LLM with an
evolvable `DriveVector` (`evolzen.schemas.drive_vector`) and a typed profile: needs, drives,
skills, roles, affiliations, memory scope, communication channels, norms, capabilities, and
lineage. These profiles define behavioral diversity; they are not a claim to reproduce real human
demographics or psychology. A deterministic background-population process may represent aggregate
residents without allocating an LLM to every resident.

Drive vectors are evolved on the vector itself, never via literal LoRA weight crossover. Action
generation goes through `agents.inference.InferenceBackend` (`transformers` for CPU/dev,
`vllm` for throughput), constrained via `outlines` to always produce a schema-valid `Action`.

Selection runs through a Quality-Diversity archive (`agents.qd_archive`), not plain fitness. The
archive is keyed by declared behavioral and social descriptors such as risk, reciprocity,
coalition formation, exploration, communication, and specialization. Agents may carry a
Darwin-Gödel-Machine-style validated self-modification mechanism (`agents.self_modification`),
but every proposal is evaluated inside containment and retained only when it improves a declared
held-out objective without violating invariants. Population execution is Ray-orchestrated for the
10–30-agent pilot; throughput is a hardware acceptance gate, not an assumption.

Population ablations should compare shared versus diverse base models, sparse versus dense
communication, and authority structures. These are experimental factors, not guaranteed rules.
A shared frozen base with private state is a valid efficiency baseline.

**Success metrics (untested):** stable 10–30-agent runs; QD coverage; agent-type occupancy and persistence;
lineage diversity; specialization; extinction/replacement; and communication-topology statistics
across at least five generations.

### 3.3 `evolzen.economy` — Phase 1.3

**Implementation status:** Phase 0 in-memory prototypes (`economy.market.Market` uses `float`
balances rather than `WorldAgentState.currency` `NonNegInt` and does not yet emit
`ActionType.TRADE`; `economy.manuals.ManualStore` enforces `real_data_floor`, while
`ProvenanceRecord` and `Manual` persistence on `WorldState` / `TransitionLogStore` remain
pending).

Currency, resource flows, contracts, specialization, and institution formation (`economy.market`)
are scoped to the persistent world. Knowledge transfer happens through falsifiable, actively
revised manuals (`economy.manuals`, `evolzen.schemas.manual`). Each manual records provenance,
scope, author, evidence, falsifications, and revision history. The provenance floor distinguishes
human-authored/external material, human demonstrations, independently generated simulator traces,
and model-generated material; no category is silently relabeled as another.

**Success metrics (untested):** specialization and at least one durable institution or norm emerge; manual
claims are falsified and revised when contradicted; the configured provenance floor is maintained;
and population/world diversity does not collapse across at least five generations.

### 3.4 `evolzen.exploration` — Phase 1.4

**Implementation status:** Phase 0 stubs (`actor.py`, `synthesizer.py`, `verifier.py`;
`Verifier.verify()` raises `NotImplementedError`, and `CandidateRule.code` signature alignment with
`(State, Action, ExogenousInput, seed)` plus `Sandbox`/`replay_transitions`/`apply_intervention`
wiring remain pending).

An actor (`exploration.actor`) probes the environment, prioritized by a measured explanation gap
over agent types, mechanics, and world-growth categories. A synthesizer
(`exploration.synthesizer`) proposes typed executable hypotheses; an off-the-shelf coding-agent
harness may be used, but only through `evolzen.containment` and never as an implicit trust
boundary. A verifier (`exploration.verifier`) checks exact replay on recorded transitions, held-out
transition combinations, at least one controlled intervention, and declared resource bounds.

**Success metrics (untested):** the verified-rule library beats a no-exploration-strategy baseline on held-out
transitions and interventions; false promotion rate is measured; and no candidate can mutate the
world engine outside the versioned capability-package interface.

### 3.5 `evolzen.library` — Phase 1.5

**Implementation status:** Phase 1.5 baseline implemented (`library.rule_library.RuleLibrary`,
`library.validity`, `library.audit.AuditLog`, `library.persistence.LibraryStore` on DuckDB, and
`library.regression_bank.RegressionBank`, backed by `schemas.library` and unit/3-round integration
tests); live wiring to Phase 1.4 `Verifier` and `CapabilityPackage` promotion awaits Phases 1.4
and 2.2.

Verified rules become immutable historical entries (`library.rule_library`) with validity context,
provenance, evidence links, and supersession metadata. A new entry spawns when no existing entry
adequately explains the observation in the current context; a changed rule creates a new version
instead of overwriting the old one. The Dirichlet-process analogy is a routing heuristic, not a
claim that the implementation is a Bayesian nonparametric model.

**Success metrics (empirically untested at world scale):** historical replay remains readable across
at least three rounds of additions; promotion and supersession decisions are auditable; and newly
added rules improve held-out transition/intervention performance without increasing false promotions.

### 3.6 `evolzen.predictor` — Phase 2.1

**Implementation status:** Phase 0 stubs (`Planner.predict()` / `Planner.train_step()` raise
`NotImplementedError`; `PredictionResult` alignment with `Emission` + `next_state: State` and
`TransitionLogStore` batching remain pending).

A planner (`predictor.planner`) may use policy-gradient training, but the first baseline is a
supervised/action-prediction predictor so that the contribution of RL is measurable. Rewards and
labels are grounded in replayable world outcomes, not inferred from another model's approval. A
rehearsal buffer (`predictor.rehearsal_buffer`) mixes old and new transitions under a declared
budget. Updates are evaluated for forward transfer, backward transfer, forgetting, adaptation
latency, and compute/data cost; task-free or replay-free continual training is an ablation, not a
default assumption.

**Success metrics (untested):** held-out prediction and intervention performance; longitudinal adaptation
latency; forgetting and transfer curves; and cost per retained capability.

### 3.7 `evolzen.containment` — Phase 2.2

**Implementation status:** `containment.sandbox.Sandbox` is a `Protocol`-only interface (no concrete
Firecracker or gVisor backend deployed yet) and `containment.governance.CapabilityGovernor` is an
in-memory bookkeeping prototype not yet wired to `CapabilityPackage` or `SocialSandboxEngine`.

Any promoted capability package passes the replay/intervention gate from Phase 1.4. All
agent-generated or self-modified code executes inside a hardware-isolated sandbox
(`containment.sandbox` is an interface only; Firecracker microVMs or gVisor are infrastructure
backends, not pip dependencies). Governance is fail-closed: static default-deny controls remain
authoritative, while behavior-sensitive policy may tighten permissions but may not grant a
capability that the static policy forbids. Every policy decision, denial, resource event, and kill
switch action is logged.

**Acceptance layers (untested):** interface tests; backend deployment tests; and target-host threat-model
tests. The phase is not complete until the selected backend demonstrates bounded resources,
egress control, evaluator separation, kill-switch latency, recovery, and tamper-evident logging on
the actual host.

### 3.8 `evolzen.recognition` — Phase 2.3

**Implementation status:** Phase 0 stubs/interface prototypes (`jepa.py`, `wake_sleep.py`,
`moe_library.py`, `embedding_router.py`); `JEPAEncoder`, `WakeSleepLearner`, and the ablation
matrix runner await Phase 1.1–2.1 transition streams and typed world bindings.

This is the project's proposed architectural variant and least-de-risked component, not a
validated contribution. A JEPA-style encoder (`recognition.jepa`, following LeJEPA's objective,
arXiv:2511.08544) learns continuous representations of partially observed world states. A
DreamCoder-style wake-sleep learner (`recognition.wake_sleep`, PLDI 2021) proposes and refactors
typed operators over those states. The combination is tested as a hypothesis: it may help, do
nothing, or interfere. It must first beat simpler baselines on the actual world representation;
JEPA is not justified merely because the domain is called social.

The verified-rule library is exposed through a sparse router
(`recognition.moe_library`, `recognition.embedding_router`), but routing confidence is not
treated as proof of rule validity. A manual layer, carried over from `evolzen.economy`, is a
fast, cheap memory tier whose provenance and revision history remain visible. Its output is
subject to the same held-out and intervention checks as any other hypothesis.

**Evaluation:** an explicit ablation matrix — with/without recognition model x with/without
manual layer x JEPA-only / wake-sleep-only / combined.

**Success metrics (untested):** the recognition condition improves adaptation latency or success on at least
one pre-registered track without unacceptable regression on the other; every ablation cell is
reported; and a negative or null result is reportable, not hidden.

### 3.9 `evolzen.evaluation` — Phase 2.4-2.5

**Implementation status:** Phase 0 stubs/prototypes (`procedural_env_gen.py` raises
`NotImplementedError`; dual-track runner, `PersistentEnvironment` integration, and `EAE` reporting
remain pending).

A procedural generator (`evaluation.procedural_env_gen`) produces held-out world seeds and
held-out combinations of mechanics. Evaluation is split into two non-interchangeable tracks:

1. **Persistent-world track:** measures durable growth, world health, type diversity, lineage
   persistence, adaptation after shocks, and recovery/extinction outcomes over long runs.
2. **Fresh-world track:** measures action-efficient adaptation with **EvolZen Action Efficiency
   (EAE)**, inspired by the motivation of RHAE but not presented as an ARC-AGI-3 score unless the
   official task and protocol are actually used.

The existing `evaluation.rhae_scorer` may remain as a compatibility implementation name while its
public documentation is corrected to distinguish EAE from official RHAE. A structured report
(`evaluation.report.EvaluationReport`) has no free-text headline-claim field: every number traces
to a phase metric, and exposure history, reused-vs-fresh performance, world-growth provenance, and
failure/extinction events are required fields.

**Success metrics (untested):** both tracks produce reproducible, seed-stratified results; all ablation cells
are reported; and any human/frontier reference uses matched observations, action space, and time
budget.

## 4. Data architecture

All cross-subsystem data contracts belong in `evolzen.schemas`. The map below distinguishes
currently implemented schema classes from still-planned contracts. Note that
`evolzen.schemas.__init__` currently re-exports `transition`, `library`, `DriveVector`, and
`Manual`, while `schemas.world` and `schemas.development` are currently imported from their
respective submodules (top-level re-export is an open hardening item).

| Schema / Module | Status | Introduced | Consumed by |
|---|---|---|---|
| `Transition` (`State`, `Action`, `ExogenousInput`, `Emission`) (`schemas/transition.py`) | Implemented (`State.data` / `Emission.data` remain untyped `dict[str, Any]`) | `environment` | `exploration`, `library`, `predictor`, `containment`, `evaluation` |
| `WorldState`, `WorldSnapshot`, `GrowthEvent`, `WorldInvariant`, `InvariantReport`, `BranchRecord`, `InterventionSpec`, `CapabilityPackage`, `ActionType` (`schemas/world.py`) | Implemented (Phase 1.1; not yet re-exported in `schemas/__init__.py`) | `environment` | `economy`, `exploration`, `library`, `containment`, `evaluation` |
| `RuleEntry`, `VerificationEvidence`, `ValidityContext`, `SupersessionLink`, `AuditEvent`, `RegressionResult` (`schemas/library.py`) | Implemented (Phase 1.5; `CapabilityPackage.evidence_id` linkage pending Phase 1.4) | `library` | `exploration`, `recognition`, `evaluation` |
| `BirthGenome`, `BirthRecord`, `BrainSnapshot`, `Candidate`, `Decision`, `Outcome`, `Lesson`, `SkillEstimate`, `EvolutionAssessment` (`schemas/development.py`) | Implemented (Phase 1.2 numerical core; not yet re-exported in `schemas/__init__.py`) | `agents` | `environment` (`adapter`), `evaluation` |
| `DriveVector`, `AgentLineage` (`schemas/drive_vector.py`) | Implemented (Phase 0 / legacy 5-coordinate path; reconciliation with 8-coordinate `development.py` pending) | `agents` | `economy`, `predictor`, `recognition`, `evaluation` |
| `Manual` (`schemas/manual.py`) | Implemented schema (`ManualEntry` also defined in `schemas/manual.py`, not re-exported in `schemas/__init__.py`; world-state & store attachment pending Phase 1.3) | `economy` | `recognition`, `evaluation` |
| `AgentProfile` | **Planned** (not yet defined in `evolzen.schemas`) | `agents` | `environment`, `economy`, `predictor`, `recognition`, `evaluation` |
| `ProvenanceRecord` (plus `ManualEntry` provenance/world integration) | **Planned** (`ProvenanceRecord` not yet defined; `ManualEntry` exists in `schemas/manual.py` but lacks provenance/world wiring) | `economy` | `recognition`, `evaluation` |

Changing any of these is, by construction, a type error everywhere it's used — see
[ADR 0003](adr/0003-nine-subsystems-not-two-packages.md).

## 5. Hardware & deployment architecture

| Device | Role | Subsystems |
|---|---|---|
| AGX Spark | Agent population inference (Ray-orchestrated, `outlines`-constrained, optionally `vllm`-served) | `agents` |
| DGX Spark | Persistent environment state/logging, rule library, routing, and sandbox coordinator | `environment`, `economy`, `exploration`, `library`, `containment`, `recognition` |
| A6000 | Baseline predictor training, recognition experiments, replay maintenance, and hardware pilot measurements | `predictor`, `recognition`, `evaluation` |

Nothing in the codebase hard-codes device placement — `evolzen.config`'s per-subsystem settings
groups each expose a `device` field, so the same code runs on a laptop for development and on
the actual rig for real runs. See [`docs/dependency-stack.md`](dependency-stack.md) for base vs.
`gpu`-extra dependencies.

### 5.1 Hardware acceptance gates

The topology is a hypothesis until measured on the actual devices. Before population-scale claims,
record at least:

- model size, quantization, context length, memory use, and tokens/sec per active agent;
- action latency, world ticks/sec, event-log write rate, snapshot size, and replay throughput;
- maximum concurrent sandboxes, startup/teardown latency, resource ceilings, and kill-switch
  latency;
- predictor/recognition training throughput, replay-buffer size, checkpoint time, and recovery
  time; and
- storage growth and network bandwidth for a representative persistent-world run.

The pilot must produce a capacity envelope (agents, ticks, sandboxes, and training cadence) before
the timeline is treated as a feasibility estimate. “10–30 agents” is an initial research range,
not a guaranteed throughput target.

## 6. Security & containment architecture

Three binding constraints, enforced structurally:

1. No agent-generated code (`exploration`'s synthesizer output, `library`'s candidate rules,
   `agents`'s self-modification proposals) executes outside `evolzen.containment.Sandbox` — even
   during early development with toy code.
2. Network egress, filesystem writes, self-modification, and subprocess spawning are each a
   distinct, individually-grantable `Capability` (`containment.governance`), not a single
   coarse flag.
3. Every governance event, capability-package promotion, world-growth event, and kill-switch
   action is logged and retained. The containment backend is not considered secure merely because
   it is named Firecracker or gVisor; deployment and threat-model acceptance are required.

The threat model includes untrusted generated code, network and filesystem access, subprocess and
syscall abuse, resource exhaustion, log tampering, evaluator contamination, credential exposure,
sandbox escape, and recovery after a killed or corrupted run. Default-deny static policy is the
authority; learned or behavior-sensitive governance can only reduce access unless an explicitly
reviewed policy update grants more.

## 7. Observability

`evolzen.logging` provides one consistently-formatted logger across every subsystem, taggable
by phase. `evolzen.tracking.ExperimentTracker` is a pluggable metrics-logging protocol —
`NoOpTracker` by default, `WandbTracker` behind the `tracking` extra. No subsystem hard-codes a
specific tracking vendor.

## 8. Testing strategy

`tests/` mirrors `src/evolzen/` exactly, subsystem for subsystem. Every stub past
`NotImplementedError` needs a real test. Phase 1.1 (`tests/environment/`,
`tests/schemas/test_world.py`, `tests/storage/`), the Phase 1.2 numerical core
(`tests/agents/development/`, `tests/schemas/test_development.py`), and Phase 1.5 (`tests/library/`)
now carry active subsystem unit/integration suites; remaining subsystems hold stub and interface
tests. Tests touching a `gpu`-extra-adjacent dependency guard with `pytest.importorskip` (see
`tests/recognition/test_embedding_router.py`) so the base test suite never fails due to an
optional extra not being installed.

## 9. Timeline

| Subsystem | Phase | Estimate | Note |
|---|---|---|---|
| `environment` | 1.1 | 5-8 weeks | Persistent-world contract, replay, growth ledger, snapshots, and hardware pilot. |
| `agents` | 1.2 | 4-6 weeks | Ontology, QD descriptors, lineage, and population capacity measurements. |
| `economy` | 1.3 | 4-6 weeks | Markets, institutions, manuals, provenance, and world-health checks. |
| `exploration` | 1.4 | 4-7 weeks | Sandboxed synthesis plus replay/intervention verification; no unvalidated compression claim. |
| `library` | 1.5 | 3-4 weeks | Immutable versions, validity context, supersession, and regression bank. |
| `predictor` | 2.1 | 4-6 weeks | Baseline predictor first, then optional policy-gradient and continual-learning ablations. |
| `containment` | 2.2 | 4-8 weeks | Interface, backend, and target-host threat-model acceptance; can start early. |
| `recognition` | 2.3 | 8-12 weeks | JEPA/wake-sleep is a hypothesis; simpler representation baselines are mandatory. |
| `evaluation` | 2.4-2.5 | 6-9 weeks | Persistent-world and fresh-world tracks, EAE scorer, reports, and reproducibility. |

**Planning range: ~9-14 months for a tested research prototype; the range is not a claim that the
full design will fit the lower bound.**

## 10. Extension points

- New world scenarios: implement the `Environment` protocol and the versioned world-growth
  contracts; evaluation must declare whether a scenario is persistent-world or fresh-world.
- New `evolzen.agents` inference backends: implement `InferenceBackend`.
- New `evolzen.containment` backends: implement `Sandbox`.
- New `evolzen.recognition` routing strategies: implement `ExpertRouter` — `EmbeddingRouter` is
  the reference implementation.
- New experiment-tracking vendors: implement `ExperimentTracker` (`evolzen.tracking`).

## 11. Non-goals / constraints

Restated from [`PRD.md`](PRD.md) §4 because they bound the architecture as much as any
functional requirement: no claim of AGI proximity, emotional intelligence, or real-human
simulation; no scaling beyond the stated three-device hardware; no unrestricted open-ended world
invention; no attempt to solve, as a project deliverable, the field's open problems this design
depends on; and no re-fragmentation into multiple packages without a new ADR.
