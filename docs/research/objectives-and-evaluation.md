# Research Objectives & Evaluation Standard

**Status:** Phase 0 scaffolding is complete and code baselines exist for Phase 1.1 (`evolzen.environment`, `schemas/world.py`, `TransitionLogStore`), Phase 1.2-numerical (`agents/development/`), and Phase 1.5 (`evolzen.library`); **no empirical result is claimed yet**.  
**Scope:** defines what EvolZen is trying to learn, what counts as evidence, and which comparisons
must be completed before a paper claim is written.

## 1. Target definition

EvolZen does not target AGI, emotional intelligence, real-human psychology, or universal laws of
civilization. Its target is a bounded, testable system with two separable capabilities:

1. **Persistent world growth:** a seeded social sandbox changes durably through declared world
   processes and agent actions, producing attributable artifacts, capabilities, institutions,
   norms, markets, roles, and lineages without evaluator-injected milestones.
2. **Efficient adaptation:** a predictor/recognition system adapts to held-out world seeds and
   mechanic combinations with fewer costly exploratory actions than declared baselines.

World growth is not evidence of learning generality, and fresh-world adaptation is not evidence
that the world itself is socially realistic. Both must be measured separately.

## 2. Research questions

The original developmental-agent question is specified in
[agent evaluation](../subsystems/agents/evaluation.md): do birth-time eight-drive equations,
age/context modulation, personal learning and living-parent teaching produce useful adaptation
or cultural accumulation beyond matched simpler controls? The new local code is a numerical
baseline, not evidence of neural self-training. The detailed page supplies a proposed EAE formula,
pilot budget, split rules, uncertainty unit and implementation gates.

### RQ1 — Can the world grow independently?

Under a fixed transition contract, can the population produce durable world changes beyond a fixed
scripted baseline, while preserving replayability, resource/institution invariants, and recovery
after declared shocks?

### RQ2 — Does behavioral diversity matter?

Does a typed heterogeneous population with QD selection produce more persistent specialization,
lineage diversity, and world-growth coverage than a matched homogeneous or fitness-only population?

### RQ3 — Does verified exploration improve discovery?

Does actor/synthesizer/verifier exploration improve held-out transition and intervention performance
relative to passive exploration or a no-synthesis baseline, without increasing false promotions?

### RQ4 — Does the learning system improve adaptation?

Do predictor and recognition components reduce adaptation latency or exploratory action cost on fresh
world seeds and held-out mechanic combinations compared with library-only, manual-only, and
recognition-disabled baselines?

### RQ5 — Does continual learning retain capability?

Under a declared update and replay budget, how do rehearsal, task-free training, and other ablations
affect backward transfer, forward transfer, spurious forgetting, true forgetting, and update cost?

### RQ6 — Is execution controlled?

Can the containment boundary demonstrate fail-closed capability control, bounded resources,
complete logging, kill-switch behavior, recovery, and evaluator separation on the target host?

## 3. Proposed hypotheses (registration pending)

These are hypotheses, not commitments to positive results:

- **H1:** the persistent-world condition will produce more durable growth categories than the
  scripted/no-growth baseline.
- **H2:** QD selection and the declared agent ontology will preserve more behavioral/type coverage
  than fitness-only or homogeneous-population baselines.
- **H3:** verified exploration will improve held-out transition/intervention performance at a
  measurable exploration cost.
- **H4:** recognition-enabled systems will reduce fresh-world adaptation latency or action cost in
  at least one track without unacceptable regression in the persistent-world track.
- **H5:** replay/rehearsal will reduce backward degradation relative to matched no-replay updates,
  subject to its data and compute budget.
- **H6:** the containment implementation will satisfy all mandatory invariants before any generated
  code is allowed into a long-running experiment.

Null and negative results are valid outcomes. No hypothesis is considered supported by an
in-sandbox score alone.

## 4. Evaluation tracks

### Track A — Persistent-world growth

Each run starts from a recorded seed and proceeds through a long-horizon event-sourced world.
During the scored interval:

- evaluator writes are disabled except for pre-declared exogenous inputs;
- every durable change receives a growth-event attribution;
- snapshots and event logs support independent replay;
- shocks, recovery windows, and resource budgets are declared before the run; and
- the run records agent exposure, manuals, replay access, rule versions, and capability promotions.

Primary measurements:

- growth-event count and category coverage;
- persistence of artifacts, institutions, norms, roles, and lineages;
- world-health invariants and recovery time;
- population/type occupancy, extinction, replacement, specialization, and lineage diversity;
- resource concentration and collapse indicators; and
- evaluator-injection violations.

### Track B — Fresh-world adaptation

The evaluator generates held-out world seeds and held-out combinations of mechanics after training
and development decisions are frozen. Final held-out instances are never reused for tuning.

Primary measurements:

- EvolZen Action Efficiency (EAE);
- adaptation latency;
- exploratory action count and cost;
- success under a fixed action/time budget;
- intervention response on held-out variables;
- compute and token cost; and
- failure, abstention, and recovery behavior.

EAE is an EvolZen metric inspired by the motivation of action-efficiency benchmarks. It is not
reported as official ARC-AGI-3 RHAE unless the official task and scoring protocol are followed.

## 5. Required baselines and ablations

The final evaluation must include, at minimum:

1. scripted/no-growth world versus endogenous-growth world;
2. homogeneous population versus typed heterogeneous population;
3. fitness-only selection versus QD selection;
4. no-economy/no-institution condition versus economy/institution condition;
5. passive exploration versus explanation-gap-guided exploration;
6. no-synthesizer condition versus sandboxed synthesizer/verifier;
7. library-only, manual-only, recognition-disabled, JEPA-only, wake-sleep-only, and combined
   recognition conditions;
8. rehearsal/replay versus matched no-replay continual updates; and
9. retrieval-assisted versus retrieval-disabled conditions, with all external assistance logged.

Containment is never removed as a convenience ablation. Security tests vary the deliberate
violation, not whether the boundary exists.

## 6. Data and split rules

- Development, validation, and final held-out seeds are generated from disjoint seed registries.
- Mechanic combinations in the final fresh-world track are not exposed during tuning.
- Reused-world scores and fresh-world scores are reported separately.
- Manual access, replay access, retrieval access, rule versions, and exposure count are recorded
  for every result.
- Synthetic output is labeled as synthetic. It cannot satisfy an external/provenance floor merely
  because it was generated by a different model.
- Human or frontier references receive the same observation, action, information, and time budget.

## 7. Statistical and reporting standard

Before the final run, record:

- seed lists or seed-generation versions;
- baseline definitions and ablation matrix;
- primary and secondary endpoints;
- stopping rules and exclusion rules;
- compute, token, replay, and exposure budgets; and
- the planned aggregation and uncertainty method.

Report per-seed results, aggregate uncertainty, failures, extinctions, abstentions, and null
results. Do not select a headline metric after inspecting which result is largest. A paper claim
must point to a measured field in `EvaluationReport` and to the corresponding run artifacts.

## 8. Decision gates

| Gate | Required evidence before proceeding |
|---|---|
| G0 — contract | Transition, snapshot, growth-event, agent-profile, provenance, and capability contracts are frozen. |
| G1 — world | Replay works; growth is attributable; invariants and shock recovery are measured. |
| G2 — population | Capacity envelope and five-generation diversity report exist. |
| G3 — exploration | Replay/intervention promotion checks and false-promotion measurements exist. |
| G4 — containment | Interface, backend, and target-host acceptance tests pass. |
| G5 — learning | Predictor baselines and transfer/forgetting curves exist before JEPA fusion claims. |
| G6 — publication | Both evaluation tracks, all required ablations, exposure history, and limitations are reported. |

The project plan is not considered complete until G0–G6 are satisfied. As of 2026-11-12 (`env` @ `81ee6eb`), Phase 0 scaffolding is complete and code baselines exist for Phase 1.1 (`evolzen.environment`, `schemas/world.py`, `TransitionLogStore`), Phase 1.2-numerical (`agents/development/`), and Phase 1.5 (`evolzen.library`), while remaining G0 items (`AgentProfile`, `ProvenanceRecord`, and Phase 1.1 hardening `ENV-01`–`ENV-08`) are still open. **G1–G6 empirical gates remain unsatisfied, and no empirical result is claimed yet.**
