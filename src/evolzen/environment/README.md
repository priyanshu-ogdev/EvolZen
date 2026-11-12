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

- Implemented in Phase 1.1: deterministic `(state, action, exogenous_input, seed) -> (emission, next_state)` transitions across all 17 `ActionType`s in `SocialSandboxEngine` with verified `CapabilityPackage` gating, DuckDB JSON/hash-chained event and snapshot/branch persistence (`TransitionLogStore`), exact replay (`replay_transitions`, `replay_from_store`) and branching (`branch_from_snapshot`), world invariants (`check_invariants`), attributable growth extraction (`extract_growth_events`) across all five `GrowthCategory` buckets, exogenous shock/regen handling, controlled counterfactual interventions (`apply_intervention`), the `evolzen.agents.development` host adapter (`adapter`), the `SocialSandboxAECEnv` PettingZoo `AECEnv` wrapper (`pettingzoo_env`), and local CPU benchmark helper (`run_environment_pilot`).
- Open Phase 1.1 hardening backlog (empirical metrics remain **untested** / unmeasured):
  - `replay_transitions` passes `recorded.state` instead of `current_state` into `engine.step`; `replay_from_store` drops `same_tick=True` transitions at `up_to_tick`; `apply_intervention` lacks sequence indexing and `initial_currency` reconciliation; `SocialSandboxAECEnv.step` lacks `exogenous_input`/`seed`/`TransitionLogStore` hooks.
  - `FR-2` bounds: `_handle_spawn_offspring` counts dead+living agents against `max_agents`, `WorldState` collections and `WorldAgentState.status` lack upper bounds, and `GrowthAttribution.ENDOGENOUS_PROCESS` has no active world-tick emitter.
  - `adapter.legal_candidates` surfaces 7 of 17 `ActionType`s (and `Discrete(10)` in `SocialSandboxAECEnv` covers basic local actions); `ContractRecord` cancel/expiry, `InstitutionRecord.contribution_rate`/treasury spending, `ArtifactRecord.durability` decay, and `NormRecord` behavioral effects remain partial/inactive.
  - All 18 `invariants.py` failure branches, Hypothesis property-based tests, long-horizon multi-generation survival/growth tests, and target-hardware pilot measurements on DGX/AGX Spark remain **untested**.
- Downstream pending gates: LLM population execution (Phase 1.2), full economy/manual integration (Phase 1.3), and sandboxed capability synthesis (Phases 1.4/2.2).

**Depends on:** `evolzen.schemas.transition`, `evolzen.schemas.world`, `evolzen.schemas.development`, `evolzen.storage`.
**Depended on by:** `evolzen.agents` (acts in it), `evolzen.exploration` (probes it),
`evolzen.predictor` (trains against its verifiable outcomes).
