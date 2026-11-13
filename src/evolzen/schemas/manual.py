"""The falsifiable manual schema (Phase 1.3 / Phase 2.3).

Modeled on a 2026 result (Agno) showing this mechanism requires no gradient step, is directly
inspectable, and produced a measured capability gain when a cheap model consumed a frontier
model's manual rather than re-deriving the same knowledge. Written and revised in
`evolzen.economy.manuals`; consumed as a fast, cheap memory tier in `evolzen.recognition`,
sitting above the frozen `evolzen.library` and the JEPA + wake-sleep recognition model.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProvenanceSource(StrEnum):
    """Origin categories for knowledge artifacts enforcing the real-data floor.

    Citation:
        Shumailov et al. (Nature, 2024, DOI:10.1038/s41586-024-07566-y).
    """

    HUMAN_EXTERNAL = "human_external"
    HUMAN_DEMONSTRATION = "human_demonstration"
    SIMULATOR_TRACE = "simulator_trace"
    MODEL_GENERATED = "model_generated"


class ProvenanceRecord(BaseModel):
    """Immutable provenance metadata tracking the source origin and verification of knowledge."""

    provenance_id: str
    source_type: ProvenanceSource
    origin: str = Field(
        description="Origin identifier: external dataset URL, human user ID, simulator run ID, or model ID."
    )
    hash_sha256: str = Field(
        description="Cryptographic SHA-256 digest of the source material or demonstration."
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    provenance: ProvenanceRecord | None = Field(
        default=None, description="Source provenance record used to enforce the real-data floor."
    )


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
    ) -> ManualEntry:
        """Falsify the old entry and append an active revised entry pointing to the old one."""
        self.falsify_entry(index, evidence_id=evidence_id)
        old_text = self.entries[index].text
        ev = (evidence_id,) if evidence_id else ()
        revised = ManualEntry(
            text=new_text,
            status=ManualEntryStatus.HYPOTHESIS,
            written_by=written_by,
            revised_from=old_text,
            evidence_ids=ev,
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
