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
- Landed Phase 1.1 hardening stages (Stages 1–4):
  - **Stage 1 (Replay & Core Boundedness):** `replay_transitions` propagates true state divergence by passing `current_state`; `replay_from_store` includes transitions up to `up_to_tick`; `apply_intervention` supports sequence indexing (`_set_nested_path`) and reconciles `initial_currency`; `_handle_spawn_offspring` and `invariants.py` evaluate living agent counts against `max_agents`.
  - **Stage 2 (Host Adapter 17-Action Coverage):** `adapter.legal_candidates` and `action_from_candidate` cover all 17 `ActionType`s plus `cancel_contract`, verified by host-side validation in `execute_decision`.
  - **Stage 3 (Operational Mechanics):** Implemented tool durability decay and 50% fatigue mitigation; commons conservation norm enforcement with hypocrisy penalties (-0.1) and social friction (-0.05); institutional trade fee withholding and reserves; voluntary contract cancellation and TTL auto-expiration sweeps; `[0.0, 1.0]` status bounds; bounded collections (`FR-2`); and unhandled exogenous event provenance.
  - **Stage 4 (PettingZoo & Endogenous Processes):** `SocialSandboxAECEnv.step()` accepts `exogenous_input` and `seed`; optional `store: TransitionLogStore` hook automatically logs transitions; discrete action space expanded to `Discrete(16)` with full typed decoding; and `_expand_endogenous_ecology` wires active carrying capacity growth to `GrowthAttribution.ENDOGENOUS_PROCESS`.
- Open Phase 1.1 hardening backlog (empirical metrics remain **untested** / unmeasured):
  - All 18 `invariants.py` failure branches, Hypothesis property-based tests, long-horizon multi-generation survival/growth tests, and target-hardware pilot measurements on DGX/AGX Spark remain **untested**.
- Downstream pending gates: LLM population execution (Phase 1.2), full economy/manual integration (Phase 1.3), and sandboxed capability synthesis (Phases 1.4/2.2).

**Depends on:** `evolzen.schemas.transition`, `evolzen.schemas.world`, `evolzen.schemas.development`, `evolzen.storage`.
**Depended on by:** `evolzen.agents` (acts in it), `evolzen.exploration` (probes it),
`evolzen.predictor` (trains against its verifiable outcomes).
