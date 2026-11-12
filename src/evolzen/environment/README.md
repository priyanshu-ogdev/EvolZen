# evolzen.environment — Phase 1.1

**Goal:** a persistent, event-sourced, discrete social sandbox with replayable typed transitions.
Verifiability and attributable world growth, not physical realism, are the non-negotiable
properties.

Full research design: [`docs/phases/1.1-environment.md`](../../../docs/phases/1.1-environment.md).

## What's here

| File | Purpose |
|---|---|
| [`engine.py`](engine.py) | `Environment` / `PersistentEnvironment` protocols and concrete `SocialSandboxEngine`. |
| [`moore_machine.py`](moore_machine.py) | Phase 0 compatibility spec (`MooreMachineSpec`) and `SOCIAL_SANDBOX_SPEC`. |
| [`world_state.py`](world_state.py) | Deterministic initial world builder (`build_default_world`) and seeded RNG (`derive_rng`). |
| [`invariants.py`](invariants.py) | World invariants (`check_invariants`): conservation, bounded state, ownership, monotonic clock. |
| [`growth.py`](growth.py) | Growth ledger extraction (`extract_growth_events`) and category summary. |
| [`replay.py`](replay.py) | Exact transition replay (`replay_transitions`, `replay_from_store`) and branching (`branch_from_snapshot`). |
| [`interventions.py`](interventions.py) | Controlled variable/action-withholding counterfactuals (`apply_intervention`). |
| [`adapter.py`](adapter.py) | Developmental-agent host bridge (`observe_features`, `legal_candidates`, `action_from_candidate`, `execute_decision`). |
| [`pettingzoo_env.py`](pettingzoo_env.py) | PettingZoo `AECEnv` wrapper (`SocialSandboxAECEnv`) backed by `SocialSandboxEngine`. |
| [`pilot.py`](pilot.py) | Local CPU throughput/storage benchmark helper (`run_environment_pilot`). |

## Status & verification

- Implemented in Phase 1.1: deterministic `(state, action, exogenous_input, seed) -> (emission, next_state)` transitions in `SocialSandboxEngine` with verified `CapabilityPackage` gating, DuckDB JSON/hash-chained event and snapshot/branch persistence (`TransitionLogStore`), exact replay (`replay_transitions`, `replay_from_store`) and branching (`branch_from_snapshot`), world invariants (`check_invariants`), attributable growth extraction (`extract_growth_events`) across all five `GrowthCategory` buckets, exogenous shock/regen handling, controlled counterfactual interventions (`apply_intervention`), the `evolzen.agents.development` host adapter (`adapter`), the `SocialSandboxAECEnv` PettingZoo `AECEnv` wrapper (`pettingzoo_env`), and local CPU benchmark helper (`run_environment_pilot`).
- Untested / pending external and downstream gates: empirical long-horizon multi-agent runs, `SocialSandboxAECEnv` learning-loop evaluation, target-hardware pilot measurements on DGX/AGX Spark, LLM population execution (Phase 1.2), full economy/manual integration (Phase 1.3), and sandboxed capability synthesis (Phases 1.4/2.2).

**Depends on:** `evolzen.schemas.transition`, `evolzen.schemas.world`, `evolzen.schemas.development`, `evolzen.storage`.
**Depended on by:** `evolzen.agents` (acts in it), `evolzen.exploration` (probes it),
`evolzen.predictor` (trains against its verifiable outcomes).
