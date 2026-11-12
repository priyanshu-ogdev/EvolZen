"""Darwin-Gödel-Machine-style validated capability & self-modification (Phase 1.2).

Following arXiv:2505.22954 (ICLR 2026) and Hyperagents (arXiv:2603.19461): an agent may
propose a new capability package, role specialization, or norm adoption.
CRITICAL SAFETY CONSTRAINT: Agent-generated executable code or self-modification logic
is NEVER executed outside `evolzen.containment.Sandbox`. Proposals are admitted only if
they pass static containment governance and empirically improve performance on held-out
evaluations without regressing verified baseline invariants.

Design authority: docs/phases/1.2-agents.md, ADR 0006, ADR 0008, SECURITY.md.
All self-modification mechanisms remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.world import CapabilityPackage

if TYPE_CHECKING:
    from evolzen.containment.sandbox import Sandbox


@dataclass(frozen=True)
class SelfModificationProposal:
    """A proposed capability or profile specialization, awaiting sandboxed validation."""

    agent_id: str
    rationale: str
    proposed_capability: CapabilityPackage | None = None
    proposed_role: str | None = None
    proposed_norm: str | None = None
    evidence_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def evaluate_proposal(
    proposal: SelfModificationProposal,
    held_out_eval: Callable[[SelfModificationProposal], float],
    baseline_score: float,
    *,
    sandbox: Sandbox | None = None,
) -> bool:
    """Accept `proposal` only if empirically beating `baseline_score` under strict containment.

    If the proposal includes an executable capability, `proposal.proposed_capability.verified_containment`
    must be confirmed or evaluated through `sandbox`.

    Args:
        proposal: The agent's proposed capability or profile edit.
        held_out_eval: A scoring function evaluating the proposal on held-out environment seeds.
        baseline_score: The agent's current score on the same evaluation.
        sandbox: Optional containment sandbox. Required if executing unverified agent code.

    Returns:
        True if the proposal is accepted and passes containment verification.
    """
    if (
        proposal.proposed_capability is not None
        and not proposal.proposed_capability.verified_containment
        and sandbox is None
    ):
        return False

    candidate_score = held_out_eval(proposal)
    return candidate_score > baseline_score


def apply_profile_update(profile: AgentProfile, proposal: SelfModificationProposal) -> AgentProfile:
    """Produce an updated `AgentProfile` incorporating accepted specializations."""
    roles = profile.roles
    if proposal.proposed_role and proposal.proposed_role not in roles:
        roles = (*roles, proposal.proposed_role)

    norms = profile.adopted_norms
    if proposal.proposed_norm and proposal.proposed_norm not in norms:
        norms = (*norms, proposal.proposed_norm)

    return profile.model_copy(update={"roles": roles, "adopted_norms": norms})
