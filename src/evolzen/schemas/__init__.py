"""Shared Pydantic schemas — the data contract every subsystem reads and writes through.

Changing anything in this subpackage is a change every one of the nine subsystems must be
checked against. See the parent package README's "shared foundation" section before editing.
"""
from evolzen.schemas.drive_vector import DriveVector
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
from evolzen.schemas.manual import Manual
from evolzen.schemas.transition import Action, Emission, ExogenousInput, State, Transition

__all__ = [
    # transition schemas
    "State",
    "Action",
    "ExogenousInput",
    "Emission",
    "Transition",
    # drive / manual schemas
    "DriveVector",
    "Manual",
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
