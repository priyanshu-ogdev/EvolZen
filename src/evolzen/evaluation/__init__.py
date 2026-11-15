"""Phase 2.4 — Held-Out Generalization Testing, Phase 2.5 — Evaluation & Publication.

See README.md.
"""
from evolzen.evaluation.dual_track import (
    DualTrackEvaluationRunner,
    DualTrackRunner,
    FreshTrackResult,
    PersistentTrackResult,
)
from evolzen.evaluation.procedural_env_gen import ProceduralEnvironmentGenerator
from evolzen.evaluation.report import EvaluationReport
from evolzen.evaluation.rhae_scorer import RHAEResult, RHAEScorer

__all__ = [
    "DualTrackEvaluationRunner",
    "DualTrackRunner",
    "EvaluationReport",
    "FreshTrackResult",
    "PersistentTrackResult",
    "ProceduralEnvironmentGenerator",
    "RHAEResult",
    "RHAEScorer",
]
