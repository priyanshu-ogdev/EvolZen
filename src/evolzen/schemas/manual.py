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

from pydantic import BaseModel, Field


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


class Manual(BaseModel):
    """A situation-scoped, actively-revised collection of manual entries."""

    situation_key: str = Field(description="Identifies which situation/environment this manual covers.")
    entries: list[ManualEntry] = Field(default_factory=list)

    def add_entry(self, entry: ManualEntry) -> None:
        self.entries.append(entry)

    def active_beliefs(self) -> list[ManualEntry]:
        """Entries not yet falsified — what an agent reading this manual should currently believe."""
        return [e for e in self.entries if e.status != ManualEntryStatus.FALSIFIED]
