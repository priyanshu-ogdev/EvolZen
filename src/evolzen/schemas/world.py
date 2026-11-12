"""Phase 1.1 persistent world, growth-ledger, snapshot, and invariant contracts.

Implements the shared cross-subsystem data contracts specified in docs/ARCHITECTURE.md §4,
docs/phases/1.1-environment.md, ADR 0004 (six versioned entity families and bounded
extensibility), and ADR 0005 (transition semantics and dual-track evaluation), informed by
Tycho (arXiv:2607.28287). These contracts are an EvolZen specification choice and remain
empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field

from evolzen.schemas.transition import State

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
NonNegInt = Annotated[int, Field(ge=0)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class WorldRecord(BaseModel):
    """Frozen closed-schema base record for Phase 1.1 world contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


class GrowthCategory(StrEnum):
    """Allowed operational world-growth categories (docs/PRD.md G1a, ADR 0004)."""

    LOCATION_RESOURCE = "location_resource"
    ARTIFACT_CAPABILITY = "artifact_capability"
    CONTRACT_MARKET_INSTITUTION = "contract_market_institution"
    NORM_BELIEF_MANUAL = "norm_belief_manual"
    AGENT_ROLE_LINEAGE = "agent_role_lineage"


class GrowthAttribution(StrEnum):
    """Causal origin of a durable world-growth event (never hidden evaluator edits)."""

    AGENT_ACTION = "agent_action"
    ENDOGENOUS_PROCESS = "endogenous_process"
    EXOGENOUS_INPUT = "exogenous_input"


class ActionType(StrEnum):
    """Typed action vocabulary supported by the Phase 1.1 social sandbox."""

    WAIT = "wait"
    GATHER = "gather"
    MOVE = "move"
    CONSUME = "consume"
    CRAFT = "craft"
    TRADE = "trade"
    PROPOSE_CONTRACT = "propose_contract"
    FULFILL_CONTRACT = "fulfill_contract"
    FOUND_INSTITUTION = "found_institution"
    JOIN_INSTITUTION = "join_institution"
    CONTRIBUTE_INSTITUTION = "contribute_institution"
    PROPOSE_NORM = "propose_norm"
    ADOPT_NORM = "adopt_norm"
    ASSIGN_ROLE = "assign_role"
    SPAWN_OFFSPRING = "spawn_offspring"
    IMPROVE_LOCATION = "improve_location"
    REGISTER_CAPABILITY = "register_capability"


class LocationNode(WorldRecord):
    """One node in the persistent discrete location/resource graph."""

    location_id: Identifier
    name: Identifier
    neighbors: tuple[Identifier, ...] = ()
    resources: dict[str, NonNegInt] = Field(default_factory=dict)
    capacities: dict[str, NonNegInt] = Field(default_factory=dict)
    regen_rates: dict[str, NonNegInt] = Field(default_factory=dict)
    shock_factor: UnitFloat = 1.0


class WorldAgentState(WorldRecord):
    """World-owned authoritative state for one agent in the sandbox."""

    agent_id: Identifier
    location_id: Identifier
    born_at: NonNegInt = 0
    alive: bool = True
    energy: UnitFloat = 0.8
    fatigue: UnitFloat = 0.0
    currency: NonNegInt = 0
    inventory: dict[str, NonNegInt] = Field(default_factory=dict)
    role: str = "generalist"
    lineage_id: Identifier
    parents: tuple[Identifier, ...] = ()
    generation: NonNegInt = 0
    status: Annotated[float, Field(ge=0.0, allow_inf_nan=False)] = 0.0
    skills: tuple[str, ...] = ()
    institution_ids: tuple[Identifier, ...] = ()
    adopted_norms: tuple[Identifier, ...] = ()
    last_action_tick: NonNegInt = 0


class ArtifactRecord(WorldRecord):
    """Durable crafted object owned by an agent or institution at a location."""

    artifact_id: Identifier
    kind: Identifier
    creator_id: Identifier
    owner_id: Identifier
    location_id: Identifier
    created_tick: NonNegInt
    recipe_resources: dict[str, NonNegInt] = Field(default_factory=dict)
    durability: NonNegInt = 100


class CapabilityPackage(WorldRecord):
    """Typed, versioned capability package (ADR 0004 bounded extensibility).

    Capability packages declare typed resource requirements and effects rather than
    executing arbitrary code inside `evolzen.environment`.
    """

    package_id: Identifier
    version: Identifier = "1.0.0"
    action_type: Identifier = ActionType.CRAFT
    required_resources: dict[str, NonNegInt] = Field(default_factory=dict)
    output_kind: Identifier
    min_age: NonNegInt = 0
    evidence_id: str = ""
    verified_replay: bool = False
    verified_intervention: bool = False
    verified_containment: bool = False


class ContractRecord(WorldRecord):
    """Bilateral resource exchange contract between two agents."""

    contract_id: Identifier
    proposer_id: Identifier
    counterparty_id: Identifier
    offer_resource: Identifier
    offer_qty: Annotated[int, Field(ge=1)]
    request_resource: Identifier
    request_qty: Annotated[int, Field(ge=1)]
    status: Literal["open", "fulfilled", "cancelled"] = "open"
    created_tick: NonNegInt = 0


class InstitutionRecord(WorldRecord):
    """Persistent multi-agent institution holding shared resources and currency."""

    institution_id: Identifier
    name: Identifier
    founder_id: Identifier
    location_id: Identifier
    member_ids: tuple[Identifier, ...] = ()
    treasury: dict[str, NonNegInt] = Field(default_factory=dict)
    currency_reserve: NonNegInt = 0
    contribution_rate: UnitFloat = 0.1
    created_tick: NonNegInt = 0


class NormRecord(WorldRecord):
    """Explicit shared norm or rule belief adopted by agents."""

    norm_id: Identifier
    title: Identifier
    proposer_id: Identifier
    rule_kind: str = "conservation"
    adopters: tuple[Identifier, ...] = ()
    created_tick: NonNegInt = 0


class ResourceAccounting(WorldRecord):
    """Exact conservation ledger across world initial stocks, inflows, and sinks."""

    initial_resources: dict[str, NonNegInt] = Field(default_factory=dict)
    exogenous_inflows: dict[str, NonNegInt] = Field(default_factory=dict)
    consumed_or_decayed: dict[str, NonNegInt] = Field(default_factory=dict)
    initial_currency: NonNegInt = 0


def canonical_json(data: Any) -> str:
    """Serialize JSON-compatible data deterministically with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


class WorldState(WorldRecord):
    """Complete deterministic world state covering all six ADR 0004 entity families."""

    world_version: str = "world-v1"
    feature_schema_version: str = "features-v1"
    run_id: Identifier = "default-run"
    branch_id: Identifier = "main"
    tick: NonNegInt = 0
    step_index: NonNegInt = 0
    seed: int = 0
    max_ticks: Annotated[int, Field(ge=1)] = 2000
    max_agents: Annotated[int, Field(ge=1)] = 64
    lifespan: Annotated[int, Field(ge=1)] = 1500
    adulthood_age: NonNegInt = 300
    locations: dict[str, LocationNode] = Field(default_factory=dict)
    agents: dict[str, WorldAgentState] = Field(default_factory=dict)
    artifacts: dict[str, ArtifactRecord] = Field(default_factory=dict)
    capabilities: dict[str, CapabilityPackage] = Field(default_factory=dict)
    contracts: dict[str, ContractRecord] = Field(default_factory=dict)
    institutions: dict[str, InstitutionRecord] = Field(default_factory=dict)
    norms: dict[str, NormRecord] = Field(default_factory=dict)
    accounting: ResourceAccounting = Field(default_factory=ResourceAccounting)

    def canonical_dict(self) -> dict[str, Any]:
        """Return a deterministically ordered JSON-serializable dictionary."""
        raw = self.model_dump(mode="json")
        return json.loads(canonical_json(raw))  # type: ignore[no-any-return]

    def state_hash(self) -> str:
        """Compute deterministic SHA-256 hash of the complete canonical state."""
        return hashlib.sha256(canonical_json(self.canonical_dict()).encode("utf-8")).hexdigest()

    def to_state(self) -> State:
        """Convert to a `evolzen.schemas.transition.State` with deterministic `state_id`."""
        data = self.canonical_dict()
        digest = hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
        return State(state_id=uuid5(NAMESPACE_URL, f"evolzen:state:{digest}"), data=data)

    @classmethod
    def from_state(cls, state: State) -> WorldState:
        """Reconstruct a validated `WorldState` from a `State` envelope."""
        return cls.model_validate(state.data)


class WorldSnapshot(WorldRecord):
    """Versioned immutable world snapshot for persistence, restore, and branching."""

    snapshot_id: Identifier
    world_version: str = "world-v1"
    run_id: Identifier
    branch_id: Identifier
    tick: NonNegInt
    parent_snapshot_id: Identifier | None = None
    state_hash: str
    state: WorldState


class GrowthEvent(WorldRecord):
    """One durable, attributable world-growth record (Phase 1.1 growth ledger)."""

    event_id: Identifier
    tick: NonNegInt
    category: GrowthCategory
    attribution: GrowthAttribution
    actor_id: Identifier
    entity_id: Identifier
    summary: str
    transition_id: str


class WorldInvariant(WorldRecord):
    """Result of evaluating one declared world invariant."""

    name: Identifier
    description: str
    passed: bool
    details: str = ""


class InvariantReport(WorldRecord):
    """Aggregated invariant verification result for one state or transition."""

    tick: NonNegInt
    passed: bool
    checks: tuple[WorldInvariant, ...]


class BranchRecord(WorldRecord):
    """Metadata describing a forked world timeline."""

    branch_id: Identifier
    run_id: Identifier
    parent_branch_id: Identifier
    fork_tick: NonNegInt
    fork_snapshot_id: Identifier


class InterventionSpec(WorldRecord):
    """Minimal controlled-intervention specification (docs/phases/1.1-environment.md)."""

    intervention_id: Identifier
    kind: Literal["set_variable", "withhold_action"]
    target_path: str = ""
    value: Any = None
    withheld_agent_id: Identifier | None = None
    description: str = ""

