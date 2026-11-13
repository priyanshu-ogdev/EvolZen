# Environment integration

Authority: [Phase 1.1](../../phases/1.1-environment.md).
Source package: `src/evolzen/environment/`.

Own the world clock, agent observations, legal candidate generation, execution and outcome
verification. Developmental agents consume eight normalized observable features and return a
pending action ID; they do not mutate world state themselves. The environment must recheck age,
resources, permissions and action parameters, then issue a matching trusted outcome receipt.
Version context/skill keys with mechanics and meaningful action parameters.

Implemented Phase 1.1 core:
- `SocialSandboxEngine` (`engine.py`) implementing `Environment` and `PersistentEnvironment` over `(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})`, covering all 17 `ActionType`s with verified `CapabilityPackage` gating (no arbitrary engine mutation);
- canonical `WorldState`, `WorldSnapshot`, `CapabilityPackage`, `GrowthEvent`, `WorldInvariant`, `InvariantReport`, `BranchRecord`, and `InterventionSpec` contracts (`evolzen.schemas.world`);
- `check_invariants` (`invariants.py`), `extract_growth_events` / `summarize_growth` (`growth.py`) across all five `GrowthCategory` buckets;
- `TransitionLogStore` (`evolzen.storage.transition_log`, `SCHEMA_VERSION = 1`) for JSON-only DuckDB persistence, SHA-256 hash-chained transition appends, snapshots, growth events, and atomic `save_snapshot_and_branch`;
- `replay_transitions`, `replay_from_store`, and `branch_from_snapshot` (`replay.py`);
- `apply_intervention` (`interventions.py`);
- `adapter` (`observe_features`, `legal_candidates`, `action_from_candidate`, `execute_decision`) for `evolzen.agents.development`, including independent host-side verification of `Decision` legality and `minimum_age`;
- `pettingzoo_env` (`SocialSandboxAECEnv`) wrapping `SocialSandboxEngine` under PettingZoo's `AECEnv` contract (`Discrete(10)` with `action_mask` or typed `Action`);
- `run_environment_pilot` (`pilot.py`) for local CPU throughput/storage benchmarking with `snapshot_interval` support.

Landed Stage 1 critical fixes:
- `replay_transitions` passes `current_state` (not `recorded.state`) to `engine.step`, propagating state divergence accurately;
- `replay_from_store` includes transitions up to `up_to_tick`, preserving `same_tick=True` multi-agent transitions;
- `apply_intervention` supports sequence indexing (`_set_nested_path`) and reconciles `ResourceAccounting.initial_currency`;
- `_handle_spawn_offspring` and `_check_bounded_state` evaluate capacity against active living agents rather than historical lineage records.

Landed Stage 2 host adapter full 17-action coverage:
- `adapter.legal_candidates` and `adapter.action_from_candidate` cover all 17 `ActionType`s (`wait`, `gather`, `move`, `consume`, `craft`, `trade`, `propose_contract`, `fulfill_contract`, `found_institution`, `join_institution`, `contribute_institution`, `propose_norm`, `adopt_norm`, `assign_role`, `spawn_offspring`, `improve_location`, `register_capability`);
- Added `cancel_contract:{cid}` candidate generation and parsing for proposers of open contracts;
- Host-side validation in `execute_decision` verifies legal candidate membership, dynamic permissions, and minimum age before stepping and returning verified `Outcome` receipts.

Landed Stage 3 operational mechanics:
- **Tool Durability & Fatigue Mitigation:** Handlers `_handle_gather` and `_handle_improve_location` consume tool durability on work actions while halving physical fatigue accumulation;
- **Norm Compliance & Social Friction:** `_handle_gather` evaluates conservation norms during common-pool harvesting, penalizing hypocrisy (-0.1 status/social reward) and community friction (-0.05 status/social reward) during resource scarcity (< 20% cap) while rewarding sustainable harvests (+0.02);
- **Institutional Trade Fee Withholding & Reserves:** `_handle_trade` withholds `contribution_rate` fee on local trades directly to `local_inst.currency_reserve` while maintaining exact `resource_conservation` invariant; `_handle_contribute_institution` supports direct currency contributions;
- **Contract Cancellation & Expiration Sweep:** Handlers support voluntary cancellation (`cancel=True` in `_handle_fulfill_contract`) and automatic expiration sweep (`_expire_contracts`) for stale open contracts exceeding TTL (100 ticks) or with deceased parties;
- **FR-2 Bounded Collections & Status:** Enforced upper bounds on `WorldAgentState.status` (`[0.0, 1.0]`) across schemas, invariants, and engine handlers. Enforced capacity bounds (`artifacts <= 512`, `contracts <= 256`, `institutions <= 64`, `norms <= 64`, `capabilities <= 64`) in `invariants.py` and action rejection;
- **Exogenous Provenance:** `_apply_exogenous` captures unhandled exogenous events (`unhandled:<kind>`) in `applied_exog` and records them in transition emissions (`exogenous_applied`).

Open Phase 1.1 hardening backlog (empirical metrics remain untested / unmeasured):
- **PettingZoo step hooks:** `SocialSandboxAECEnv.step` needs optional `exogenous_input`, `seed`, and `TransitionLogStore` hooks;
- **Endogenous Process Growth Attribution:** Wire or clarify active world-tick emitter for `GrowthAttribution.ENDOGENOUS_PROCESS`;
- **Untested validation & downstream scope:** all 18 failure branches in `invariants.py`, Hypothesis property-based tests, empirical long-horizon Phase 1.1 runs, `SocialSandboxAECEnv` multi-agent learning integrations, LLM population scheduling (`evolzen.agents`, Phase 1.2), full market/manual provenance flows (`evolzen.economy`, Phase 1.3), sandboxed capability synthesis (`evolzen.exploration`, `evolzen.containment`, Phases 1.4/2.2), and target-rig hardware pilot measurements on DGX/AGX Spark.
See [agent engineering](../agents/engineering.md) for the broader boundaries.
