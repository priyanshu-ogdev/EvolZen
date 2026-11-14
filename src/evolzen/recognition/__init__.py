"""Phase 2.3 — Recognition Model & Growing Library. See README.md.

This is the project's central novel architectural contribution — read the module docstrings
in this package before touching them.
"""
from evolzen.recognition.ablations import AblationCondition, AblationResult, AblationRunner
from evolzen.recognition.embedding_router import EmbeddingRouter
from evolzen.recognition.jepa import GroundedJEPAEncoder, JEPAEncoder
from evolzen.recognition.moe_library import SparseMoELibrary
from evolzen.recognition.wake_sleep import FantasyCase, WakeSleepLearner

__all__ = [
    "AblationCondition",
    "AblationResult",
    "AblationRunner",
    "EmbeddingRouter",
    "FantasyCase",
    "GroundedJEPAEncoder",
    "JEPAEncoder",
    "SparseMoELibrary",
    "WakeSleepLearner",
]
