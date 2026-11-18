"""Phase 1.2 — Unified Agent Profile, Identity, Lineage, and Population Snapshot Schemas.

Defines the persistent social, institutional, lineage identity, and population snapshot
contracts for agents in the EvolZen multi-agent population (docs/ARCHITECTURE.md §3.2,
docs/phases/1.2-agents.md, ADR 0006, ADR 0008). Replaces legacy interfaces with rich
social profiles linked to `evolzen.schemas.world.WorldAgentState` and the eight-coordinate
developmental core (`evolzen.schemas.development.AgentDevelopmentState`).

Citations:
- Park et al. (Generative Agents, arXiv:2304.03442) for agent social identity, memory, and roles;
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392) for cultural transfer;
- Vassiliades et al. (CVT-MAP-Elites, IEEE TEVC 2018, DOI:10.1109/TEVC.2017.2735550) for
  behavioral descriptor keys in high-dimensional phenotype archives;
- Zheng et al. (The AI Economist, Science Advances 2022) for macro-distribution tracking.

These contracts are an EvolZen specification choice and remain empirically untested until
Phase 1.2 population experiments are run.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonNegInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(ge=1)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


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
    base_model_id: Identifier = "Qwen/Qwen3.5-9B-VL-AWQ"
    adapter_tier: str = "tier1"  # 'tier1' (LoRA tactical) or 'tier2' (DoRA deliberative)
    adapter_checkpoint: str | None = None
    tier2_adapter_checkpoint: str | None = None
    behavioral_descriptor: tuple[float, ...] = ()

    def descriptor_vector(self) -> list[float]:
        """Return the behavioral descriptor as a mutable list for distance calculations."""
        return list(self.behavioral_descriptor)


class LineageNode(BaseModel):
    """Genealogical graph node representing one agent in a family lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    agent_id: Identifier
    lineage_id: Identifier
    generation: NonNegInt
    parents: tuple[Identifier, ...] = ()
    children: tuple[Identifier, ...] = ()
    born_at: NonNegInt
    died_at: NonNegInt | None = None
    roles: tuple[Identifier, ...] = ("generalist",)
    behavioral_descriptor: tuple[float, ...] = ()


class LineageSnapshot(BaseModel):
    """Immutable genealogical tree and survival state for one distinct agent lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    lineage_id: Identifier
    founder_id: Identifier
    nodes: dict[str, LineageNode] = Field(default_factory=dict)
    active_members: tuple[Identifier, ...] = ()
    is_extinct: bool = False
    extinct_at_tick: NonNegInt | None = None
    total_born: NonNegInt = 0
    max_generation: NonNegInt = 0


class CommunicationGraphSnapshot(BaseModel):
    """Sparse communication and trade interaction graph across the population."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    nodes: tuple[Identifier, ...] = ()
    interactions: dict[str, dict[str, int]] = Field(default_factory=dict)
    total_interactions: NonNegInt = 0
    edge_density: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)] = 0.0


class PopulationSnapshot(BaseModel):
    """Comprehensive snapshot of population state, lineages, diversity, and topology."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    snapshot_id: Identifier
    tick: NonNegInt
    generation: NonNegInt = 0
    total_agents: NonNegInt
    active_population: NonNegInt
    profiles: dict[str, AgentProfile] = Field(default_factory=dict)
    lineages: dict[str, LineageSnapshot] = Field(default_factory=dict)
    communication_graph: CommunicationGraphSnapshot = Field(
        default_factory=CommunicationGraphSnapshot
    )
    archive_coverage: NonNegInt = 0
    gini_coefficient: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)] = 0.0
    role_distribution: dict[str, int] = Field(default_factory=dict)
