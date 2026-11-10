# Comparative Landscape (reviewed 2026-10-21)

`docs/research/literature-review.md` gives the six-thread summary mapped to subsystems. This
document is the fuller picture behind it — the source-status notes, dated benchmark context, and
reasoning that shaped the major design decisions in `docs/ARCHITECTURE.md`, kept in one place so
claims do not have to be re-derived per subsystem.

## The field's own yardstick

ARC-AGI-3 is relevant because it operationalizes one important question: how efficiently can a
system learn an unfamiliar interactive task under a fixed action/observation protocol. It is not a
universal definition of general intelligence and its leaderboard is date-sensitive. The official
ARC material distinguishes public progress from blind evaluation; third-party leaderboard
summaries should not be used as permanent baselines. EvolZen records the benchmark date and source
when it cites ARC-AGI-3, and uses its own EAE metric for a custom world unless the official
protocol is followed exactly [arcprize2026].

## The public-set/private-set gap — the single most load-bearing fact in this design

A different, important pattern remains: specialized agent harnesses and persistent manuals can
substantially improve performance on a reused public set. That is an exposure-regime result, not
automatically evidence of cold-start generalization. Vendor or third-party reports are retained as
case studies, labeled as such, and are not treated as independent replication [agno2026manual].

Read this as a methodological warning: reused-set performance and fresh-set performance answer
different questions. The exact gap is not a permanent constant and must be re-measured for each
system, exposure protocol, model, and benchmark release.

This is why `evolzen.evaluation.procedural_env_gen` exists at all, and why it's a hard
requirement rather than a nice-to-have: `evolzen.evaluation`'s held-out testing must be designed
so it can't quietly collapse into measuring the first thing while believing it measures the
second. See `docs/phases/2.4-2.5-evaluation.md` and `evolzen.evaluation.report.EvaluationReport`,
which makes the reused-vs-fresh gap a required field, not optional.

## Programmatic world-model synthesis

Several recent approaches use actor/synthesizer/verifier systems that build an executable world
model from interaction and check it against replay — OPINE-World [opineworld2026], Tycho's active
identification formalization [tycho2026], and coding-agent-based variants
[executableworldmodels2026]. These are relevant design precedents, not proof that the method is
the field's universal leader or that it transfers to a persistent social sandbox. EvolZen may use
an existing coding-agent harness as a candidate synthesizer, but all generated code remains behind
containment and the transfer result is an explicit experiment.

## Representation learning and library learning

LeJEPA and related JEPA work provide candidate objectives for learning representations, while
DreamCoder provides a precedent for wake-sleep library learning [lejepa2025, dreamcoder2021].
The proposed EvolZen combination is not assumed to be necessary, novel, or effective: it must be
compared with simpler state encoders, symbolic baselines, and manual-only conditions. A similar
2026 preprint may motivate the hypothesis, but it does not validate the implementation here.

## Continual learning remains an open engineering risk

Continual learning remains an empirical risk rather than a solved property. Reported degradation
varies with model, task sequence, metric, and update regime [tfgn2026]. Those numbers are not a
universal baseline for EvolZen; the predictor phase must reproduce a matched protocol and report
forgetting, spurious forgetting, forward transfer, backward transfer, adaptation latency, and
update cost. A rehearsal buffer is a candidate mitigation, not a guarantee.

## Recent agent-evolution precedents

DGM and CORAL are relevant design precedents for empirically validated self-modification,
archives, persistent memory, and safeguard checklists [dgm2026, coral2026]. They do not establish
that small local LLM agents with drive vectors will evolve useful social types or grow a persistent
world. EvolZen treats those transfers as hypotheses requiring matched ablations.

## Diversity collapse is a testable population risk

A cited 2026 study reports three actionable patterns in a specific multi-agent ideation setting
[diversitycollapse2026]. EvolZen treats them as hypotheses to reproduce: base-model alignment,
authority structure, communication density, and group size may affect semantic diversity. They do
not automatically predict diversity of persistent social roles or world growth.

## Containment has moved past cgroup/eBPF

The containment literature motivates hardware isolation, default-deny capabilities, evaluator
separation, resource ceilings, and recovery testing for long-running code-generating agents
[sidikrokach2026, safetyopenended2025]. The repository does not call any backend a “default” or
secure by name: the selected Firecracker/gVisor deployment must pass a target-host threat model,
and behavior-sensitive governance may only tighten a static policy until separately reviewed.

## Full reference list

See [`references.bib`](references.bib).
