"""Unit tests for Phase 1.2 offline private LoRA adapter curation and validation."""
from __future__ import annotations

from pathlib import Path

from evolzen.agents.trainer import (
    AdapterTrainingConfig,
    CuratedTrajectory,
    OfflineAdapterTrainer,
    TrajectoryCurator,
)
from evolzen.schemas.transition import Action, Emission, State, Transition
from evolzen.storage.transition_log import TransitionLogStore


def test_trajectory_curator_extraction(tmp_path: Path) -> None:
    """Verifies that TrajectoryCurator groups transitions by agent and categorizes success/failure."""
    db_path = tmp_path / "trainer_transitions.duckdb"
    store = TransitionLogStore(db_path)

    t1 = Transition(
        state=State(data={"tick": 0, "agents": {"agent-0": {"lineage_id": "lineage-1", "generation": 0}}}),
        action=Action(agent_id="agent-0", action_type="gather"),
        emission=Emission(data={"accepted": True, "rewards": (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "invariant_passed": True}),
        next_state=State(data={"tick": 1}),
    )
    t2 = Transition(
        state=State(data={"tick": 1, "agents": {"agent-0": {"lineage_id": "lineage-1", "generation": 0}}}),
        action=Action(agent_id="agent-0", action_type="consume"),
        emission=Emission(data={"accepted": True, "rewards": (0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "invariant_passed": True}),
        next_state=State(data={"tick": 2}),
    )
    t3 = Transition(
        state=State(data={"tick": 0, "agents": {"agent-1": {"lineage_id": "lineage-2", "generation": 0}}}),
        action=Action(agent_id="agent-1", action_type="wait"),
        emission=Emission(data={"accepted": True, "rewards": (-0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "invariant_passed": False}),
        next_state=State(data={"tick": 1}),
    )

    store.append(t1, run_id="curate-test")
    store.append(t2, run_id="curate-test")
    store.append(t3, run_id="curate-test")

    trajectories = TrajectoryCurator.extract_from_store(store, run_id="curate-test")
    assert len(trajectories) == 2

    traj_0 = next(t for t in trajectories if t.agent_id == "agent-0")
    assert traj_0.is_success is True
    assert traj_0.total_reward == 0.8
    assert len(traj_0.transitions) == 2

    traj_1 = next(t for t in trajectories if t.agent_id == "agent-1")
    assert traj_1.is_success is False
    assert traj_1.failure_type == "invariant_violation"


def test_trajectory_curator_stratified_mixing() -> None:
    """Verifies that mix_stratified_replay balances successes and instructive failures."""
    successes = [
        CuratedTrajectory(
            trajectory_id=f"succ-{i}",
            lineage_id="l1",
            agent_id=f"a-{i}",
            transitions=(),
            total_reward=1.0,
            is_success=True,
        )
        for i in range(10)
    ]
    failures = [
        CuratedTrajectory(
            trajectory_id=f"fail-{i}",
            lineage_id="l1",
            agent_id=f"a-{i}",
            transitions=(),
            total_reward=-0.5,
            is_success=False,
            failure_type="suboptimal_return",
        )
        for i in range(10)
    ]

    all_trajs = successes + failures
    mixed = TrajectoryCurator.mix_stratified_replay(all_trajs, success_ratio=0.6, max_samples=10)
    assert len(mixed) == 10
    succ_count = sum(1 for t in mixed if t.is_success)
    fail_count = sum(1 for t in mixed if not t.is_success)
    assert succ_count == 6
    assert fail_count == 4


def test_offline_adapter_trainer_validation_and_promotion() -> None:
    """Verifies promotion gating: requires task improvement, retention >= threshold, and safety passed."""
    config = AdapterTrainingConfig(retention_threshold=0.9, safety_threshold=1.0)
    trainer = OfflineAdapterTrainer(config)

    # 1. Successful validation pass
    succ_trajs = [
        CuratedTrajectory(
            trajectory_id=f"t-{i}",
            lineage_id="lineage-alpha",
            agent_id=f"a-{i}",
            transitions=(),
            total_reward=1.0,
            is_success=True,
        )
        for i in range(5)
    ]
    res_pass = trainer.validate_and_gate_promotion(
        candidate_checkpoint_id="chkpt-001",
        lineage_id="lineage-alpha",
        held_out_trajectories=succ_trajs,
        historical_baseline_score=1.0,
    )
    assert res_pass.promoted is True
    assert res_pass.safety_passed is True
    assert res_pass.retention_score == 1.0
    assert trainer.active_checkpoints["lineage-alpha"] == "chkpt-001"

    # 2. Catastrophic forgetting rejection (retention score below 0.9)
    res_forgetting = trainer.validate_and_gate_promotion(
        candidate_checkpoint_id="chkpt-002",
        lineage_id="lineage-alpha",
        held_out_trajectories=succ_trajs[:2],  # only 2 successes
        historical_baseline_score=4.0,  # baseline was 4.0 -> accuracy 1.0 / 4.0 = 0.25 < 0.9
    )
    assert res_forgetting.promoted is False
    assert "Catastrophic forgetting" in (res_forgetting.rejection_reason or "")

    # 3. Safety rejection (invariant violation)
    unsafe_trajs = [
        CuratedTrajectory(
            trajectory_id="t-unsafe",
            lineage_id="lineage-alpha",
            agent_id="a-unsafe",
            transitions=(),
            total_reward=1.0,
            is_success=False,
            failure_type="invariant_violation",
        )
    ]
    res_unsafe = trainer.validate_and_gate_promotion(
        candidate_checkpoint_id="chkpt-003",
        lineage_id="lineage-alpha",
        held_out_trajectories=unsafe_trajs,
        historical_baseline_score=0.5,
    )
    assert res_unsafe.promoted is False
    assert res_unsafe.safety_passed is False
    assert "Safety check failed" in (res_unsafe.rejection_reason or "")


def test_offline_adapter_trainer_train_epoch() -> None:
    """Verifies that train_adapter_epoch computes loss convergence, mixes rehearsal, and saves checkpoints."""
    config = AdapterTrainingConfig(epochs=3, learning_rate=1e-4, lora_rank=8, lora_alpha=16)
    trainer = OfflineAdapterTrainer(config)

    trajs = [
        CuratedTrajectory(
            trajectory_id=f"t-{i}",
            lineage_id="lineage-beta",
            agent_id=f"a-{i}",
            transitions=(
                Transition(
                    state=State(data={"tick": 0}),
                    action=Action(agent_id=f"a-{i}", action_type="gather"),
                    emission=Emission(data={"rewards": (0.2,) * 8, "invariant_passed": True}),
                    next_state=State(data={"tick": 1}),
                ),
            ),
            total_reward=1.6,
            is_success=True,
        )
        for i in range(4)
    ]
    rehearsal = [
        CuratedTrajectory(
            trajectory_id="t-rehearsal",
            lineage_id="lineage-beta",
            agent_id="a-old",
            transitions=(
                Transition(
                    state=State(data={"tick": 0}),
                    action=Action(agent_id="a-old", action_type="wait"),
                    emission=Emission(data={"rewards": (0.1,) * 8, "invariant_passed": True}),
                    next_state=State(data={"tick": 1}),
                ),
            ),
            total_reward=0.8,
            is_success=True,
        )
    ]

    report = trainer.train_adapter_epoch(
        lineage_id="lineage-beta",
        trajectories=trajs,
        rehearsal_trajectories=rehearsal,
    )
    assert report["status"] == "completed"
    assert report["lineage_id"] == "lineage-beta"
    assert report["initial_loss"] > 0
    assert report["final_loss"] < report["initial_loss"]
    assert report["loss_delta"] > 0
    assert report["samples_trained"] == 5
    assert report["checkpoint_id"] in trainer.checkpoints


def test_offline_adapter_trainer_train_and_gate_lineage() -> None:
    """Verifies train_and_gate_lineage executes training and gates promotion atomically."""
    trainer = OfflineAdapterTrainer()
    train_trajs = [
        CuratedTrajectory(
            trajectory_id="train-1",
            lineage_id="lineage-gamma",
            agent_id="ag-1",
            transitions=(),
            total_reward=1.0,
            is_success=True,
        )
    ]
    val_trajs = [
        CuratedTrajectory(
            trajectory_id="val-1",
            lineage_id="lineage-gamma",
            agent_id="ag-2",
            transitions=(),
            total_reward=1.0,
            is_success=True,
        )
    ]

    report, val_res = trainer.train_and_gate_lineage(
        lineage_id="lineage-gamma",
        train_trajectories=train_trajs,
        held_out_trajectories=val_trajs,
        historical_baseline_score=1.0,
    )
    assert report["status"] == "completed"
    assert val_res.promoted is True
    assert trainer.active_checkpoints["lineage-gamma"] == report["checkpoint_id"]


def test_population_scheduler_run_training_cycle(tmp_path: Path) -> None:
    """Verifies that PopulationScheduler executes an end-to-end training cycle and promotes checkpoints."""
    from evolzen.agents.scheduler import PopulationScheduler
    from evolzen.environment.engine import SocialSandboxEngine

    db_path = tmp_path / "sched_training.duckdb"
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(default_seed=42, num_locations=2, num_agents=2, max_ticks=20)
        state = engine.reset(seed=42)
        scheduler = PopulationScheduler(engine, initial_state=state, store=store, run_id="cycle-test")

        # Step 4 generations/cycles to accumulate real transitions
        scheduler.run_generation(steps=4, seed=42)
        assert store.count() > 0

        trainer = OfflineAdapterTrainer()
        results = scheduler.run_training_cycle(trainer=trainer)
        assert len(results) > 0
        for lineage_id, (report, val_res) in results.items():
            assert report["status"] == "completed"
            assert val_res.checkpoint_id == report["checkpoint_id"]
            if val_res.promoted:
                for agent in scheduler.agents.values():
                    if agent.profile.lineage_id == lineage_id:
                        assert agent.profile.adapter_checkpoint == val_res.checkpoint_id


def test_single_agent_training_and_adapter_update() -> None:
    """Verifies that an isolated single agent can record environment transitions, train, and promote its LoRA adapter."""
    from evolzen.agents.agent import Agent
    from evolzen.environment.adapter import execute_decision, legal_candidates, observe_features
    from evolzen.environment.engine import SocialSandboxEngine
    from evolzen.schemas.agent_profile import AgentProfile

    engine = SocialSandboxEngine(default_seed=101, num_locations=2, num_agents=1, max_ticks=20)
    state = engine.reset(seed=101)

    profile = AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-solo",
        roles=("forager",),
    )
    agent = Agent.create(profile=profile, seed=101, tick=0)
    assert agent.profile.adapter_checkpoint is None

    transitions = []
    for tick in range(6):
        signal = observe_features(state, "agent-0")
        candidates = legal_candidates(state, "agent-0")
        decision = agent.decide(signal, candidates, tick=tick, seed=101 + tick)
        t, outcome = execute_decision(engine, state, decision)
        agent.observe(outcome)
        state = t.next_state
        transitions.append(t)

    trajs = TrajectoryCurator.extract_from_transitions(transitions)
    assert len(trajs) == 1
    assert trajs[0].agent_id == "agent-0"
    assert len(trajs[0].transitions) == 6

    trainer = OfflineAdapterTrainer()
    report, val_res = trainer.train_and_gate_lineage(
        lineage_id="lineage-solo",
        train_trajectories=trajs,
        held_out_trajectories=trajs,
        historical_baseline_score=1.0,
    )

    assert report["status"] == "completed"
    assert report["final_loss"] < report["initial_loss"]
    assert val_res.promoted is True
    assert val_res.safety_passed is True
    assert val_res.retention_score >= 0.95

    # Apply promoted checkpoint to the single agent
    agent.profile = agent.profile.model_copy(update={"adapter_checkpoint": val_res.checkpoint_id})
    assert agent.profile.adapter_checkpoint == report["checkpoint_id"]

    # Verify agent continues acting with the updated checkpoint profile
    post_signal = observe_features(state, "agent-0")
    post_cands = legal_candidates(state, "agent-0")
    post_decision = agent.decide(post_signal, post_cands, tick=6, seed=107)
    assert post_decision.agent_id == "agent-0"
    assert post_decision.candidate.permitted is True


def test_offline_adapter_trainer_dora_configuration() -> None:
    """Verifies that DoRA (Weight-Decomposed Low-Rank Adaptation) configuration is tracked."""
    config = AdapterTrainingConfig(
        adapter_type="dora",
        dora_magnitude=True,
        lora_rank=16,
        lora_alpha=32,
    )
    trainer = OfflineAdapterTrainer(config)

    trajs = [
        CuratedTrajectory(
            trajectory_id="traj-dora-0",
            lineage_id="lineage-dora",
            agent_id="agent-dora",
            transitions=(),
            total_reward=1.2,
            is_success=True,
        )
    ]
    report = trainer.train_adapter_epoch("lineage-dora", trajs)

    assert report["adapter_type"] == "dora"
    assert report["dora_magnitude"] is True
    assert report["lora_rank"] == 16
    assert report["lora_alpha"] == 32
    chkpt_id = report["checkpoint_id"]
    assert trainer.checkpoints[chkpt_id]["adapter_type"] == "dora"
    assert trainer.checkpoints[chkpt_id]["dora_magnitude"] is True
