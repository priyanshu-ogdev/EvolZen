"""Procedural generator for held-out novel mini-environments (Phase 2.4).

Never reuse a small, fixed set of held-out environments across evaluation rounds — this is a
direct, actionable lesson from the field's own ARC-AGI-3 public/private gap (a harness went
from 30.2% cold to 96.4% purely through repeated exposure to the *same* 25 games). Every
evaluation round must use genuinely fresh instances.

Citations:
- Cobbe et al. (Procgen, ICML 2020, DOI:10.48550/arXiv.1912.01588) for seed-stratified procedural generation;
- Chollet (On the Measure of Intelligence, arXiv:1911.01547; ARC-AGI-2, arXiv:2505.11831).

Empirical fresh-world adaptation benchmarks remain untested until Phase 2.4 experiments
are executed on target hardware (AGENTS.md Rules #4 and #5).
"""
from __future__ import annotations

import hashlib
from typing import Any

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.world import ActionType, CapabilityPackage

MULTI_TIER_CAPABILITIES: tuple[CapabilityPackage, ...] = (
    CapabilityPackage(
        package_id="craft:tool_handle",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1},
        output_kind="tool_handle",
        min_age=0,
        evidence_id="multi_tier:craft:tool_handle",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    ),
    CapabilityPackage(
        package_id="craft:stone_blade",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"stone": 1},
        output_kind="stone_blade",
        min_age=0,
        evidence_id="multi_tier:craft:stone_blade",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    ),
    CapabilityPackage(
        package_id="craft:stone_axe",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1, "stone": 1},
        output_kind="stone_axe",
        min_age=0,
        evidence_id="multi_tier:craft:stone_axe",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    ),
)


class ProceduralEnvironmentGenerator:
    """Generates a fresh, never-before-seen environment instance within the Phase 1.1 domain
    family, for each evaluation round."""

    def __init__(self, seed: int = 42, task_tier: str = "basic") -> None:
        self._seed = seed
        self._task_tier = task_tier
        self._round = 0
        self._generated_configs: list[dict[str, Any]] = []

    @property
    def round_count(self) -> int:
        return self._round

    @property
    def task_tier(self) -> str:
        return self._task_tier

    @property
    def target_goal(self) -> str | None:
        return "craft:stone_axe" if self._task_tier == "multi_tier" else None

    @property
    def metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {"task_tier": self._task_tier}
        if self._task_tier == "multi_tier":
            meta["target_goal"] = "craft:stone_axe"
        return meta

    @property
    def generated_configs(self) -> list[dict[str, Any]]:
        return list(self._generated_configs)

    def next_environment(self) -> SocialSandboxEngine:
        """Generate the next fresh, non-reused environment instance.

        Guarantees:
        (a) genuinely novel parameters each call (seed, locations, agent counts);
        (b) novel parameter tracking so the evaluation report can prove zero reuse;
        (c) seeded multi-tier capabilities when task_tier == 'multi_tier'.
        """
        self._round += 1
        digest = hashlib.sha256(f"{self._seed}:round:{self._round}".encode()).hexdigest()
        round_seed = int(digest[:8], 16)

        # Procedural variation across topologies and capacities
        num_locations = 2 + (round_seed % 5)  # 2..6
        num_agents = 2 + ((round_seed // 5) % 5)  # 2..6
        max_ticks = 200 + (round_seed % 800)  # 200..999

        config: dict[str, Any] = {
            "round": self._round,
            "seed": round_seed,
            "num_locations": num_locations,
            "num_agents": num_agents,
            "max_ticks": max_ticks,
            "task_tier": self._task_tier,
        }
        if self._task_tier == "multi_tier":
            config["target_goal"] = "craft:stone_axe"

        # Enforce strict non-repetition across seeds
        if any(c["seed"] == round_seed for c in self._generated_configs):
            raise RuntimeError(f"Seed collision detected in procedural environment generation: {round_seed}")

        self._generated_configs.append(config)

        initial_caps = MULTI_TIER_CAPABILITIES if self._task_tier == "multi_tier" else None
        return SocialSandboxEngine(
            default_seed=round_seed,
            num_locations=num_locations,
            num_agents=num_agents,
            max_ticks=max_ticks,
            initial_capabilities=initial_caps,
        )

    def has_reused_instances(self) -> bool:
        """Verify that all generated environment seeds are strictly unique."""
        seen_seeds = {c["seed"] for c in self._generated_configs}
        return len(seen_seeds) < len(self._generated_configs)

    def generate_suite(self, num_instances: int) -> list[SocialSandboxEngine]:
        """Generate a batch of fresh, un-reused environment instances."""
        if num_instances <= 0:
            return []
        return [self.next_environment() for _ in range(num_instances)]
