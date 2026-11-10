# evolzen.environment — Phase 1.1

**Goal:** a persistent, event-sourced, discrete social sandbox with replayable typed transitions.
Verifiability and attributable world growth, not physical realism, are the non-negotiable
properties.

Full research design: [`docs/phases/1.1-environment.md`](../../../docs/phases/1.1-environment.md).

## What's here

| File | Purpose |
|---|---|
| [`engine.py`](engine.py) | The `Environment` protocol every concrete domain implementation must satisfy. |
| [`moore_machine.py`](moore_machine.py) | Phase 0 compatibility module for the seeded typed transition specification. |
## How to build this

1. Freeze the persistent-world contract, growth categories, and action vocabulary.
2. Implement `Environment.reset()` / `.step()` / `.is_terminal()` plus snapshot, branch, restore,
   and replay operations.
3. Confirm that every transition is re-derivable from complete state, action, exogenous input,
   and seed; hidden mutable state is a failure.
4. Add a growth ledger and world invariants before connecting LLM agents.
5. Wire `evolzen.storage.TransitionLogStore` to a concrete DuckDB schema matching the versioned
   world and transition contracts.

**Success metric:** replay determinism, durable growth in at least three allowed categories, and
recovery from a declared shock without evaluator-injected milestones. No mock environment is used
as evidence for this metric; the real adapter is still pending.

**Depends on:** `evolzen.schemas.transition`, `evolzen.storage`.
**Depended on by:** `evolzen.agents` (acts in it), `evolzen.exploration` (probes it),
`evolzen.predictor` (trains against its verifiable outcomes).
