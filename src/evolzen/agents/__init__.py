"""Phase 1.2 — The Agents. See README.md."""
from evolzen.agents.drive_vector import Agent
from evolzen.agents.inference import InferenceBackend, TransformersBackend, VLLMBackend
from evolzen.agents.qd_archive import QualityDiversityArchive
from evolzen.agents.self_modification import SelfModificationProposal, evaluate_proposal

__all__ = [
    "Agent",
    "InferenceBackend",
    "TransformersBackend",
    "VLLMBackend",
    "QualityDiversityArchive",
    "SelfModificationProposal",
    "evaluate_proposal",
]
