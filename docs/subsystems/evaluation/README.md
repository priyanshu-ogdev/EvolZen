# Evaluation integration

Authority: [Phases 2.4–2.5](../../phases/2.4-2.5-evaluation.md),
[system objectives](../../research/objectives-and-evaluation.md), and
[developmental protocol](../agents/evaluation.md).
Source package: `src/evolzen/evaluation/`.

Keep world growth, individual learning, cultural transfer and population selection as distinct
endpoints. Count teacher interactions, failed births, inactivity and discarded candidates in
budgets. Split by family and world mechanics, not random ticks from a shared life. Evolution
uses validation evidence; sealed final evaluations are never fitness feedback. Note: the
existing `rhae_scorer.py` and minimal `EvaluationReport` helpers are early scaffolding slated for
replacement by the per-episode `EAE_B` formula and full dual-track reporting contract.
