"""Phase 1.2 — Unified Agent Subsystem.

Combines the eight-coordinate developmental runtime, structured LLM inference backends,
CVT-MAP-Elites behavioral archiving, and sandboxed capability self-modification.

Design authority: docs/phases/1.2-agents.md, ADR 0006, ADR 0008.
"""
from evolzen.agents.agent import Agent
from evolzen.agents.development import (
    DevelopmentArchive,
    advance,
    born,
    decide,
    drive_step,
    inherit_genome,
    observe,
    sample_genome,
    stage_at,
    teach,
)
from evolzen.agents.inference import InferenceBackend, TransformersBackend, VLLMBackend
from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry, QualityDiversityArchive
from evolzen.agents.scheduler import PopulationScheduler, PopulationSchedulerMetrics
from evolzen.agents.self_modification import (
    SelfModificationProposal,
    apply_profile_update,
    evaluate_proposal,
)

__all__ = [
    # Unified Agent Runtime
    "Agent",
    # Population Scheduler
    "PopulationScheduler",
    "PopulationSchedulerMetrics",
    # Developmental Core Functions & Lifecycle
    "born",
    "advance",
    "decide",
    "observe",
    "teach",
    "stage_at",
    "drive_step",
    "inherit_genome",
    "sample_genome",
    "DevelopmentArchive",
    # Structured Inference Backends
    "InferenceBackend",
    "TransformersBackend",
    "VLLMBackend",
    # Quality-Diversity Archives
    "QualityDiversityArchive",
    "CVTArchive",
    "QDArchiveEntry",
    # Sandboxed Self-Modification
    "SelfModificationProposal",
    "evaluate_proposal",
    "apply_profile_update",
]
