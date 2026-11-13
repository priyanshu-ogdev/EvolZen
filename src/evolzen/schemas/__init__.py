"""Shared Pydantic schemas — the data contract every subsystem reads and writes through.

Changing anything in this subpackage is a change every one of the nine subsystems must be
checked against. See the parent package README's "shared foundation" section before editing.
"""
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import (
    AgentDevelopmentState,
    BirthGenome,
    BirthRecord,
    BrainSnapshot,
    Candidate,
    Decision,
    DevelopmentConfig,
    Lesson,
    LifeStage,
    Motive,
    Outcome,
    Signal,
    SkillEstimate,
    Stage,
)
from evolzen.schemas.library import (
    AuditEvent,
    AuditEventType,
    ProvenanceClass,
    RegressionResult,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
    ValidityContext,
    VerificationEvidence,
)
from evolzen.schemas.manual import (
    Manual,
    ManualEntry,
    ManualEntryStatus,
    ProvenanceRecord,
    ProvenanceSource,
)
from evolzen.schemas.transition import Action, Emission, ExogenousInput, State, Transition
from evolzen.schemas.world import ActionType, WorldAgentState, WorldState

__all__ = [
    # transition schemas
    "State",
    "Action",
    "ExogenousInput",
    "Emission",
    "Transition",
    # identity & development schemas (Phase 1.2)
    "AgentProfile",
    "AgentDevelopmentState",
    "BirthGenome",
    "BirthRecord",
    "BrainSnapshot",
    "Candidate",
    "Decision",
    "DevelopmentConfig",
    "Lesson",
    "LifeStage",
    "Motive",
    "Outcome",
    "Signal",
    "SkillEstimate",
    "Stage",
    # world schemas (Phase 1.1)
    "ActionType",
    "WorldAgentState",
    "WorldState",
    # manual schemas (Phase 1.3)
    "Manual",
    "ManualEntry",
    "ManualEntryStatus",
    "ProvenanceRecord",
    "ProvenanceSource",
    # library schemas (Phase 1.5)
    "AuditEvent",
    "AuditEventType",
    "ProvenanceClass",
    "RegressionResult",
    "RuleEntry",
    "RuleStatus",
    "SupersessionLink",
    "ValidityContext",
    "VerificationEvidence",
]
