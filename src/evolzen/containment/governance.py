"""Dynamic capability governance (Phase 2.2).

Replaces a purely static network-egress allow-list with permissions that tighten or loosen
based on observed agent behavior, following Sidik & Rokach (arXiv:2604.11839) and Microsoft's
2026 Agent Governance Toolkit. Read alongside "Safety Must Precede the Deployment of
Open-Ended AI" (arXiv:2502.04512) — this module exists because this project's agent population
is structurally exactly the kind of open-ended system that paper is about.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from evolzen.schemas.world import CapabilityPackage

_GENESIS_HASH: str = "0" * 64


class Capability(StrEnum):
    """Capabilities subject to dynamic governance and fail-closed isolation."""

    NETWORK_EGRESS = "network_egress"
    FILESYSTEM_WRITE = "filesystem_write"
    SELF_MODIFICATION = "self_modification"
    SPAWN_SUBPROCESS = "spawn_subprocess"
    REGISTER_CAPABILITY = "register_capability"


@dataclass
class GovernanceEvent:
    """Audit event recorded when governance policy is probed or violated."""

    agent_id: str
    capability: Capability
    description: str
    tick: int = 0
    severity: str = "warning"
    hash_digest: str = ""

    def __post_init__(self) -> None:
        if not self.hash_digest:
            self.hash_digest = self.compute_digest()

    def compute_digest(self) -> str:
        """Compute deterministic SHA-256 digest over the event attributes."""
        payload = {
            "agent_id": self.agent_id,
            "capability": str(self.capability),
            "description": self.description,
            "tick": self.tick,
            "severity": self.severity,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to a dictionary representation."""
        return {
            "agent_id": self.agent_id,
            "capability": str(self.capability),
            "description": self.description,
            "tick": self.tick,
            "severity": self.severity,
            "hash_digest": self.hash_digest,
        }


class CapabilityGovernor:
    """Tracks per-agent capability grants, enforces containment gates, and logs audit chains.

    Implements dynamic capability governance following Sidik & Rokach (arXiv:2604.11839)
    and fail-closed containment boundaries (Phase 2.2).
    """

    def __init__(self) -> None:
        self._grants: dict[str, set[Capability]] = {}
        self._flagged_events: list[GovernanceEvent] = []
        self._audit_trail: list[dict[str, Any]] = []
        self._current_audit_hash: str = _GENESIS_HASH

    def grant(self, agent_id: str, capability: Capability) -> None:
        """Grant a capability to an agent."""
        self._grants.setdefault(agent_id, set()).add(capability)

    def revoke(self, agent_id: str, capability: Capability) -> None:
        """Revoke a capability from an agent."""
        self._grants.get(agent_id, set()).discard(capability)

    def has_capability(self, agent_id: str, capability: Capability) -> bool:
        """Check whether an agent holds a capability."""
        return capability in self._grants.get(agent_id, set())

    def flag(self, event: GovernanceEvent) -> None:
        """Record a governance-relevant event and update the tamper-evident audit chain."""
        self._flagged_events.append(event)
        prev_hash = self._current_audit_hash
        entry_hash = hashlib.sha256(
            f"{prev_hash}:{event.hash_digest}".encode()
        ).hexdigest()
        self._current_audit_hash = entry_hash
        trail_entry = {
            **event.to_dict(),
            "prev_hash": prev_hash,
            "audit_hash": entry_hash,
        }
        self._audit_trail.append(trail_entry)

    def flagged_events(self) -> list[GovernanceEvent]:
        """Return a copy of all recorded governance events."""
        return list(self._flagged_events)

    def record_violation(
        self,
        agent_id: str,
        capability: Capability,
        reason: str,
        tick: int = 0,
    ) -> GovernanceEvent:
        """Immediately revoke capability, log violation event, and update audit hash."""
        self.revoke(agent_id, capability)
        event = GovernanceEvent(
            agent_id=agent_id,
            capability=capability,
            description=reason,
            tick=tick,
            severity="violation",
        )
        self.flag(event)
        return event

    def verify_capability_package(self, package: CapabilityPackage) -> bool:
        """Verify that a capability package passes containment gate and bounds checks."""
        # Fail-closed containment check
        if not getattr(package, "verified_containment", False):
            return False

        # Bounds checks
        if not package.package_id or not str(package.package_id).strip():
            return False
        if not package.output_kind or not str(package.output_kind).strip():
            return False
        if not package.version or not str(package.version).strip():
            return False
        if package.min_age < 0:
            return False
        return not any(qty < 0 for qty in package.required_resources.values())

    def export_audit_trail(self) -> list[dict[str, Any]]:
        """Return the complete audit trail as a list of dictionaries."""
        return [dict(entry) for entry in self._audit_trail]

    def audit_hash(self) -> str:
        """Return the current SHA-256 audit chain head hash."""
        return self._current_audit_hash
