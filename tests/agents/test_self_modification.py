"""Unit tests for sandboxed self-modification and capability proposals."""
from __future__ import annotations

from evolzen.agents.self_modification import (
    SelfModificationProposal,
    apply_profile_update,
    evaluate_proposal,
)
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.world import ActionType, CapabilityPackage


def test_evaluate_proposal_rejects_unverified_capability_without_sandbox() -> None:
    pkg = CapabilityPackage(
        package_id="craft:unverified_tool:v1",
        action_type=ActionType.CRAFT,
        output_kind="tool",
        verified_containment=False,
    )
    proposal = SelfModificationProposal(
        agent_id="agent-0",
        rationale="New tool invention",
        proposed_capability=pkg,
    )

    accepted = evaluate_proposal(
        proposal,
        held_out_eval=lambda p: 10.0,
        baseline_score=5.0,
        sandbox=None,
    )
    # Must reject unverified capability if sandbox is not provided
    assert accepted is False


def test_evaluate_proposal_accepts_verified_improvement() -> None:
    pkg = CapabilityPackage(
        package_id="craft:verified_tool:v1",
        action_type=ActionType.CRAFT,
        output_kind="tool",
        verified_containment=True,
    )
    proposal = SelfModificationProposal(
        agent_id="agent-0",
        rationale="Verified tool invention",
        proposed_capability=pkg,
    )

    accepted = evaluate_proposal(
        proposal,
        held_out_eval=lambda p: 10.0,
        baseline_score=5.0,
        sandbox=None,
    )
    assert accepted is True


def test_apply_profile_update_adds_roles_and_norms() -> None:
    profile = AgentProfile(agent_id="agent-0", lineage_id="lineage-0", roles=("generalist",))
    proposal = SelfModificationProposal(
        agent_id="agent-0",
        rationale="Role specialization",
        proposed_role="blacksmith",
        proposed_norm="conserve_ore",
    )
    updated = apply_profile_update(profile, proposal)
    assert "blacksmith" in updated.roles
    assert "generalist" in updated.roles
    assert "conserve_ore" in updated.adopted_norms

