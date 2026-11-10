# evolzen.exploration — Phase 1.4

**Goal:** use a bounded actor/synthesizer/verifier loop to propose typed rules and capability
packages for the persistent world. The loop is a design precedent, not proof that open-ended
social or technological discovery transfers to EvolZen.

Full research design: [`docs/phases/1.4-exploration.md`](../../../docs/phases/1.4-exploration.md).

## What's here

| File | Purpose |
|---|---|
| [`actor.py`](actor.py) | `Actor` — chooses what to probe next, prioritized by ontology error. |
| [`synthesizer.py`](synthesizer.py) | `Synthesizer` protocol + `CandidateRule` — proposes typed executable hypotheses or capability packages. |
| [`verifier.py`](verifier.py) | `Verifier` — checks replay, held-out transition combinations, interventions, and resource bounds before promotion. |

## How to build this

1. Use an existing coding-agent harness as a candidate synthesizer only if it can operate through
   `evolzen.containment.Sandbox`; never treat a scratch directory or restricted namespace as the
   security boundary.
2. Implement `Verifier.verify` to check exact replay, held-out transition combinations, at least
   one controlled intervention, declared validity context, and resource bounds.
3. Keep explanation-gap-guided exploration (`Actor`) and measure exploration cost, false promotion,
   and false rejection rather than assuming ontology error is sufficient.

**Success metric:** verified hypotheses beat a no-exploration baseline on held-out transitions and
interventions, with false promotion below the pre-registered threshold and no mutation outside the
versioned capability boundary.

**Depends on:** `evolzen.schemas.transition`, `evolzen.containment` (for safe execution).
**Depended on by:** `evolzen.library` (stores verified rules), `evolzen.containment` (Phase 2.2
reuses this exact verification standard for its own promotion gate).
