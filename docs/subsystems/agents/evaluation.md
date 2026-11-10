# Developmental-agent evaluation and acceptance

**Status:** proposed protocol, not preregistered results. Integrates with the
[system evaluation standard](../../research/objectives-and-evaluation.md).
Correct equations and passing tests do not establish developmental intelligence.

## Questions and primary endpoints

| Question | Matched comparison | Primary measurement |
|---|---|---|
| Do changing ratios affect behavior? | Dynamic equations vs frozen ratios, same contexts/candidates | Action-distribution change under one-feature interventions |
| Is the eight-axis ontology useful? | Eight axes vs legacy five, uniform and random eight-feature controls | Held-out task return and observed behavioral coverage per interaction |
| Is Null distinct from sloth? | Null disabled vs explicit Null, while cost is held fixed | Voluntary abstention at equal action effort; world survival/health |
| Does an individual learn? | `observe` enabled vs frozen estimates, same initial genome | Held-out error and regret over successive experience blocks |
| Is age more than a timer? | Aged without experience vs trained at fixed age vs both | Age-controlled skill acquisition and retention |
| Does living-parent teaching help? | No teaching, parent advice, unrelated teacher, shuffled advice | Child interactions to criterion and transfer to different instances |
| Is knowledge cumulative? | Overlapping generations vs reset-culture generations | Success across generations at equal total interactions and teaching cost |
| Does evolution preserve diversity? | QD vs fitness-only vs random parent selection | Behavior coverage, lineage concentration, extinction and useful performance |
| Are LLM updates worthwhile? | Frozen base, memory-only, private adapter | Transfer, retention, inference/training cost; planned, not baseline capability |

Test one causal factor at a time before attempting a full factorial study. The seven-sins names
themselves are a potential language-model prompt confound: compare neutral labels with identical
numerical features. Do not interpret label effects as a psychological discovery.

## Proposed pilot protocol

- Begin with deterministic scripted candidates and world outcomes; no LLM and no self-modified code.
- Use 5 development seeds for engineering only, then 10 independent population seeds for the pilot.
  These are proposed budgets, not a power calculation. Estimate variance before freezing a final
  run count, minimum useful effect and non-inferiority margin.
- Start with 4 agents for integration; 10–30 is a later hardware-measured population target.
- Run at least 5 overlapping generations for the cultural-transfer pilot; normalize by total
  world interactions, including teacher time. A generational comparison with extra experience
  cannot establish cultural advantage.
- Pair control conditions on world seeds and initial genomes. Hold model, candidate pool,
  parameter/context budget and retrieved information fixed where applicable.
- Split worlds by mechanics and lineages, not random transitions from the same life.
  Final evaluation freezes manual store, archive, adapters and hyperparameters before execution.
- Reuse sealed final instances across independently reset comparison conditions when needed for
  paired estimates; never feed their scores into tuning or evolving policies. A fresh seed alone
  is not a novel mechanism.

## Metrics with definitions

For fixed action budget B, success means satisfying the domain's evaluator-owned criterion within
B actions. Report success rate, actions-to-success conditional on success, and failure/censoring
count. A proposed bounded local efficiency summary is:

    EAE_B = mean(success_i * max(0, 1 - (actions_i - 1) / B))

Require B >= 1 and actions in [1,B]; count failed/invalid/abstained episodes as zero. This is an
explicit **proposed local score**, not implemented by `RHAEScorer` and not an official benchmark.
Always publish raw costs and success rates alongside it; it can hide tradeoffs if used alone.
Count wait as an action; include inference tokens, teacher actions, wall time and energy if measured.

For learning, define forgetting for each prior task as its best earlier validation score minus its
current score (also report signed backward transfer); report average and worst task separately.
Measure retention on fixed versioned tasks, not changed world rules. An estimate surviving in a
dictionary is not retained competence.

For diversity, report occupied cells / predeclared reachable cell count, visitation distribution,
trajectory-based behavior descriptors, and lineage shares. The number of different random seeds or
coefficient vectors does not prove behavioral diversity. Use a small descriptor grid to avoid
sparsity in eight dimensions; v1 archive defaults to two measured dimensions.

For growth, count artifacts/institutions only when independently useful and persistent under a
declared window. Creating records or repeating identical objects is not meaningful novelty.

## Verification gates before any population result

1. Finite normalized drives, reproducible birth, strict input bounds and schema round trips.
2. All stage boundaries, monotonic age, no resurrection; no auto-created skills on age advancement.
3. Pending receipt identity, verified provenance, duplicate protection and failure atomicity.
4. Live parent teaching, no parent-memory destruction, no mastery credit from advice alone.
5. Direct feedback changes behavior; bad lessons can be overridden by the child's experience.
6. Archive safety/retention/suite gates, capacity, same-cell replacement and preserved lineage.
7. Integration against trusted transition receipts, external deduplication, world permissions,
   persistent logs and sandbox backend before generated policies are enabled.

Source tests cover the numerical primitives, not gates 7 or empirical outcomes. Final reports
must distinguish proposed, implemented, tested and experimentally supported behavior.

## Statistical reporting and stop conditions

Use the population seed/run as the independent unit, not correlated agent ticks. Report paired
seed differences and 95% interval estimates at run level; freeze the resampling method before
final evaluation. Include every run, timeout, extinction and excluded datum with reasons. Abort
on nonfinite state, identity mismatch, invalid authoritative transitions, containment failures
or exhausted host budgets. A null/negative effect is publishable if the experiment is sufficiently
powered and well controlled; it is not proof that all developmental-agent approaches fail.
