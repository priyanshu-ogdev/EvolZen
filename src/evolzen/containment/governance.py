"""Dynamic capability governance (Phase 2.2).

Replaces a purely static network-egress allow-list with permissions that tighten or loosen
based on observed agent behavior, following Sidik & Rokach (arXiv:2604.11839) and Microsoft's
2026 Agent Governance Toolkit. Read alongside "Safety Must Precede the Deployment of
Open-Ended AI" (arXiv:2502.04512) — this module exists because this project's agent population
is structurally exactly the kind of open-ended system that paper is about.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Capability(StrEnum):
    NETWORK_EGRESS = "network_egress"
    FILESYSTEM_WRITE = "filesystem_write"
    SELF_MODIFICATION = "self_modification"
    SPAWN_SUBPROCESS = "spawn_subprocess"


@dataclass
class GovernanceEvent:
    agent_id: str
    capability: Capability
    description: str


class CapabilityGovernor:
    """Tracks per-agent capability grants and tightens them on suspicious behavior.

    Phase 0 stub with working bookkeeping; the actual tightening/loosening policy (what counts
    as "suspicious," how quickly a capability is restored) is a Phase 2.2 research decision,
    not a scaffolding one.
    """

    def __init__(self) -> None:
        self._grants: dict[str, set[Capability]] = {}
        self._flagged_events: list[GovernanceEvent] = []

    def grant(self, agent_id: str, capability: Capability) -> None:
        self._grants.setdefault(agent_id, set()).add(capability)

    def revoke(self, agent_id: str, capability: Capability) -> None:
        self._grants.get(agent_id, set()).discard(capability)

    def has_capability(self, agent_id: str, capability: Capability) -> bool:
        return capability in self._grants.get(agent_id, set())

    def flag(self, event: GovernanceEvent) -> None:
        """Record a governance-relevant event (e.g. a containment-boundary probe from
        `evolzen.agents`). The actual policy for reacting to flags is left to research."""
        self._flagged_events.append(event)

    def flagged_events(self) -> list[GovernanceEvent]:
        return list(self._flagged_events)
