"""Phase 1.1 — Environment Engine. See README.md."""
from evolzen.environment.adapter import (
    action_from_candidate,
    execute_decision,
    legal_candidates,
    observe_features,
)
from evolzen.environment.engine import Environment, PersistentEnvironment, SocialSandboxEngine
from evolzen.environment.growth import extract_growth_events, summarize_growth
from evolzen.environment.interventions import apply_intervention
from evolzen.environment.invariants import check_invariants
from evolzen.environment.moore_machine import SOCIAL_SANDBOX_SPEC, MooreMachineSpec
from evolzen.environment.pettingzoo_env import SocialSandboxAECEnv
from evolzen.environment.pilot import EnvironmentPilotMetrics, run_environment_pilot
from evolzen.environment.replay import (
    ReplayResult,
    branch_from_snapshot,
    replay_from_store,
    replay_transitions,
)
from evolzen.environment.world_state import build_default_world, derive_rng

__all__ = [
    "Environment",
    "PersistentEnvironment",
    "SocialSandboxAECEnv",
    "SocialSandboxEngine",
    "MooreMachineSpec",
    "SOCIAL_SANDBOX_SPEC",
    "ReplayResult",
    "EnvironmentPilotMetrics",
    "action_from_candidate",
    "apply_intervention",
    "branch_from_snapshot",
    "build_default_world",
    "check_invariants",
    "derive_rng",
    "execute_decision",
    "extract_growth_events",
    "legal_candidates",
    "observe_features",
    "replay_from_store",
    "replay_transitions",
    "run_environment_pilot",
    "summarize_growth",
]
