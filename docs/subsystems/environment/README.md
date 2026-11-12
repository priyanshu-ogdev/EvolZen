# Environment integration

Authority: [Phase 1.1](../../phases/1.1-environment.md).
Source package: `src/evolzen/environment/`.

Own the world clock, agent observations, legal candidate generation, execution and outcome
verification. Developmental agents consume eight normalized observable features and return a
pending action ID; they do not mutate world state themselves. The environment must recheck age,
resources, permissions and action parameters, then issue a matching trusted outcome receipt.
Version context/skill keys with mechanics and meaningful action parameters.

Implemented Phase 1.1 core:
- `SocialSandboxEngine` (`engine.py`) implementing `Environment` and `PersistentEnvironment` over `(state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})`, with verified `CapabilityPackage` gating (no arbitrary engine mutation);
- canonical `WorldState`, `WorldSnapshot`, `CapabilityPackage`, `GrowthEvent`, `WorldInvariant`, `InvariantReport`, `BranchRecord`, and `InterventionSpec` contracts (`evolzen.schemas.world`);
- `check_invariants` (`invariants.py`), `extract_growth_events` / `summarize_growth` (`growth.py`) across all five `GrowthCategory` buckets;
- `TransitionLogStore` (`evolzen.storage.transition_log`) for schema-versioned JSON-only DuckDB persistence, SHA-256 hash-chained transition appends, snapshots, growth events, and atomic `save_snapshot_and_branch`;
- `replay_transitions`, `replay_from_store`, and `branch_from_snapshot` (`replay.py`);
- `apply_intervention` (`interventions.py`);
- `adapter` (`observe_features`, `legal_candidates`, `action_from_candidate`, `execute_decision`) for `evolzen.agents.development`, including independent host-side verification of `Decision` legality and `minimum_age`;
- `pettingzoo_env` (`SocialSandboxAECEnv`) wrapping `SocialSandboxEngine` under PettingZoo's `AECEnv` contract (`Discrete(10)` with `action_mask` or typed `Action`);
- `run_environment_pilot` (`pilot.py`) for local CPU throughput/storage benchmarking with `snapshot_interval` support.

Pending / untested scope: empirical long-horizon Phase 1.1 runs, `SocialSandboxAECEnv` multi-agent learning integrations, LLM population scheduling (`evolzen.agents`, Phase 1.2), full market/manual provenance flows (`evolzen.economy`, Phase 1.3), sandboxed capability synthesis (`evolzen.exploration`, `evolzen.containment`, Phases 1.4/2.2), and target-rig hardware pilot measurements on DGX/AGX Spark.
See [agent engineering](../agents/engineering.md) for the broader boundaries.
