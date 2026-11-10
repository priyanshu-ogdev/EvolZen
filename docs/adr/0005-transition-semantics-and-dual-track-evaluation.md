# ADR 0005: Explicit transition semantics and dual-track evaluation

**Status:** Accepted

## Context

The existing documents call the environment a deterministic Moore machine while also requiring
outcomes to be re-derived from `(state, action)`. Strict Moore-machine emissions depend on state;
the project's interactive contract is an action-conditioned transition system. The existing
evaluation also focuses on fresh mini-environments, which is useful for transfer but does not
measure whether a persistent world grows or remains healthy over time.

## Decision

The normative environment contract is:

```text
(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})
```

The transition is deterministic for a fixed complete state, action, exogenous-input record, and
seed. The repository may retain `moore_machine.py` as a compatibility-oriented module name, but
documentation must call the formal object a **seeded, typed interactive transition system** (or a
Moore-inspired rendered state machine), not rely on “Moore” as shorthand for causal validity.

Evaluation has two mandatory tracks:

1. **Persistent-world track:** long-horizon runs measure durable world growth, population/type
   diversity, economic/ecological stability, adaptation latency, and recovery from shocks.
2. **Fresh-world transfer track:** procedurally generated held-out seeds and held-out mechanic
   combinations measure action-efficient adaptation. The metric is **EvolZen Action Efficiency
   (EAE)**, inspired by the rationale of RHAE but not presented as an ARC-AGI-3 score unless the
   task and scoring protocol are formally compatible.

The two tracks are reported separately and never collapsed into one headline number.

## Consequences

- Exact replay is correctly treated as a mechanistic verification property, not proof of causal
  identification or human-intent understanding.
- Controlled interventions, held-out transition combinations, and hidden-state checks are required
  for causal claims.
- A system can improve on one track while regressing on the other; the report must preserve that
  distinction.
- Human and frontier-model reference scores are only used when the reference system receives the
  same observations, action space, and time budget as EvolZen.
