"""Phase 1.1 deterministic initial world builders and seeded RNG utilities.

All randomness derives strictly from explicit `(seed, tick, step_index, salt)` inputs so
exact replay reproduces every state and emission with zero hidden mutable state, following
Procgen-style seed-indexed world generation (Cobbe et al., arXiv:1912.01588), Tycho
(arXiv:2607.28287), and ADR 0004. The initial world layout is an EvolZen design choice and
remains empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

import hashlib
import random

from evolzen.schemas.world import (
    ActionType,
    CapabilityPackage,
    LocationNode,
    ResourceAccounting,
    WorldAgentState,
    WorldState,
)


def derive_rng(seed: int, tick: int, step_index: int, salt: str = "") -> random.Random:
    """Return a deterministic `random.Random` instance from explicit transition inputs."""
    material = f"{seed}:{tick}:{step_index}:{salt}".encode()
    digest = hashlib.sha256(material).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def build_default_world(
    *,
    seed: int = 42,
    run_id: str = "default-run",
    branch_id: str = "main",
    num_locations: int = 4,
    num_agents: int = 4,
    max_ticks: int = 2000,
    max_agents: int = 64,
    initial_agent_age: int = 0,
) -> WorldState:
    """Construct a deterministic discrete graph/grid social sandbox initial state.

    Creates `num_locations` connected locations with finite resource pools, carrying
    capacities, and regeneration rates; `num_agents` founder agents distributed across
    locations; one pre-verified baseline `craft:tool` capability package; and an exact
    `ResourceAccounting` ledger matching initial totals.
    """
    if num_locations < 1:
        raise ValueError("num_locations must be >= 1")
    if num_agents < 1 or num_agents > max_agents:
        raise ValueError("num_agents must be in [1, max_agents]")

    rng = derive_rng(seed, 0, 0, "init-world")
    base_names = ("plaza", "grove", "quarry", "market_square")
    location_ids = [
        base_names[i] if i < len(base_names) else f"sector_{i}" for i in range(num_locations)
    ]

    locations: dict[str, LocationNode] = {}
    initial_resources: dict[str, int] = {"food": 0, "wood": 0, "stone": 0}
    for idx, loc_id in enumerate(location_ids):
        neighbors: list[str] = []
        if num_locations > 1:
            neighbors.append(location_ids[(idx + 1) % num_locations])
            prev_id = location_ids[(idx - 1) % num_locations]
            if prev_id not in neighbors:
                neighbors.append(prev_id)
        food_amt = 20 + rng.randint(0, 10)
        wood_amt = 15 + rng.randint(0, 10)
        stone_amt = 10 + rng.randint(0, 8)
        stock = {"food": food_amt, "wood": wood_amt, "stone": stone_amt}
        for key, qty in stock.items():
            initial_resources[key] += qty
        locations[loc_id] = LocationNode(
            location_id=loc_id,
            name=loc_id.replace("_", " ").title(),
            neighbors=tuple(sorted(neighbors)),
            resources=stock,
            capacities={"food": 50, "wood": 45, "stone": 40},
            regen_rates={"food": 2, "wood": 1, "stone": 1},
            shock_factor=1.0,
        )

    agents: dict[str, WorldAgentState] = {}
    initial_currency = 0
    for idx in range(num_agents):
        agent_id = f"agent-{idx}"
        loc_id = location_ids[idx % num_locations]
        agent_food = 3
        agent_wood = 2
        agent_currency = 20
        initial_resources["food"] += agent_food
        initial_resources["wood"] += agent_wood
        initial_currency += agent_currency
        agents[agent_id] = WorldAgentState(
            agent_id=agent_id,
            location_id=loc_id,
            born_at=0,
            alive=True,
            energy=0.8,
            fatigue=0.0,
            currency=agent_currency,
            inventory={"food": agent_food, "wood": agent_wood, "stone": 0},
            role="generalist",
            lineage_id=f"lineage-{idx}",
            parents=(),
            generation=0,
            status=0.1 * (idx % 3),
            skills=(),
            institution_ids=(),
            adopted_norms=(),
            last_action_tick=initial_agent_age,
        )

    base_capability = CapabilityPackage(
        package_id="craft:tool:v1",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 2, "stone": 1},
        output_kind="tool",
        min_age=0,
        evidence_id="bootstrap:craft:tool:v1",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )

    return WorldState(
        run_id=run_id,
        branch_id=branch_id,
        tick=initial_agent_age,
        step_index=0,
        seed=seed,
        max_ticks=max_ticks,
        max_agents=max_agents,
        locations=locations,
        agents=agents,
        artifacts={},
        capabilities={base_capability.package_id: base_capability},
        contracts={},
        institutions={},
        norms={},
        accounting=ResourceAccounting(
            initial_resources=initial_resources,
            exogenous_inflows={k: 0 for k in initial_resources},
            consumed_or_decayed={k: 0 for k in initial_resources},
            initial_currency=initial_currency,
        ),
    )

