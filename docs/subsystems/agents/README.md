# Developmental agents: seven sins plus Null

**Design version:** eight-drive-v1, October 24, 2026.
**Status:** a deterministic numerical baseline is implemented; no experiment has established
developmental intelligence, neural self-training, or population evolution.

## User-visible target

An agent is born as a child with its own randomized equation, acquires experience with age,
acts according to changing motivational ratios, learns from outcomes, and can be taught by living
parents. On maturation it can contribute temperament to a new child. A child does not receive
its parents' learned skills at birth. The world and host—not the agent—control permissions,
resource limits, clocks, births and authoritative outcome verification.

The original names are preserved: **pride, greed, lust, envy, gluttony, wrath, sloth, Null**.
These are fictional motivational coordinates, not moral ratings of agents or scientific
categories of humans. Lust means nonsexual attraction/affiliation in this implementation,
including all child-stage behavior. Reproduction is a population-management operation.
Null means no goal-directed engagement: waiting, resting or abstaining. It is not death,
depression, self-destruction, or a ninth drive.

## Read in order

1. [Motivation mathematics](motivation.md): operational meanings, randomized equations,
   normalization, action ranking, limits and alternatives.
2. [Lifecycle and inheritance](lifecycle.md): age, competence, overlapping generations,
   parenting and population control.
3. [Learning and evolution](learning.md): memory, empirical updates, lessons, future LLM
   training, validation gates and archive selection.
4. [Evaluation protocol](evaluation.md): falsifiable questions, controls and development gates.
5. [Engineering and delivery](engineering.md): source map, interfaces, status and integration.
6. [Research evidence](evidence.md): sources actually inspected and what they do not establish.

## A brain is more than its equation

The equation sets *preferences*, not beliefs or abilities. In the baseline, the learner stores
context/action outcome estimates. In the proposed neural path, a shared pretrained model generates
candidate plans from private observations and evidence-linked memories; the motivational layer
ranks those plans. Outcomes revise beliefs and skills, while a promotion gate governs weight
updates. No free-form internal monologue is evidence that reasoning or learning occurred.

Four clocks must be distinguished: world ticks, decision count, learning-update count and
generation number. Age alone grants neither knowledge nor a larger LoRA rank. A newborn based on
a pretrained LLM is *locally inexperienced*, not linguistically blank or biologically childlike.

## What exists now

- validated, immutable records and JSON snapshots;
- seeded birth equations and bounded coefficient inheritance;
- lifecycle boundaries with terminal expiry;
- eight-drive context/age/momentum dynamics and normalized ratios;
- deterministic safe-candidate ranking, using personal experience and capped parental advice;
- feedback-dependent online numerical updates, finite memory, parent teaching while alive;
- a capacity-limited phenotype archive with host validation/safety/retention gates;
- source tests covering these primitives (results must be reported separately).

Not implemented: a functioning world, LLM generation, private adapter training, episodic text
retrieval, reflective planning, persistent scheduler, population budget enforcement, automatic
QD-driven birth selection or deployed sandbox backend. Existing `Agent`/`DriveVector` code remains
the legacy five-coordinate path, not an implementation of this design.

See [ADR 0006](../../adr/0006-developmental-eight-drive-agents.md) and the source package under
`src/evolzen/agents/`.
