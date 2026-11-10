# Paper Outline

A skeleton for the research paper this project is meant to produce, mapping each section onto
material that already exists elsewhere in this repository. Fill in results as they're measured;
don't fill in claims ahead of measurement — every placeholder below says exactly what evidence
it's waiting on.

## Working title

*EvolZen: Measuring Persistent World Growth and Fresh-World Adaptation in a Grounded,
Evolutionarily-Diverse Multi-Agent Sandbox*

(Or shorter: *EvolZen: A Testbed for Generalization Efficiency in Grounded Multi-Agent Systems*.)

## Abstract

*Draft once Phase 2.4/2.5 results exist.* One paragraph: the two questions (does the world grow
durably under endogenous processes, and does the learning system improve fresh-world adaptation?),
the method (nine subsystems, briefly), the persistent-world and EAE results, the ablation outcome,
and the honest scope (bounded evidence about a defined sandbox — not a claim about general
intelligence, emotional intelligence, or real human psychology).

## 1. Introduction

- The difference between plausible narrative behavior and replayable, persistent world dynamics
  (`docs/PRD.md` §2, `docs/research/design-audit.md`).
- The two research questions this project tests (`docs/PRD.md` §1).
- Contribution statement: **draft from `docs/PRD.md` §1's summary sentence directly** — resist
  the temptation to strengthen it once results are in hand; if results support a stronger
  statement, that's a finding to report, not a reason to have written it earlier.

## 2. Related Work

Pull directly from `docs/research/literature-review.md` and `docs/research/landscape.md`. Six
threads, each with its own subsection: World Models, Continual Learning, Verified World-Model
Synthesis, Program-Synthesis Memory, Population Diversity, Data Provenance. State which
techniques are hypotheses, which are precedents, and how source status and exposure history
constrain the paper's evaluation design.

## 3. Method / Architecture

One subsection per subsystem, drawn from `docs/ARCHITECTURE.md` §3: `environment`, `agents`,
`economy`, `exploration`, `library`, `predictor`, `containment`, `recognition`, `evaluation`.
Each subsection: mechanism, why it was chosen over the alternative the original design used,
citation. This is close to a direct copy of `docs/ARCHITECTURE.md` §3, trimmed of
implementation-file references that don't belong in a paper (e.g., drop `moe_library.py`-style
pointers, keep the mechanism descriptions).

## 4. Design Evolution (optional section, or fold into Related Work / Appendix)

`docs/research/objectives-and-evaluation.md` is the authority for research questions, hypotheses,
baselines, split rules, and decision gates. `docs/research/design-evolution.md` in full is likely too long for the main paper body, but its
existence and structure (every mechanism traced from its original, unsupported version to a
cited, buildable one) is itself worth a paragraph — reviewers evaluating a design this iterative
benefit from seeing that the iteration was principled, not ad hoc. Consider an appendix with the
full table, and a one-paragraph summary in the main text pointing to it.

## 5. Evaluation

- **Setup:** the persistent-world generator and fresh-world generator
  (`evolzen.evaluation.procedural_env_gen`), with exposure, manual, replay, and seed history
  recorded for every run.
- **Persistent-world metrics:** durable growth, world health, population/type diversity,
  lineage persistence, shock recovery, and extinction/replacement (`docs/PRD.md` §9).
- **Learning metrics:** forgetting, forward/backward transfer, adaptation latency, and update cost.
- **Ablation matrix:** with/without recognition model x with/without manual layer x JEPA-only /
  wake-sleep-only / combined (`docs/phases/2.3-recognition.md`). Report all cells, not just the
  best one.
- **Fresh-world result:** EAE on genuinely unseen seeds/mechanic combinations. Use human or
  frontier reference points only when observations, action space, and time budget match; do not
  inherit ARC-AGI-3 numbers as if they were directly comparable.
- **Exposure result:** reused-vs-fresh performance and all manual/replay access history for this
  system specifically (`evolzen.evaluation.report.EvaluationReport` makes this required).

## 6. Results

*Empty until measured.* Structure the table to match `EvaluationReport`'s fields exactly, so
writing this section is substituting numbers into a pre-agreed shape rather than deciding what
to report after seeing what looks good.

## 7. Limitations & Honest Positioning

Draft directly from `docs/PRD.md` §4 (Non-Goals) and `docs/research/design-evolution.md`'s
closing section ("Why the ceiling holds regardless of any upgrade above"):

- Generality is bounded by task and world diversity — a result within this environment family is
  not evidence about real human psychology or general intelligence.
- No component here distills past its teacher without an external reward; everything is bounded
  by the base models plus whatever real signal `evolzen.environment` provides.
- If programmatic verification, the recognition model, or the proposed world-growth mechanisms
  fail on the persistent social sandbox, that is reported here as a finding, not omitted.

## 8. Conclusion

One paragraph, restating the defensible claim from `docs/PRD.md` §1 with the actual measured
result slotted in, and one sentence on what a negative result would still contribute to the
field (a citable answer that this specific combination doesn't transfer, ruling out a real
hypothesis other groups might otherwise spend time on).

## References

Generate from [`references.bib`](research/references.bib) directly — every citation used in this
outline already has an entry there.

## A note on scope creep, for whoever drafts this

The single most common way a paper drawn from this project could go wrong is tightening the
Abstract or Conclusion's language beyond what the persistent-world and fresh-world results
support — see
`AGENTS.md`'s "Safety-critical constraints" #4 and `docs/PRD.md` §4 (NG1). If a draft sentence
would read differently to a skeptical reviewer than to the person who ran the experiment, that's
the sentence to rewrite before submission, not after review.
