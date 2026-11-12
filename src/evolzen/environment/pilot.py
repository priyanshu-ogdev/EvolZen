"""Phase 1.1 — Local CPU throughput & storage benchmark helper.

Design authority: docs/phases/1.1-environment.md, ADR 0004, ADR 0005.
Citations: Tycho (arXiv:2607.28287) for deterministic transition/replay logging.
Measurements produced here reflect local CPU smoke benchmarks only; rig-scale
throughput and long-horizon growth dynamics remain empirically untested until Phase 1.1
experiments are run.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from evolzen.config import EnvironmentSettings
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.replay import replay_transitions
from evolzen.schemas.transition import Action, ExogenousInput, Transition
from evolzen.schemas.world import ActionType, GrowthEvent, WorldSnapshot
from evolzen.storage.transition_log import TransitionLogStore


@dataclass(frozen=True)
class EnvironmentPilotMetrics:
    """Measured local-host throughput and storage metrics (not a rig-scale claim)."""

    steps: int
    step_seconds: float
    ticks_per_second: float
    write_seconds: float
    writes_per_second: float
    replay_seconds: float
    replay_exact_match: bool
    snapshot_bytes: int
    db_bytes: int


def run_environment_pilot(
    *,
    db_path: Path,
    steps: int = 100,
    seed: int = 42,
    snapshot_interval: int | None = None,
) -> EnvironmentPilotMetrics:
    """Run a deterministic Phase 1.1 throughput and DuckDB persistence benchmark."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    resolved_snapshot_interval = (
        snapshot_interval if snapshot_interval is not None else EnvironmentSettings().snapshot_interval
    )
    if resolved_snapshot_interval < 1:
        raise ValueError("snapshot_interval must be >= 1")

    engine = SocialSandboxEngine(default_seed=seed, max_ticks=max(2000, steps + 10))
    initial_state = engine.reset(seed=seed, run_id="pilot-run")
    state = initial_state
    transitions: list[Transition] = []

    snapshot = engine.snapshot(initial_state)
    snapshots: list[WorldSnapshot] = [snapshot]
    last_snapshot_id = snapshot.snapshot_id

    t0 = time.perf_counter()
    for i in range(steps):
        agent_id = f"agent-{i % 4}"
        action = (
            Action(agent_id=agent_id, action_type=ActionType.GATHER, params={"resource": "food", "amount": 1})
            if i % 2 == 0
            else Action(agent_id=agent_id, action_type=ActionType.WAIT)
        )
        exog = ExogenousInput(
            tick=i + 1,
            events=({"type": "regen"},) if (i + 1) % 5 == 0 else (),
        )
        transition = engine.step(state, action, exogenous_input=exog, seed=seed)
        transitions.append(transition)
        state = transition.next_state
        if (i + 1) % resolved_snapshot_interval == 0:
            periodic_snapshot = engine.snapshot(state, parent_snapshot_id=last_snapshot_id)
            snapshots.append(periodic_snapshot)
            last_snapshot_id = periodic_snapshot.snapshot_id
    step_seconds = max(time.perf_counter() - t0, 1e-9)

    snapshot_bytes = len(snapshot.model_dump_json().encode("utf-8"))
    growth_events: list[GrowthEvent] = []
    for tr in transitions:
        raw_events = tr.emission.data.get("growth_events", ())
        if isinstance(raw_events, list | tuple):
            growth_events.extend(GrowthEvent.model_validate(item) for item in raw_events)

    t1 = time.perf_counter()
    with TransitionLogStore(db_path) as store:
        for snap in snapshots:
            store.save_snapshot(snap)
        for tr in transitions:
            store.append(tr, run_id="pilot-run", branch_id="main")
        if growth_events:
            store.append_growth_events(growth_events, run_id="pilot-run", branch_id="main")
    write_seconds = max(time.perf_counter() - t1, 1e-9)

    t2 = time.perf_counter()
    replay_result = replay_transitions(engine, initial_state, transitions)
    replay_seconds = max(time.perf_counter() - t2, 1e-9)

    db_bytes = db_path.stat().st_size if db_path.exists() else 0
    return EnvironmentPilotMetrics(
        steps=steps,
        step_seconds=step_seconds,
        ticks_per_second=steps / step_seconds,
        write_seconds=write_seconds,
        writes_per_second=steps / write_seconds,
        replay_seconds=replay_seconds,
        replay_exact_match=replay_result.exact_match,
        snapshot_bytes=snapshot_bytes,
        db_bytes=db_bytes,
    )

