# evolzen.library — Phase 1.5

**Goal:** store verified rules and capability packages as immutable historical entries while
supporting explicit validity context and supersession when the world changes.

Full research design: [`docs/phases/1.5-library.md`](../../../docs/phases/1.5-library.md).

## What's here

| File | Purpose |
|---|---|
| [`rule_library.py`](rule_library.py) | `RuleLibrary` — immutable entries, context-aware routing, and explicit supersession rather than silent overwrite. |

## How to build this

1. Keep the representation consistent with the seeded typed transition contract in
   `evolzen.environment` (the `moore_machine.py` filename is retained for compatibility)
   — transition logs, library entries, and the synthesizer's hypotheses should all speak the
   same typed language, not three ad-hoc formats needing translation layers.
2. Implement routing confidence only as a hypothesis-ranking signal. It must never substitute for
   replay/intervention verification; `evolzen.recognition` later provides a learned router, but
   routing confidence is not proof of validity.
3. Add validity context, provenance, evidence links, supersession/deprecation, and audit records
   before supporting legitimate world-rule changes.

**Success metric:** historical entries remain readable and replayable across at least three rounds
of additions; new entries improve held-out performance; and every supersession is explicit,
reversible, and attributable to a measured context change.

**Depends on:** `evolzen.exploration.synthesizer` (the `CandidateRule` type it stores).
**Depended on by:** `evolzen.recognition` (restructures this library as a sparse
mixture-of-experts and routes queries against it), `evolzen.containment` (Phase 2.2 promotion
gate writes here too, under the same verification standard).
