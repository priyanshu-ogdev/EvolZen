"""Falsifiable manual store with a mandatory real-data floor (Phase 1.3).

Manuals (`evolzen.schemas.manual.Manual`) are the primary Phase 1.3 knowledge-transfer
mechanism — natural-language, actively revised, requiring no gradient step. This module
enforces the real-data floor: purely recursive training on prior generations' own synthetic
output is the reference mechanism producing distribution collapse and diversity loss.

Design authority: `docs/phases/1.3-economy.md`.
Citations:
    - Model collapse & provenance floor: Shumailov et al. (Nature, 2024, DOI: 10.1038/s41586-024-07566-y).
    - Inspectable manual transfer: Agno (2026, agno2026manual).
    - Multi-agent welfare & policy: Zheng et al. (Science Advances, 2022, DOI: 10.1126/sciadv.abk2607).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from evolzen.schemas.manual import (
    Manual,
    ManualEntry,
    ManualEntryStatus,
    ProvenanceCategory,
    ProvenanceRecord,
)


class RealDataFloorViolation(Exception):
    """Raised when a generation's training corpus falls below the configured real-data floor."""


class KnowledgeTransferReport(BaseModel):
    """Measurement of capability transfer between agents via manual consumption.

    Citation:
        Agno (2026, agno2026manual) — measured capability gain without gradient steps.
    """

    situation_key: str
    num_novice_trials: int
    num_baseline_trials: int
    mean_novice_score: float
    mean_baseline_score: float
    absolute_gain: float
    relative_gain: float
    transfer_effective: bool
    evidence_ids: tuple[str, ...] = Field(default=())
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManualStore:
    """Keyed store of Manuals, one per `situation_key`, with a real-data floor check.

    Enforces that knowledge transfer maintains a minimum fraction of non-recursive,
    human-authored, demonstration, or independent simulator traces to prevent recursive
    model collapse.
    """

    def __init__(self, real_data_floor: float) -> None:
        if not 0.0 <= real_data_floor <= 1.0:
            raise ValueError("real_data_floor must be in [0, 1]")
        self._real_data_floor = real_data_floor
        self._manuals: dict[str, Manual] = {}

    @property
    def real_data_floor(self) -> float:
        """Configured real-data floor in [0, 1]."""
        return self._real_data_floor

    def get_or_create(self, situation_key: str) -> Manual:
        """Retrieve existing manual for `situation_key` or initialize a new empty one."""
        if situation_key not in self._manuals:
            self._manuals[situation_key] = Manual(situation_key=situation_key)
        return self._manuals[situation_key]

    def get(self, situation_key: str) -> Manual | None:
        """Retrieve manual if present, else None."""
        return self._manuals.get(situation_key)

    def list_manuals(self) -> list[Manual]:
        """Return all stored manuals in key order."""
        return [self._manuals[k] for k in sorted(self._manuals)]

    def check_real_data_floor(self, real_fraction: float | None = None) -> None:
        """Raise if a generation's corpus doesn't meet the real-data floor.

        Args:
            real_fraction: Proportion of training data from non-synthetic sources.
                If None, computes actual real fraction across all stored manuals
                using `manual.real_data_fraction()`.

        Raises:
            RealDataFloorViolation: When real_fraction < self._real_data_floor.
        """
        if real_fraction is None:
            if not self._manuals:
                actual_fraction = 1.0
            else:
                total_entries = sum(len(m.entries) for m in self._manuals.values())
                if total_entries == 0:
                    actual_fraction = 1.0
                else:
                    real_entries = sum(
                        m.real_data_fraction() * len(m.entries)
                        for m in self._manuals.values()
                    )
                    actual_fraction = float(real_entries / total_entries)
            real_fraction = actual_fraction

        if real_fraction < self._real_data_floor:
            raise RealDataFloorViolation(
                f"real_fraction={real_fraction:.3f} is below the configured floor "
                f"={self._real_data_floor:.3f}; halt this generation (see docs/phases/1.3-economy.md)."
            )

    def calculate_real_fraction(self, entries: Sequence[ManualEntry] | None = None) -> float:
        """Calculate the proportion of entries sourced from non-model-generated material.

        Non-model sources include HUMAN_AUTHORED, HUMAN_DEMONSTRATION, and SIMULATOR_TRACE.

        Args:
            entries: Sequence of entries to evaluate. If None, evaluates all stored entries.

        Returns:
            Fraction in [0.0, 1.0]. Returns 1.0 if corpus is empty.
        """
        targets: list[ManualEntry] = []
        if entries is not None:
            targets = list(entries)
        else:
            for m in self._manuals.values():
                targets.extend(m.entries)

        if not targets:
            return 1.0

        real_count = sum(1 for entry in targets if entry.is_ground_truth)
        return float(real_count / len(targets))

    def verify_generation_corpus(self, entries: Sequence[ManualEntry]) -> float:
        """Calculate the real data fraction of candidate training entries and assert floor compliance.

        Args:
            entries: Candidate training entries for an upcoming generation.

        Returns:
            Calculated real data fraction.

        Raises:
            RealDataFloorViolation: If calculated fraction is strictly below the configured floor.
        """
        fraction = self.calculate_real_fraction(entries)
        self.check_real_data_floor(fraction)
        return fraction

    def add_entry(
        self,
        situation_key: str,
        entry: ManualEntry | None = None,
        *,
        text: str = "",
        written_by: str = "",
        status: ManualEntryStatus = ManualEntryStatus.HYPOTHESIS,
        revised_from: str | None = None,
        evidence_ids: Sequence[str] = (),
        provenance: ProvenanceRecord | None = None,
        category: ProvenanceCategory | None = None,
    ) -> ManualEntry:
        """Add a manual entry to the manual for `situation_key`.

        Accepts either an instantiated :class:`ManualEntry` or keyword attributes.
        """
        manual = self.get_or_create(situation_key)
        if entry is not None:
            manual.add_entry(entry)
            return entry

        cat = category if category is not None else (
            provenance.category if provenance is not None else ProvenanceCategory.MODEL_GENERATED
        )
        new_entry = ManualEntry(
            text=text,
            status=status,
            written_by=written_by,
            revised_from=revised_from,
            evidence_ids=tuple(evidence_ids),
            provenance=provenance,
            category=cat,
        )
        manual.add_entry(new_entry)
        return new_entry

    def falsify_entry(
        self,
        situation_key: str,
        index: int,
        evidence_id: str | None = None,
    ) -> ManualEntry:
        """Falsify a manual entry by index upon empirical contradiction."""
        manual = self.get_or_create(situation_key)
        return manual.falsify_entry(index, evidence_id=evidence_id)

    falsify = falsify_entry

    def revise_entry(
        self,
        situation_key: str,
        index: int,
        new_text: str,
        written_by: str,
        evidence_id: str | None = None,
        provenance: ProvenanceRecord | None = None,
        category: ProvenanceCategory | None = None,
    ) -> ManualEntry:
        """Falsify a prior belief and introduce an updated revised belief linking prior text."""
        manual = self.get_or_create(situation_key)
        return manual.revise_entry(
            index,
            new_text=new_text,
            written_by=written_by,
            evidence_id=evidence_id,
            provenance=provenance,
            category=category,
        )

    revise = revise_entry

    def to_dict(self) -> dict[str, Any]:
        """Serialize ManualStore to a dictionary representation."""
        return {
            "real_data_floor": self._real_data_floor,
            "manuals": {k: m.model_dump(mode="json") for k, m in self._manuals.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManualStore:
        """Deserialize a ManualStore from dictionary data."""
        floor = float(data.get("real_data_floor", 0.0))
        store = cls(real_data_floor=floor)
        manuals_data = data.get("manuals", {})
        for k, m_dict in manuals_data.items():
            store._manuals[k] = Manual.model_validate(m_dict)
        return store

    def confirm(
        self,
        situation_key: str,
        index: int,
        evidence_id: str | None = None,
    ) -> ManualEntry:
        """Promote a manual belief to CONFIRMED based on supporting evidence."""
        manual = self.get_or_create(situation_key)
        return manual.confirm_entry(index, evidence_id=evidence_id)

    def measure_knowledge_transfer(
        self,
        situation_key: str,
        novice_eval: Sequence[float],
        baseline_eval: Sequence[float],
        min_relative_gain: float = 0.1,
    ) -> KnowledgeTransferReport:
        """Quantify forward capability transfer from manual exposure over unguided baseline.

        Args:
            situation_key: The scenario identifier evaluated.
            novice_eval: Scores achieved by agents reading active manual beliefs.
            baseline_eval: Scores achieved by unassisted baseline agents.
            min_relative_gain: Threshold of relative improvement to consider transfer effective.

        Returns:
            Structured :class:`KnowledgeTransferReport`.
        """
        if not novice_eval or not baseline_eval:
            raise ValueError("novice_eval and baseline_eval must each contain at least one score")

        mean_novice = float(sum(novice_eval) / len(novice_eval))
        mean_baseline = float(sum(baseline_eval) / len(baseline_eval))
        abs_gain = mean_novice - mean_baseline

        if abs(mean_baseline) > 1e-6:
            rel_gain = abs_gain / abs(mean_baseline)
        else:
            rel_gain = abs_gain if abs_gain > 0 else 0.0

        effective = rel_gain >= min_relative_gain

        return KnowledgeTransferReport(
            situation_key=situation_key,
            num_novice_trials=len(novice_eval),
            num_baseline_trials=len(baseline_eval),
            mean_novice_score=round(mean_novice, 4),
            mean_baseline_score=round(mean_baseline, 4),
            absolute_gain=round(abs_gain, 4),
            relative_gain=round(rel_gain, 4),
            transfer_effective=effective,
        )

    def verify_backward_compatibility(
        self,
        prior_scores: Sequence[float],
        updated_scores: Sequence[float],
        max_degradation: float = 0.05,
    ) -> bool:
        """Verify that newly revised manual entries do not cause catastrophic forgetting on prior tasks.

        Args:
            prior_scores: Evaluation scores before manual revision.
            updated_scores: Evaluation scores on the same benchmark after manual revision.
            max_degradation: Maximum allowable performance drop fraction.

        Returns:
            True if updated performance does not degrade by more than `max_degradation`.
        """
        if not prior_scores or not updated_scores:
            return True
        mean_prior = sum(prior_scores) / len(prior_scores)
        mean_updated = sum(updated_scores) / len(updated_scores)
        if mean_prior <= 0:
            return mean_updated >= mean_prior
        drop = (mean_prior - mean_updated) / mean_prior
        return bool(drop <= max_degradation)
