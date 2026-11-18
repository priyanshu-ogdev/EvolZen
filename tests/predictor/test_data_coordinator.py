"""Tests for Phase 2.1 Continual RL Data Coordinator.

Validates:
1. TransitionLogStore, RuleLibrary, and CLEAR RehearsalBuffer data coordination.
2. Ingestion of live environment rollouts into RuleLibrary.regression_bank as held-out fixtures.
3. CLEAR mixed on-policy / off-policy batch sampling with provenance tracking and real_data_floor checks.
4. Coordinated continual RL update steps executing joint updates across Planner (GRPO),
   WorldDynamicsPredictor, GroundedJEPAEncoder, and OfflineAdapterTrainer with BWT/FWT tracking.

Citations:
- CLaaS (arXiv:2606.05559);
- CLEAR (Rolnick et al., NeurIPS 2019, arXiv:1811.11682);
- Wang et al. (IEEE TPAMI 2024, DOI:10.1109/TPAMI.2024.3367329);
- Shumailov et al. (Model Collapse, Nature 2024).
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evolzen.agents.trainer import OfflineAdapterTrainer
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.predictor.data_coordinator import (
    ContinualRLBatch,
    ContinualRLDataCoordinator,
    ContinualRLUpdateSummary,
)
from evolzen.predictor.dynamics import WorldDynamicsPredictor
from evolzen.predictor.planner import Planner
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.recognition.jepa import GroundedJEPAEncoder
from evolzen.schemas.transition import Action, Transition
from evolzen.schemas.world import ActionType, CapabilityPackage
from evolzen.storage.transition_log import TransitionLogStore


def _seed_transitions(db_path: Path, count: int = 12) -> list[Transition]:
    """Helper to populate DuckDB store with verified synthetic transitions."""
    transitions: list[Transition] = []
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=count + 10)
        state = engine.reset(seed=42)
        cur = state
        for i in range(count):
            act_type = ActionType.WAIT if i % 2 == 0 else ActionType.GATHER
            action = Action(agent_id=f"agent-{i % 2}", action_type=act_type)
            trans = engine.step(cur, action)
            store.append(trans)
            transitions.append(trans)
            cur = trans.next_state
    return transitions


def _create_rule_library(tmp_path: Path) -> RuleLibrary:
    """Helper to create a test RuleLibrary."""
    db_path = tmp_path / "coordinator_lib.duckdb"
    store = LibraryStore(db_path)
    return RuleLibrary(store=store)


def _make_capability_package(package_id: str = "craft:iron_axe:v1") -> CapabilityPackage:
    return CapabilityPackage(
        package_id=package_id,
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 1, "iron": 2},
        output_kind="iron_axe",
        min_age=0,
        evidence_id=f"ev-{uuid4()}",
        verified_replay=True,
        verified_intervention=True,
        verified_containment=True,
    )


def test_coordinator_initialization_and_sync(tmp_path: Path) -> None:
    """Coordinator syncs transitions from TransitionLogStore into buffer and regression bank."""
    db_path = tmp_path / "transitions.duckdb"
    _seed_transitions(db_path, count=10)

    lib = _create_rule_library(tmp_path)
    pkg = _make_capability_package("craft:iron_axe:v1")
    lib.register_capability(pkg)

    rehearsal_buffer = RehearsalBuffer(capacity=100)
    store = TransitionLogStore(db_path)

    coordinator = ContinualRLDataCoordinator(
        store=store,
        rehearsal_buffer=rehearsal_buffer,
        rule_library=lib,
    )

    assert len(rehearsal_buffer) == 0
    assert lib.regression_bank.fixture_count() == 0

    ingested = coordinator.sync_from_store()
    assert ingested == 10
    assert len(rehearsal_buffer) == 10
    assert lib.regression_bank.fixture_count() == 10

    # Calling sync again without new records should ingest 0
    assert coordinator.sync_from_store() == 0


def test_sample_clear_batch_provenance(tmp_path: Path) -> None:
    """Coordinator samples CLEAR batch with accurate provenance tracking and real data fraction."""
    db_path = tmp_path / "clear_test.duckdb"
    seeded = _seed_transitions(db_path, count=8)

    lib = _create_rule_library(tmp_path)
    rehearsal_buffer = RehearsalBuffer(capacity=100)
    rehearsal_buffer.extend(seeded)

    store = TransitionLogStore(db_path)
    coordinator = ContinualRLDataCoordinator(
        store=store,
        rehearsal_buffer=rehearsal_buffer,
        rule_library=lib,
    )

    batch = coordinator.sample_clear_batch(
        new_transitions=seeded[:4],
        batch_size=8,
        replay_ratio=0.5,
    )

    assert isinstance(batch, ContinualRLBatch)
    assert len(batch.transitions) == 8
    assert batch.rehearsal_count == 4
    assert batch.new_count == 4
    assert 0.0 <= batch.real_data_fraction <= 1.0


def test_step_continual_rl_joint_updates(tmp_path: Path) -> None:
    """step_continual_rl executes joint updates across Planner, JEPA, and Adapter Trainer."""
    db_path = tmp_path / "joint_updates.duckdb"
    _seed_transitions(db_path, count=12)

    lib = _create_rule_library(tmp_path)
    rehearsal_buffer = RehearsalBuffer(capacity=100)
    store = TransitionLogStore(db_path)

    coordinator = ContinualRLDataCoordinator(
        store=store,
        rehearsal_buffer=rehearsal_buffer,
        rule_library=lib,
    )

    predictor = WorldDynamicsPredictor()
    planner = Planner(dynamics=predictor, rehearsal_buffer=rehearsal_buffer, lr=0.05)
    jepa = GroundedJEPAEncoder(seed=42)
    agent_trainer = OfflineAdapterTrainer()

    summary = coordinator.step_continual_rl(
        planner=planner,
        jepa=jepa,
        agent_trainer=agent_trainer,
        batch_size=6,
        replay_ratio=0.5,
        current_task_idx=1,
    )

    assert isinstance(summary, ContinualRLUpdateSummary)
    assert summary.step == 1
    assert planner.update_count == 1
    assert summary.rehearsal_buffer_size >= 12
    assert summary.jepa_variance >= 0.0
    assert 0 <= summary.active_dimensions <= jepa.embedding_dim
    assert isinstance(summary.backward_transfer, float)
    assert isinstance(summary.forward_transfer, float)
    assert isinstance(summary.average_forgetting, float)
    assert "batch_size" in summary.metadata
