"""Phase 2.3 — Recognition Model & Growing Library. See README.md.

This is the project's central novel architectural contribution — read the module docstrings
in this package before touching them.
"""
from evolzen.recognition.embedding_router import EmbeddingRouter
from evolzen.recognition.jepa import JEPAEncoder
from evolzen.recognition.moe_library import SparseMoELibrary
from evolzen.recognition.wake_sleep import WakeSleepLearner

__all__ = ["JEPAEncoder", "WakeSleepLearner", "SparseMoELibrary", "EmbeddingRouter"]
