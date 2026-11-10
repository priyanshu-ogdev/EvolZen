# ADR 0006: Developmental eight-drive agents with separate learning and inheritance

**Date:** October 24, 2026. **Status:** Accepted for the numerical baseline; neural and population
integration remain proposed and empirically untested.

## Context

The user's original model requires birth as a child, a randomized equation governing seven sins
and Null, development with age, teaching while parents are alive, and intergenerational evolution.
The scaffold instead has five static coefficients and no lifecycle. Replacing that public schema
silently would break inference, archive and tests while overstating neural capability.

## Decision

- Preserve all legacy five-drive types and methods. Add `schemas/development.py` and the cohesive
  `agents/development/` subpackage, documented under `docs/subsystems/agents/`.
- Fix the eight-coordinate order and treat labels as synthetic utility dimensions. Lust is
  nonsexual attraction/affiliation; Null is disengagement, distinct from sloth and death.
- Sample bounded coefficients at birth in a fixed tanh/softmax equation family. Do not execute
  generated equations or permit agents to change their reward evaluator.
- Separate immutable temperament, age, learned outcome estimates, parental advice and future
  adapter checkpoints. Neither birthdays nor teaching automatically certify competence.
- Permit living mature parents to teach descendants without disappearing on birth. New children
  start without personal evidence; numeric temperament inheritance is separate from knowledge.
- Implement a CPU-only numerical action/feedback loop and a bounded validated phenotype archive
  first. Keep LLM generation, weight updates, world execution and population scheduling explicit
  future milestones.
- Use external validation/retention/safety evidence for archive admission; final test data is never
  evolutionary fitness. Generated policy code remains behind Sandbox.

## Alternatives and consequences

Random source programs would create avoidable containment/numerical hazards. Literal neural-weight
crossover has different alignment problems from mixing explicitly aligned numeric coefficients.
Rank-by-age guarantees capacity growth without evidence of usefulness; it is not adopted.
Eight labels may be less useful than a simpler basis; the design includes neutral-label,
uniform-drive, five-drive and random-feature controls rather than assuming superiority.

The new path is usable independently of model serving but is not yet connected to the legacy CLI.
This costs an explicit later adapter migration, while avoiding silently dropping three dimensions.
Evidence and research limits: [agent evidence ledger](../subsystems/agents/evidence.md).
