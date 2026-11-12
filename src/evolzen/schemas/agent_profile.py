"""Phase 1.2 — Unified Agent Profile and Identity Schema.

Defines the persistent social, institutional, and lineage identity contracts for agents
in the EvolZen multi-agent population (docs/ARCHITECTURE.md §3.2, docs/phases/1.2-agents.md,
ADR 0006, ADR 0008). Replaces the legacy five-coordinate `DriveVector` with a rich
social profile linked to `evolzen.schemas.world.WorldAgentState` and the eight-coordinate
developmental core (`evolzen.schemas.development.AgentDevelopmentState`).

Citations:
- Park et al. (Generative Agents, arXiv:2304.03442) for agent social identity, memory, and roles;
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392) for cultural transfer;
- Vassiliades et al. (CVT-MAP-Elites, IEEE TEVC 2018, DOI:10.1109/TEVC.2017.2735550) for
  behavioral descriptor keys in high-dimensional phenotype archives.

These contracts are an EvolZen specification choice and remain empirically untested until
Phase 1.2 population experiments are run.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonNegInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class AgentProfile(BaseModel):
    """Immutable identity, lineage, institutional, and behavioral descriptor record."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    agent_id: Identifier
    lineage_id: Identifier
    generation: NonNegInt = 0
    parents: tuple[Identifier, ...] = ()
    roles: tuple[Identifier, ...] = ("generalist",)
    institutional_affiliations: tuple[Identifier, ...] = ()
    adopted_norms: tuple[Identifier, ...] = ()
    memory_horizon: PositiveInt = 32
    base_model_id: Identifier = "default-small-llm"
    adapter_checkpoint: str | None = None
    behavioral_descriptor: tuple[float, ...] = ()

    def descriptor_vector(self) -> list[float]:
        """Return the behavioral descriptor as a mutable list for distance calculations."""
        return list(self.behavioral_descriptor)
