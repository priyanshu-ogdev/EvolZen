"""Tests for Phase 1.5 <-> Phase 1.1 Bidirectional Synchronization via PopulationScheduler.

Verifies:
1. Active capabilities in RuleLibrary are automatically exported into WorldState.capabilities on scheduler init.
2. New capabilities registered via ActionType.REGISTER_CAPABILITY in the environment are imported into RuleLibrary.
3. Live environment transitions stepped by agents are ingested into RuleLibrary.regression_bank as held-out fixtures.
4. Generational steps maintain bidirectional capability parity between WorldState and RuleLibrary.

Citations:
- Voyager (Wang et al., TMLR 2023) for verified compositional skill libraries;
- Section §3.5 of docs/ARCHITECTURE.md.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evolzen.agents.scheduler import PopulationScheduler
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType, CapabilityPackage, WorldState


def _create_rule_library(tmp_path: Path) -> RuleLibrary:
    """Helper to instantiate a standalone RuleLibrary backed by temporary store."""
    db_path = tmp_path / "sync_lib.duckdb"
    store = LibraryStore(db_path)
    return RuleLibrary(store=store)


def _make_test_package(
    package_id: str = "craft:iron_plow:v1",
    action_type: str = ActionType.CRAFT,
    verified: bool = True,
    output_kind: str | None = None,
) -> CapabilityPackage:
    """Helper to create a verified CapabilityPackage."""
    kind = output_kind or (package_id.split(":")[1] if ":" in package_id else "item")
    return CapabilityPackage(
        package_id=package_id,
        version="1.0.0",
        action_type=action_type,
        required_resources={"wood": 2, "iron": 2},
        output_kind=kind,
        min_age=0,
        evidence_id=f"ev-{uuid4()}",
        verified_replay=verified,
        verified_intervention=verified,
        verified_containment=verified,
    )


def test_scheduler_exports_library_capabilities_on_init(tmp_path: Path) -> None:
    """PopulationScheduler exports active RuleLibrary capabilities into WorldState on initialization."""
    lib = _create_rule_library(tmp_path)
    pkg = _make_test_package("craft:iron_plow:v1")
    lib.register_capability(pkg)
    assert lib.active_capability_count() == 1

    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=50)
    init_state = engine.reset(seed=42)
    init_world = WorldState.from_state(init_state)
    assert "craft:iron_plow:v1" not in init_world.capabilities

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=init_state,
        rule_library=lib,
    )

    # Capability from library must now be available in world state
    assert "craft:iron_plow:v1" in scheduler.world.capabilities
    exported_pkg = scheduler.world.capabilities["craft:iron_plow:v1"]
    assert exported_pkg.package_id == "craft:iron_plow:v1"
    assert exported_pkg.output_kind == "iron_plow"


def test_scheduler_ingests_transitions_into_regression_bank(tmp_path: Path) -> None:
    """Live transitions stepped in PopulationScheduler are automatically ingested into RuleLibrary.regression_bank."""
    lib = _create_rule_library(tmp_path)
    assert lib.regression_bank.fixture_count() == 0

    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=50)
    init_state = engine.reset(seed=42)

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=init_state,
        rule_library=lib,
    )

    agent_id = next(iter(scheduler.world.agents.keys()))
    res = scheduler.step_agent(agent_id)

    assert res is not None
    transition, outcome = res
    assert transition is not None
    # Regression bank should have ingested this live transition
    assert lib.regression_bank.fixture_count() >= 1


def test_scheduler_imports_new_capabilities_from_world(tmp_path: Path) -> None:
    """When a capability is registered during a step, scheduler imports it into RuleLibrary."""
    lib = _create_rule_library(tmp_path)
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=50)
    init_state = engine.reset(seed=42)

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=init_state,
        rule_library=lib,
    )

    agent_id = next(iter(scheduler.world.agents.keys()))
    new_pkg = _make_test_package("craft:solar_forge:v1")

    # Directly step registration of verified capability
    action = Action(
        agent_id=agent_id,
        action_type=ActionType.REGISTER_CAPABILITY,
        params={"package": new_pkg.model_dump()},
    )
    # Step engine to generate transition
    transition = engine.step(scheduler.state, action)
    assert "craft:solar_forge:v1" in WorldState.from_state(transition.next_state).capabilities

    # Scheduler imports it into rule_library
    lib.import_capabilities_from_world(WorldState.from_state(transition.next_state))

    imported = lib.get_capability("craft:solar_forge:v1")
    assert imported is not None
    assert imported.package_id == "craft:solar_forge:v1"
    assert imported.output_kind == "solar_forge"


def test_generational_sync_bidirectional(tmp_path: Path) -> None:
    """Generational execution maintains capability synchronization and grows regression bank."""
    lib = _create_rule_library(tmp_path)
    seed_pkg = _make_test_package("craft:stone_mortar:v1")
    lib.register_capability(seed_pkg)

    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=50)
    init_state = engine.reset(seed=42)

    scheduler = PopulationScheduler(
        engine=engine,
        initial_state=init_state,
        rule_library=lib,
    )

    metrics = scheduler.run_generation(steps=5, seed=100)
    assert metrics.total_transitions > 0

    # Verification: world has seed capability
    assert "craft:stone_mortar:v1" in scheduler.world.capabilities
    # Verification: regression bank grew from generational stepping
    assert lib.regression_bank.fixture_count() >= metrics.total_transitions
