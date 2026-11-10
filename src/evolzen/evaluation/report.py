"""Final honest evaluation report (Phase 2.5).

Every claim in the report must be traceable to a specific measured result. Critically, the
report must explicitly measure and disclose the gap between reused and genuinely fresh
held-out environments for this specific system — not a footnote, a citable finding in its own
right.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvaluationReport:
    """Structured container for the Phase 2.5 report.

    Deliberately has no "headline claim" field with free text — every reported number must
    come from one of the typed fields below, each traceable to a specific phase's success
    metric, so the report cannot accidentally drift into an unsupported claim.
    """

    in_sandbox_metrics: dict[str, float] = field(default_factory=dict)  # Phases 1.1-2.1
    containment_verified: bool = False  # Phase 2.2
    recognition_ablation_results: dict[str, float] = field(default_factory=dict)  # Phase 2.3
    held_out_rhae_score: float | None = None  # Phase 2.4
    human_reference_rhae: float | None = None  # Phase 2.4 calibration
    frontier_model_reference_rhae: float | None = None  # Phase 2.4 calibration
    reused_vs_fresh_score_gap: float | None = None  # Phase 2.5's most important honesty check
    negative_findings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Render a plain-text summary. Raises if the report is incomplete, on purpose — an
        incomplete report should never be silently rendered as if it were final."""
        if self.held_out_rhae_score is None:
            raise ValueError("held_out_rhae_score is required before a report can be summarized.")
        if self.reused_vs_fresh_score_gap is None:
            raise ValueError(
                "reused_vs_fresh_score_gap is required before a report can be summarized "
                "(see the Phase 2.5 honesty requirement)."
            )
        lines = [
            f"Held-out RHAE score: {self.held_out_rhae_score:.3f}",
            f"Human reference: {self.human_reference_rhae}",
            f"Frontier-model reference: {self.frontier_model_reference_rhae}",
            f"Reused-vs-fresh score gap: {self.reused_vs_fresh_score_gap:.3f}",
            f"Containment verified: {self.containment_verified}",
        ]
        if self.negative_findings:
            lines.append("Negative findings:")
            lines.extend(f"  - {f}" for f in self.negative_findings)
        return "\n".join(lines)
