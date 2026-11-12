"""Phase 1.1 — Snapshot, branching, restore, and exact-replay helpers.

Design authority: docs/phases/1.1-environment.md, ADR 0004, ADR 0005.
Citations: Tycho (arXiv:2607.28287) for deterministic replay and branch restoration;
ADR 0005 (docs/adr/0005-transition-semantics-and-dual-track-evaluation.md) clarifying that
exact replay is a mechanistic verification property rather than proof of causal
identification. Long-horizon rig-scale replay performance remains empirically untested
until Phase 1.1 experiments are run.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants
from evolzen.schemas.transition import State, Transition
from evolzen.schemas.world import BranchRecord, WorldSnapshot, WorldState
from evolzen.storage.transition_log import TransitionLogStore


@dataclass(frozen=True)
class ReplayResult:
    """Outcome of replaying recorded transitions through `SocialSandboxEngine`."""

    total_transitions: int
    matched: int
    mismatches: tuple[str, ...]
    invariant_failures: tuple[str, ...]
    final_state: State

    @property
    def exact_match(self) -> bool:
        """True iff every replayed transition reproduced emission, state, and invariants."""
        return (
            self.matched == self.total_transitions
            and not self.mismatches
            and not self.invariant_failures
        )


def replay_transitions(
    engine: SocialSandboxEngine,
    initial_state: State,
    transitions: Sequence[Transition],
) -> ReplayResult:
    """Re-execute `transitions` from `initial_state` and verify exact state/emission match."""
    current_state = initial_state
    matched = 0
    mismatches: list[str] = []
    invariant_failures: list[str] = []

    for idx, recorded in enumerate(transitions):
        if current_state.data != recorded.state.data:
            mismatches.append(f"step {idx}: initial state mismatch before transition {recorded.transition_id}")
        replayed = engine.step(
            recorded.state,
            recorded.action,
            recorded.exogenous_input,
            recorded.seed,
        )
        prev_world = WorldState.from_state(recorded.state)
        next_world = WorldState.from_state(replayed.next_state)
        report = check_invariants(prev_world, next_world)
        if not report.passed:
            invariant_failures.append(f"step {idx}: invariants failed ({report})")

        emission_ok = replayed.emission.data == recorded.emission.data
        next_ok = replayed.next_state.data == recorded.next_state.data
        if emission_ok and next_ok:
            matched += 1
        else:
            mismatches.append(
                f"step {idx} ({recorded.transition_id}): emission_ok={emission_ok}, next_state_ok={next_ok}"
            )
        current_state = replayed.next_state

    return ReplayResult(
        total_transitions=len(transitions),
        matched=matched,
        mismatches=tuple(mismatches),
        invariant_failures=tuple(invariant_failures),
        final_state=current_state,
    )


def replay_from_store(
    engine: SocialSandboxEngine,
    store: TransitionLogStore,
    *,
    run_id: str,
    branch_id: str = "main",
    up_to_tick: int | None = None,
) -> ReplayResult:
    """Restore the nearest snapshot in `store` and replay transitions forward."""
    snapshot = store.latest_snapshot(run_id, branch_id, max_tick=up_to_tick)
    if snapshot is None:
        raise KeyError(f"No snapshot found for run_id={run_id!r}, branch_id={branch_id!r}")
    initial_state = engine.restore(snapshot)
    raw_transitions = store.list_transitions(
        run_id=run_id,
        branch_id=branch_id,
        from_tick=snapshot.tick,
        to_tick=up_to_tick - 1 if up_to_tick is not None else None,
    )
    transitions = [
        tr
        for tr in raw_transitions
        if int(tr.state.data.get("step_index", 0)) >= snapshot.state.step_index
        and (
            up_to_tick is None
            or (
                int(tr.state.data.get("tick", 0)) < up_to_tick
                and int(tr.next_state.data.get("tick", 0)) <= up_to_tick
            )
        )
    ]
    return replay_transitions(engine, initial_state, transitions)


def branch_from_snapshot(
    engine: SocialSandboxEngine,
    store: TransitionLogStore,
    snapshot: WorldSnapshot,
    *,
    new_branch_id: str,
) -> tuple[BranchRecord, State]:
    """Fork a new immutable timeline branch from `snapshot` without mutating the parent."""
    restored_world = WorldState.from_state(engine.restore(snapshot))
    branched_world = restored_world.model_copy(update={"branch_id": new_branch_id})
    branched_state = branched_world.to_state()
    fork_snapshot = engine.snapshot(
        branched_state,
        snapshot_id=f"snap-{branched_world.run_id}-{new_branch_id}-{branched_world.tick}",
        parent_snapshot_id=snapshot.snapshot_id,
    )
    branch = BranchRecord(
        branch_id=new_branch_id,
        run_id=branched_world.run_id,
        parent_branch_id=snapshot.branch_id,
        fork_tick=snapshot.tick,
        fork_snapshot_id=fork_snapshot.snapshot_id,
    )
    store.save_snapshot_and_branch(fork_snapshot, branch)
    return branch, branched_state
