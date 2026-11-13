"""The falsifiable manual schema (Phase 1.3 / Phase 2.3).

Modeled on a 2026 result (Agno) showing this mechanism requires no gradient step, is directly
inspectable, and produced a measured capability gain when a cheap model consumed a frontier
model's manual rather than re-deriving the same knowledge. Written and revised in
`evolzen.economy.manuals`; consumed as a fast, cheap memory tier in `evolzen.recognition`,
sitting above the frozen `evolzen.library` and the JEPA + wake-sleep recognition model.

Citations:
    - Model collapse & provenance floor: Shumailov et al. (Nature 2024, DOI: 10.1038/s41586-024-07566-y).
    - Inspectable manual transfer: Agno (2026, agno2026manual).
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from evolzen.schemas.provenance import (
    GROUND_TRUTH_CATEGORIES,
    ProvenanceCategory,
    ProvenanceRecord,
)


class ProvenanceSource(StrEnum):
    """Legacy origin categories for knowledge artifacts enforcing the real-data floor.

    .. deprecated::
        Use :class:`evolzen.schemas.provenance.ProvenanceCategory` instead.
    """

    HUMAN_EXTERNAL = "human_external"
    HUMAN_DEMONSTRATION = "human_demonstration"
    SIMULATOR_TRACE = "simulator_trace"
    MODEL_GENERATED = "model_generated"


class ManualEntryStatus(StrEnum):
    HYPOTHESIS = "hypothesis"
    CONFIRMED = "confirmed"
    FALSIFIED = "falsified"


class ManualEntry(BaseModel):
    """One belief within a manual — a mechanic, a hazard, or a hypothesis."""

    text: str
    status: ManualEntryStatus = ManualEntryStatus.HYPOTHESIS
    written_by: str
    written_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revised_from: str | None = Field(
        default=None, description="Previous entry text this one revises, if it revises one."
    )
    evidence_ids: tuple[str, ...] = Field(
        default=(), description="IDs of transition or world events supporting/falsifying this belief."
    )
    category: ProvenanceCategory = ProvenanceCategory.MODEL_GENERATED
    provenance: ProvenanceRecord | None = Field(
        default=None, description="Source provenance record used to enforce the real-data floor."
    )

    @model_validator(mode="before")
    @classmethod
    def _sync_category_from_provenance(cls, data: Any) -> Any:
        if isinstance(data, dict):
            prov = data.get("provenance")
            if prov is not None and "category" not in data:
                if isinstance(prov, ProvenanceRecord):
                    data["category"] = prov.category
                elif isinstance(prov, dict) and "category" in prov:
                    data["category"] = prov["category"]
        return data

    @property
    def is_ground_truth(self) -> bool:
        """Return True if this entry represents ground-truth / real data."""
        if self.provenance is not None:
            return self.provenance.is_ground_truth
        return self.category in GROUND_TRUTH_CATEGORIES


class Manual(BaseModel):
    """A situation-scoped, actively-revised collection of manual entries."""

    situation_key: str = Field(description="Identifies which situation/environment this manual covers.")
    entries: list[ManualEntry] = Field(default_factory=list)

    def add_entry(self, entry: ManualEntry) -> None:
        self.entries.append(entry)

    def active_beliefs(self) -> list[ManualEntry]:
        """Entries not yet falsified — what an agent reading this manual should currently believe."""
        return [e for e in self.entries if e.status != ManualEntryStatus.FALSIFIED]

    def get_entry(self, index: int) -> ManualEntry:
        """Retrieve entry by 0-based index."""
        if not 0 <= index < len(self.entries):
            raise IndexError(f"Manual entry index {index} out of range [0, {len(self.entries) - 1}]")
        return self.entries[index]

    def falsify_entry(self, index: int, evidence_id: str | None = None) -> ManualEntry:
        """Mark an entry as FALSIFIED with optional empirical evidence."""
        old = self.get_entry(index)
        ev = (*old.evidence_ids, evidence_id) if evidence_id else old.evidence_ids
        updated = old.model_copy(update={"status": ManualEntryStatus.FALSIFIED, "evidence_ids": ev})
        self.entries[index] = updated
        return updated

    def revise_entry(
        self,
        index: int,
        new_text: str,
        written_by: str,
        evidence_id: str | None = None,
        provenance: ProvenanceRecord | None = None,
        category: ProvenanceCategory | None = None,
    ) -> ManualEntry:
        """Falsify the old entry and append an active revised entry pointing to the old one."""
        self.falsify_entry(index, evidence_id=evidence_id)
        old_text = self.entries[index].text
        ev = (evidence_id,) if evidence_id else ()
        cat = category if category is not None else (
            provenance.category if provenance is not None else ProvenanceCategory.MODEL_GENERATED
        )
        revised = ManualEntry(
            text=new_text,
            status=ManualEntryStatus.HYPOTHESIS,
            written_by=written_by,
            revised_from=old_text,
            evidence_ids=ev,
            category=cat,
            provenance=provenance,
        )
        self.add_entry(revised)
        return revised

    def confirm_entry(self, index: int, evidence_id: str | None = None) -> ManualEntry:
        """Promote an entry from HYPOTHESIS to CONFIRMED."""
        old = self.get_entry(index)
        ev = (*old.evidence_ids, evidence_id) if evidence_id else old.evidence_ids
        updated = old.model_copy(update={"status": ManualEntryStatus.CONFIRMED, "evidence_ids": ev})
        self.entries[index] = updated
        return updated

    def real_data_fraction(self) -> float:
        """Calculate the proportion of entries sourced from non-model-generated material.

        Returns:
            Fraction in [0.0, 1.0]. Returns 1.0 if manual has no entries.
        """
        if not self.entries:
            return 1.0
        real_count = sum(1 for e in self.entries if e.is_ground_truth)
        return float(real_count / len(self.entries))


__all__ = [
    "Manual",
    "ManualEntry",
    "ManualEntryStatus",
    "ProvenanceCategory",
    "ProvenanceRecord",
    "ProvenanceSource",
]
