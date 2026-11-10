"""Darwin-Gödel-Machine-style validated self-modification (Phase 1.2).

Following arXiv:2505.22954 (ICLR 2026): an agent may propose an edit to its own policy code or
drive-vector. The edit is kept only if it empirically improves performance on a held-out
evaluation, and the full archive of variants is retained (never overwritten) — a working,
published analogue of the "reproduction" mechanic in the project's original blueprint, without
the neural-network weight-alignment failure mode literal crossover runs into.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from evolzen.schemas.drive_vector import DriveVector


@dataclass(frozen=True)
class SelfModificationProposal:
    """A proposed edit to an agent's own drive-vector, awaiting empirical validation."""

    agent_id: str
    proposed_drive_vector: DriveVector
    rationale: str


def evaluate_proposal(
    proposal: SelfModificationProposal,
    held_out_eval: Callable[[DriveVector], float],
    baseline_score: float,
) -> bool:
    """Accept `proposal` only if it empirically beats `baseline_score` on `held_out_eval`.

    Args:
        proposal: the agent's self-proposed edit.
        held_out_eval: a function scoring a drive-vector on a held-out evaluation (Phase 0
            callers should pass a real evaluation once Phase 1.1's domain exists).
        baseline_score: the agent's current (pre-edit) score on the same evaluation.

    Returns:
        True if the proposal is accepted and should be archived as a new QD-archive entry
        (never overwriting the parent).
    """
    candidate_score = held_out_eval(proposal.proposed_drive_vector)
    return candidate_score > baseline_score
