# EvolZen — Product & Research Requirements Document

**Status:** scaffold plus an initial Phase 1.2 numerical agent core; world integration and empirical
research results remain pending. Implemented versus planned: [agent engineering](subsystems/agents/engineering.md).
**Owner:** EvolZen research team.
**Related:** [`ARCHITECTURE.md`](ARCHITECTURE.md) (how this is built), repository-root `AGENTS.md`
(rules for AI coding agents working in this repo), this document (what and why).

---

## Table of contents

1. Summary
2. Problem statement
3. Goals
4. Non-goals
5. Users & stakeholders
6. System overview
7. Requirements (functional, by subsystem)
8. Non-functional requirements
9. Success metrics
10. Milestones & timeline
11. Risks & mitigations
12. Parallel workstreams & team structure
13. Out of scope
14. Glossary
15. References

---

## 1. Summary

EvolZen is a concept-research project with two linked research questions:

1. **World-growth question:** can a persistent, verifiable social sandbox support durable growth
   of artifacts, institutions, norms, markets, and agent roles without being scripted as a fixed
   sequence of milestones?
2. **Learning question:** does combining an evolvable, behaviorally diverse population with
   verified world-model synthesis and a hybrid recognition model improve action-efficient
   adaptation to held-out world seeds and mechanic combinations?

The first question is about the world and its inhabitants. The second is about the learning system
that predicts, explains, and adapts within that world. They are related, but neither is allowed to
stand in for the other.

The system that investigates these questions is built from **nine subsystems inside one package**
(`evolzen`) — not two, not an arbitrary number chosen for tidiness, but the nine components the
underlying research design actually specifies: an environment engine, an agent population, an
economy and knowledge layer, a directed-exploration loop, a growing rule library, a grounded
predictor, a verification-and-containment layer, a recognition model, and an evaluation/
reporting layer. This document specifies *what* the project must deliver and *why*.
[`ARCHITECTURE.md`](ARCHITECTURE.md) specifies *how*.

## 2. Problem statement

Current language models can produce plausible social narratives and tool actions, but plausibility
is not the same as a persistent world that changes for reasons that can be checked. The original
EvolZen blueprint treated a physically rich voxel civilization and a central observer as if they
would automatically produce causal understanding, human-like intent recognition, continual
learning, and general intelligence. They do not.

The research problem is narrower and more useful: define a world whose state is persistent,
actionable, and replayable; define a behavioral ontology for heterogeneous agents; then measure
whether the resulting population can grow a world and whether the predictor/recognition system
improves adaptation to new situations. ARC-AGI-3 is relevant as motivation for measuring efficient
adaptation, but it is not the project's default benchmark or definition of general intelligence.
Its scoring protocol is
not automatically transferable to a custom persistent world.

The literature and the repository design impose four constraints:

- verified executable models are useful for discrete interactive tasks, but exact replay alone is
  not causal identification;
- continual learning requires explicit replay, forward/backward-transfer, and forgetting
  measurements rather than a claim that learning is monotonic;
- quality-diversity mechanisms preserve behavioral coverage only if descriptors and selection
  pressure are designed and audited;
- repeated exposure to a fixed evaluation set can measure memorized familiarity instead of fresh
  adaptation, so persistent-world and fresh-world evaluation must remain separate.

This project's own predecessor concept — an unscoped blueprint aiming directly at "AGI" via a
physically-simulated voxel civilization, observed by a monolithic "Central AGI" — could not
answer any research question: it required compute several orders of magnitude beyond the
available hardware (a DGX Spark, an AGX Spark, and an A6000), assumed several of the field's
genuinely open research problems were already solved, and had no external, falsifiable success
criterion. Every mechanism in that blueprint has since been traced to its specific failure and
replaced with something implementable and evidence-backed; see [ADR 0003](adr/0003-nine-subsystems-not-two-packages.md)
for the most recent step in that process (correcting an earlier scaffold that had, in turn,
mis-divided the design into two artificial "segments").

## 3. Goals

**G1.** Build a persistent, event-sourced, verifiable social sandbox (`evolzen.environment`) in
which outcomes are independently re-derivable from complete state, action, exogenous input, and
seed.

**G1a.** Define world growth operationally: durable changes to locations/resources, artifacts and
capabilities, contracts/markets/institutions, norms/beliefs/manuals, and agent roles or lineages.
Growth must arise from declared world processes and agent actions, not hidden evaluator edits.

**G1b.** Keep extensibility bounded: new mechanics are typed, versioned capability packages that
pass sandbox, replay, intervention, and resource-bound checks before becoming part of the world.

**G2.** Populate that environment with 10–30 active cognitive agents plus optional deterministic
background population processes. Agent diversity is represented by an explicit behavioral/social
ontology (needs, drives, skills, roles, affiliations, memory, communication, norms, and
lineage), not by an undefined claim to simulate real people.

**G2a.** Maintain diversity with a Quality-Diversity archive and report coverage, persistence,
extinction, replacement, specialization, and lineage metrics—not only a single entropy number.

**G2b.** Implement the original developmental-agent objective: birth as a child with a randomized
bounded equation over pride, greed, lust, envy, gluttony, wrath, sloth and Null. Age/context alter
motivational ratios; experience determines acquired skills. Living parents can teach children;
temperament, cultural knowledge and neural weights remain separate inheritance channels.
The eight dimensions are synthetic design choices, not a complete psychological taxonomy.
See [agent design](subsystems/agents/README.md) for equations, lifecycle and validation controls.

**G3.** Give that population an economy, institutions, and a fast, falsifiable knowledge-transfer
mechanism (`evolzen.economy`) without letting it collapse into recursive self-training. The
"real-data floor" is operationalized as a provenance floor over human-authored rules, external
documents, human demonstrations, or independently generated simulator traces; simulator output
must not be mislabeled as external data.

**G4.** Replace "agents discover engineering via pure RL" with a bounded actor/synthesizer/
verifier hypothesis-formation loop (`evolzen.exploration`), backed by a versioned verified-rule
library (`evolzen.library`). The library is non-destructive but supports supersession and
context-specific validity when the world legitimately changes.

**G5.** Build prediction and recognition components (`evolzen.predictor` +
`evolzen.recognition`) that learn from the population and world through a verification-gated
pipeline. The JEPA + wake-sleep combination is a proposed research variant, not an established
architecture or guaranteed source of generality. All generated code remains behind
`evolzen.containment`.

**G6.** Evaluate both persistent-world growth and fresh-world adaptation in
`evolzen.evaluation`. The fresh-world score is an EvolZen Action Efficiency (EAE) metric inspired
by the rationale of RHAE, not presented as an ARC-AGI-3 result unless the protocol is formally
compatible. Human or frontier references are used only under matched observations, actions, and
time budgets.

**G7 (this document's own scope).** Phase 0: ship a working, dependency-locked, documented,
typed codebase — this repository — so that G1-G6 can be pursued by a team of more than one
person working in parallel, without first solving engineering-setup problems.

## 4. Non-goals

**NG1.** This project does not claim, at any point, proximity to artificial general intelligence,
general emotional intelligence, or a model of real human psychology. Every requirement below is
scoped to a specific, falsifiable metric.

**NG2.** This project does not attempt to scale the agent population or the environment beyond
what the stated hardware (AGX Spark, DGX Spark, A6000) can run.

**NG3.** This project does not attempt to solve general catastrophic-forgetting mitigation,
generalizable causal discovery from unstructured trajectories, formally verified open-ended
alignment, or unrestricted open-ended world invention. It uses bounded mechanisms and reports
where they fall short.

**NG4.** Phase 0 does not implement the world engine, but the research direction is no longer an
undecided three-way candidate list. Phase 1.1 must specify the persistent social-sandbox contract;
negotiation, markets, and code tasks may be contained subsystems or evaluation slices, not
substitutes for the world itself.

**NG5.** This project does not introduce artificial groupings of its nine subsystems into a
smaller number of "parts" or installable packages for the sake of tidiness. If a future
contributor is tempted to reintroduce a "Segment 1/2" or "World/Observer" style split, read
[ADR 0003](adr/0003-nine-subsystems-not-two-packages.md) first — this has already been tried
twice and reverted twice.

## 5. Users & stakeholders

| Stakeholder | Interest |
|---|---|
| Research team (implementers) | A working codebase to build the nine subsystems inside; clear per-subsystem ownership; CI/CD that doesn't block parallel work (§12). |
| Academic advisor / reviewers | A falsifiable research question, an honest evaluation methodology, and a paper-ready accounting of what changed and why across design iterations. |
| Future maintainers | Documentation and typed interfaces sufficient to pick up a single subsystem's implementation without reverse-engineering the whole system. |
| AI coding agents assisting the team | Repository-root `AGENTS.md` — machine-readable setup, conventions, and hard constraints. |

## 6. System overview

One Python package (`evolzen`), nine subsystems, one shared foundation. Full detail in
[`ARCHITECTURE.md`](ARCHITECTURE.md); the shape:

```
[environment] -> [agents] -> [economy] -> [exploration] -> [library]
                                                                 |
                              verified transitions + rule library + manuals
                                                                 |
                                                                 v
     [predictor] -> [containment] -> [recognition] -> [evaluation]
```

The subsystems jointly maintain a persistent world, a heterogeneous population, executable
hypotheses, and measured learning components. The transition data is mechanistically generated and
verifiable; it is not called causal merely because it can be replayed. `evolzen.containment`
protects every subsystem that executes agent-originated or synthesized code.

## 7. Requirements (functional, by subsystem)

| ID | Requirement | Phase | Subsystem |
|---|---|---|---|
| FR-1 | A transition is replayable from complete state, action, exogenous input, and seed; hidden mutable state is forbidden. | 1.1 | `evolzen.environment` |
| FR-2 | The world persists through snapshots and event logs, and records durable growth in resources, artifacts/capabilities, institutions, norms, and agent roles/lineages. | 1.1 | `evolzen.environment` |
| FR-3 | The active population (10–30 cognitive agents) uses a declared behavioral/social ontology; diversity coverage, persistence, extinction, replacement, and specialization are tracked. | 1.2 | `evolzen.agents` |
| FR-4 | Knowledge transfer uses falsifiable, revisable manuals with explicit provenance classes and a configured provenance floor. | 1.3 | `evolzen.economy` |
| FR-5 | Candidate rules or capability packages pass sandbox execution, exact replay, held-out combinations, and at least one controlled intervention before promotion. | 1.4 | `evolzen.exploration` |
| FR-6 | Verified rules are immutable records with validity context and supersession links; historical rules remain readable and are never silently overwritten. | 1.5 | `evolzen.library` |
| FR-7 | Prediction updates use verifiable outcomes plus rehearsal, and report forward transfer, backward transfer, forgetting, adaptation latency, and update cost. | 2.1 | `evolzen.predictor` |
| FR-8 | All synthesized or self-modified code executes inside the containment boundary; backend deployment and kill-switch tests are reported separately from interface tests. | 2.2 | `evolzen.containment` |
| FR-9 | The recognition model is evaluated through the declared ablation matrix and must demonstrate benefit separately on persistent-world and fresh-world tracks. | 2.3 | `evolzen.recognition` |
| FR-10 | Evaluation includes persistent-world longitudinal runs and held-out seeds/mechanic combinations, using EAE rather than calling a custom score ARC-AGI-3 RHAE. | 2.4 | `evolzen.evaluation` |
| FR-11 | The final report discloses reused-versus-fresh performance, world-growth metrics, diversity metrics, failure/extinction events, and all ablation cells. | 2.5 | `evolzen.evaluation` |
| FR-12 | Birth equations are seeded, finite, versioned numerical data with exactly eight ordered coordinates; no executable equation strings. | 1.2 | `evolzen.agents` |
| FR-13 | Child development, living-parent teaching, maturity and terminal expiry use a monotonic world clock; age and advice never automatically confer mastery. | 1.2 | `evolzen.agents` |
| FR-14 | Learning uses trusted identity-matched outcomes; parental advice, own evidence and validation scores remain separate. | 1.2 | `evolzen.agents`, `evolzen.evaluation` |
| FR-15 | Cultural-transfer and evolution claims compare matched experience/compute across generations, with held-out families/mechanics and no final-test fitness feedback. | 1.2–2.5 | `evolzen.agents`, `evolzen.evaluation` |

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Every schema shared across subsystem boundaries lives in exactly one place (`evolzen.schemas`) and is type-checked against every importer. |
| NFR-2 | The base dependency set installs and passes tests on a CPU-only machine; GPU-only packages are opt-in extras (see [ADR 0002](adr/0002-dependency-stack-and-optional-extras.md)). |
| NFR-3 | No agent-generated or self-modified code executes outside `evolzen.containment`, even during early development. |
| NFR-4 | Every subsystem's design decision traces to either a citation (`docs/research/references.bib`) or an explicit "this is untested, flagged" note; source status (peer-reviewed, preprint, vendor report, or unverified) is recorded. |
| NFR-5 | CI (lint, type-check, test) runs on every push, path-filtered per subsystem so a change to one doesn't block feedback on another. |
| NFR-6 | The whole project remains **one installable package** — no future revision should re-fragment it into multiple packages/workspaces without a new ADR justifying the specific problem that solves. |

## 9. Success metrics (project-level)

- **World growth:** durable, independently re-playable growth events per run, separated by
  artifact/capability, institution, norm, market, and role/lineage categories.
- **World health:** resource conservation, bounded state growth, recovery after declared shocks,
  and absence of evaluator-injected milestone events.
- **Population diversity:** QD-archive coverage plus type occupancy, persistence, extinction,
  replacement, specialization, and lineage diversity across ≥ 5 generations.
- **Forgetting and transfer:** regression performance, forward transfer, backward transfer,
  forgetting, adaptation latency, and update cost under a declared replay budget.
- **Recognition-model ablation:** a measured delta (positive, negative, or null) on both
  persistent-world and fresh-world tracks.
- **Fresh-world efficiency:** EAE on held-out seeds and mechanic combinations, with matched human
  or frontier references only where the protocol is comparable.
- **Exposure gap:** reused-versus-fresh performance is explicitly measured and reported.

## 10. Milestones & timeline

See [`ARCHITECTURE.md`](ARCHITECTURE.md) §9 for the phase-by-phase timeline. Phase 0 (this
repository) is complete as a scaffold. Phase 1.1 is the next milestone and must first freeze the
persistent-world contract, agent ontology, replay semantics, and hardware pilot gates before any
full population or learning claim is scheduled.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| The world grows only because the evaluator injects milestones, so “independent growth” is narrative rather than a property of the system. | Event-sourced provenance, no hidden evaluator writes during evaluation, held-out world seeds, and a growth ledger that attributes every durable change to an endogenous process, an agent action, or a declared exogenous input. |
| “All types of people” becomes an untestable claim about human psychology or demographics. | Use an explicit behavioral/social ontology and report coverage of observable traits, roles, capabilities, relationships, norms, and lineages; do not claim realism about actual people. |
| Exact replay is mistaken for causal understanding. | Add controlled interventions, held-out transition combinations, hidden-state checks, and adversarial replay; use “mechanistically verifiable” unless causal identification is demonstrated. |
| A frozen rule library cannot represent legitimate world change. | Keep immutable historical entries, attach validity context, and add explicit supersession/version links rather than overwriting or silently routing around old rules. |
| `evolzen.recognition`'s JEPA + wake-sleep fusion is the least de-risked component in the whole plan — proposed in the literature but not yet demonstrated as one system. | Scheduled with the largest buffer of any phase (7-10 weeks); evaluated via an ablation matrix that produces a useful result even if the fusion underperforms either half alone. |
| Domain transfer from clean discrete tasks to a persistent social sandbox may fail. | Treat the clean replication as a calibration baseline, then run a separate domain-transfer experiment; do not use the clean result as evidence for social generalization. |
| Population diversity collapse (a documented failure mode in multi-agent LLM systems). | QD-archive selection plus concrete, literature-backed population-design rules (see `evolzen.agents`'s README) rather than an assumption that diversity will emerge. |
| Evaluation rewards accumulated familiarity instead of world growth or fresh adaptation. | Separate persistent-world and fresh-world tracks, prohibit reuse of final held-out seeds, and disclose exposure, manual access, and replay history for every score. |
| Firecracker/gVisor is treated as secure by name without a deployed threat-model test. | Separate interface, backend, and hardware acceptance gates; fail closed until resource, egress, logging, kill-switch, and recovery tests pass on the target host. |
| The three-device rig cannot sustain the claimed population, world tick rate, logs, or training cadence. | Add a hardware pilot before Phase 1.2: measure model memory, tokens/sec, action latency, world ticks/sec, sandbox density, storage growth, and training throughput. |
| Scope creep back toward an AGI claim. | Every phase doc, README, `AGENTS.md`, and this PRD states the honest ceiling explicitly (§4); treat any documentation or code comment that overclaims as a bug. |
| Naming/structure drift — reintroducing an artificial package-level split. | [ADR 0003](adr/0003-nine-subsystems-not-two-packages.md) documents why this was tried and reverted twice; NG5 above makes it an explicit non-goal. |
| Multiple contributors working in parallel produce `uv.lock` merge conflicts or silently drift on the shared schema contract. | See §12 and [`docs/ci-cd.md`](ci-cd.md) — path-filtered CI, CODEOWNERS review routing, and a documented `uv.lock` conflict-resolution procedure. |

## 12. Parallel workstreams & team structure

The nine-subsystem architecture is deliberately structured so independent people can work
concurrently, as long as the shared contract in `evolzen.schemas` (and the rest of the
foundation: `config.py`, `logging.py`, `tracking.py`, `storage/`) is treated as a jointly-owned,
carefully-changed interface.

| Workstream | Depends on | Can start once... |
|---|---|---|
| `evolzen.environment` | `evolzen.schemas` | The persistent-world contract, transition semantics, and hardware pilot plan are signed off. |
| `evolzen.agents` | `evolzen.environment`'s `Action` shape | The domain's `Action` shape is settled, even in draft form. |
| `evolzen.economy` | `evolzen.agents` producing real behavior | Agents can act and the world can persist at least one durable artifact or institution. |
| `evolzen.exploration` | `evolzen.environment`'s `Transition` format is stable | The environment protocol has a minimal working implementation. |
| `evolzen.library` | `evolzen.exploration` producing `CandidateRule`s | Exploration exists, even producing trivial rules. |
| `evolzen.containment` | Nothing | **Immediately** — doesn't depend on the environment domain at all; per `SECURITY.md` should be stood up early regardless. |
| `evolzen.predictor` | Real transition data | The environment is producing genuine (not fixture) transitions. |
| `evolzen.recognition` | `evolzen.library`, `evolzen.economy.manuals` | Both have real (not fixture) content — interface work against fixtures can start earlier. |
| `evolzen.evaluation` | Everything else, functionally | A full pipeline exists to evaluate — though the procedural-generator interface can be built early. |

**Coordination points that need explicit sign-off across whichever subsystems are affected:**
any change to `evolzen.schemas`, any change to the exact-match verification standard shared by
`evolzen.exploration` and `evolzen.containment`, and any change to `SECURITY.md`'s containment
requirements.

**Mechanics:** see [`docs/ci-cd.md`](ci-cd.md) for path-filtered CI and `uv.lock` conflict
resolution, and repository `.github/CODEOWNERS` for review routing by subsystem.

## 13. Out of scope

- Implementing a voxel/DEM physics engine or claiming physical realism.
- Provisioning the actual hardware-isolated sandboxing infrastructure (Firecracker/gVisor) on
  the DGX Spark — infrastructure work, not a software requirement of this repository.
- Simulating real human demographics, consciousness, emotions, or moral status. Agents are
  synthetic behavioral entities defined by an explicit ontology.
- Unrestricted open-ended invention of arbitrary new executable mechanics. Extensions must remain
  typed, versioned, bounded, and verifiable.
- Any claim about real-world deployment, commercialization, or production use of any component
  built under this project.

## 14. Glossary

| Term | Meaning |
|---|---|
| Transition | One `(State, Action, ExogenousInput, Seed) -> (Emission, next State)` record — the atomic unit of replayable data (`evolzen.schemas.transition`). |
| Persistent world | A versioned world state that survives episodes through snapshots and an append-only event log. |
| World growth | A durable, attributable change in an allowed world-growth category: resource/location, artifact/capability, institution/market, norm/belief/manual, or role/lineage. |
| Agent ontology | The declared schema of observable needs, drives, skills, roles, affiliations, memory, communication, norms, capabilities, and lineage. |
| Verified rule | A candidate world-model hypothesis that has passed exact-match replay against recorded transitions. |
| EAE | EvolZen Action Efficiency — this project's action-cost metric for fresh-world adaptation, inspired by RHAE but not interchangeable with ARC-AGI-3 RHAE. |
| RHAE | Relative Human Action Efficiency — the ARC-AGI-3 metric; use its name only when the official protocol is actually followed. |
| Drive-vector | A low-dimensional, evolvable coefficient vector shaping one agent's reward function (`evolzen.schemas.drive_vector`). |
| Manual | A falsifiable, actively-revised natural-language knowledge note shared between agents and consumed by the recognition model. |

## 15. References

See [`docs/research/references.bib`](research/references.bib) for the full citation list and
[`docs/research/literature-review.md`](research/literature-review.md) for the six research
threads this design draws on.
