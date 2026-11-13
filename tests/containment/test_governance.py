"""Tests for Phase 2.2 dynamic capability governance and audit trails."""
from __future__ import annotations

import hashlib
from typing import Any

from evolzen.containment.governance import (
    Capability,
    CapabilityGovernor,
    GovernanceEvent,
)
from evolzen.schemas.world import ActionType, CapabilityPackage


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


def test_register_capability_enum_and_grants() -> None:
    assert Capability.REGISTER_CAPABILITY.value == "register_capability"

    gov = CapabilityGovernor()
    assert gov.has_capability("agent-gov", Capability.REGISTER_CAPABILITY) is False

    gov.grant("agent-gov", Capability.REGISTER_CAPABILITY)
    assert gov.has_capability("agent-gov", Capability.REGISTER_CAPABILITY) is True

    gov.revoke("agent-gov", Capability.REGISTER_CAPABILITY)
    assert gov.has_capability("agent-gov", Capability.REGISTER_CAPABILITY) is False


def test_record_violation_dynamic_tightening() -> None:
    gov = CapabilityGovernor()
    gov.grant("agent-bad", Capability.NETWORK_EGRESS)
    gov.grant("agent-bad", Capability.FILESYSTEM_WRITE)
    gov.grant("agent-bad", Capability.REGISTER_CAPABILITY)

    assert gov.has_capability("agent-bad", Capability.NETWORK_EGRESS) is True
    assert gov.has_capability("agent-bad", Capability.FILESYSTEM_WRITE) is True
    assert gov.has_capability("agent-bad", Capability.REGISTER_CAPABILITY) is True

    # Violate network egress
    event = gov.record_violation(
        agent_id="agent-bad",
        capability=Capability.NETWORK_EGRESS,
        reason="Detected outbound connection attempt to unauthorized port",
        tick=42,
    )

    # Dynamic tightening: immediately revoked
    assert gov.has_capability("agent-bad", Capability.NETWORK_EGRESS) is False
    # Other capabilities remain unaffected
    assert gov.has_capability("agent-bad", Capability.FILESYSTEM_WRITE) is True
    assert gov.has_capability("agent-bad", Capability.REGISTER_CAPABILITY) is True

    # Event integrity
    assert event.agent_id == "agent-bad"
    assert event.capability == Capability.NETWORK_EGRESS
    assert event.description == "Detected outbound connection attempt to unauthorized port"
    assert event.tick == 42
    assert event.severity == "violation"
    assert event.hash_digest != ""
    assert event in gov.flagged_events()


def test_verify_capability_package_gating() -> None:
    gov = CapabilityGovernor()

    # Valid verified package
    valid_pkg = CapabilityPackage(
        package_id="pkg-plow",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 2, "iron": 1},
        output_kind="plow",
        min_age=5,
        verified_containment=True,
    )
    assert gov.verify_capability_package(valid_pkg) is True

    # Fail-closed gate: unverified containment
    unverified_pkg = CapabilityPackage(
        package_id="pkg-plow",
        version="1.0.0",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 2, "iron": 1},
        output_kind="plow",
        min_age=5,
        verified_containment=False,
    )
    assert gov.verify_capability_package(unverified_pkg) is False

    # Bound checks: empty package_id or output_kind or version
    empty_id_pkg = valid_pkg.model_copy(update={"package_id": ""})
    assert gov.verify_capability_package(empty_id_pkg) is False

    empty_kind_pkg = valid_pkg.model_copy(update={"output_kind": ""})
    assert gov.verify_capability_package(empty_kind_pkg) is False

    empty_version_pkg = valid_pkg.model_copy(update={"version": ""})
    assert gov.verify_capability_package(empty_version_pkg) is False

    # Bound checks: negative min_age and negative resource requirements
    negative_age_pkg = CapabilityPackage.model_construct(**{**valid_pkg.model_dump(), "min_age": -1})
    assert gov.verify_capability_package(negative_age_pkg) is False

    negative_res_pkg = valid_pkg.model_copy(update={"required_resources": {"wood": -1}})
    assert gov.verify_capability_package(negative_res_pkg) is False


def test_export_audit_trail_and_sha256_chaining() -> None:
    gov = CapabilityGovernor()

    # Initial state: genesis hash (64 zeros) and empty trail
    genesis_hash = "0" * 64
    assert gov.audit_hash() == genesis_hash
    assert gov.export_audit_trail() == []

    # First event
    ev1 = GovernanceEvent(
        agent_id="agent-1",
        capability=Capability.FILESYSTEM_WRITE,
        description="Write access to /etc probe",
        tick=10,
        severity="warning",
    )
    gov.flag(ev1)

    expected_hash_1 = hashlib.sha256(f"{genesis_hash}:{ev1.hash_digest}".encode()).hexdigest()
    assert gov.audit_hash() == expected_hash_1

    trail = gov.export_audit_trail()
    assert len(trail) == 1
    assert trail[0]["prev_hash"] == genesis_hash
    assert trail[0]["audit_hash"] == expected_hash_1
    assert trail[0]["agent_id"] == "agent-1"
    assert trail[0]["capability"] == "filesystem_write"
    assert trail[0]["severity"] == "warning"

    # Second event via record_violation
    ev2 = gov.record_violation(
        agent_id="agent-2",
        capability=Capability.SPAWN_SUBPROCESS,
        reason="Subprocess spawn attempt",
        tick=11,
    )

    expected_hash_2 = hashlib.sha256(f"{expected_hash_1}:{ev2.hash_digest}".encode()).hexdigest()
    assert gov.audit_hash() == expected_hash_2

    trail2 = gov.export_audit_trail()
    assert len(trail2) == 2
    assert trail2[1]["prev_hash"] == expected_hash_1
    assert trail2[1]["audit_hash"] == expected_hash_2
    assert trail2[1]["severity"] == "violation"

    # Test export immutability (modifying returned list does not mutate internal trail)
    trail2.append({"tampered": True})
    assert len(gov.export_audit_trail()) == 2


def test_governance_deterministic_audit_hashes() -> None:
    # Two independent governors receiving identical events produce identical hashes
    gov_a = CapabilityGovernor()
    gov_b = CapabilityGovernor()

    for idx in range(3):
        gov_a.record_violation(f"agent-{idx}", Capability.NETWORK_EGRESS, f"violation {idx}", tick=idx)
        gov_b.record_violation(f"agent-{idx}", Capability.NETWORK_EGRESS, f"violation {idx}", tick=idx)

    assert gov_a.audit_hash() == gov_b.audit_hash()
    assert gov_a.export_audit_trail() == gov_b.export_audit_trail()


def test_governance_event_serialization() -> None:
    event = GovernanceEvent(
        agent_id="agent-serialize",
        capability=Capability.REGISTER_CAPABILITY,
        description="Registration check",
        tick=5,
        severity="info",
    )
    data: dict[str, Any] = event.to_dict()
    assert data["agent_id"] == "agent-serialize"
    assert data["capability"] == "register_capability"
    assert data["description"] == "Registration check"
    assert data["tick"] == 5
    assert data["severity"] == "info"
    assert data["hash_digest"] == event.hash_digest
