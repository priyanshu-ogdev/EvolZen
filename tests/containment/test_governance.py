from evolzen.containment.governance import Capability, CapabilityGovernor, GovernanceEvent


def test_grant_and_revoke() -> None:
    gov = CapabilityGovernor()
    gov.grant("agent-1", Capability.NETWORK_EGRESS)
    assert gov.has_capability("agent-1", Capability.NETWORK_EGRESS) is True
    gov.revoke("agent-1", Capability.NETWORK_EGRESS)
    assert gov.has_capability("agent-1", Capability.NETWORK_EGRESS) is False


def test_flag_records_events() -> None:
    gov = CapabilityGovernor()
    gov.flag(GovernanceEvent("agent-1", Capability.SELF_MODIFICATION, "attempted self-edit"))
    assert len(gov.flagged_events()) == 1
