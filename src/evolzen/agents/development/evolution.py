"""Phase 1.2 bounded phenotype archive inspired by MAP-Elites (arXiv:1504.04909).

This untested controller stores validated developmental snapshots; it does not
run evaluations, grant birth permissions, or edit policy code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from evolzen.agents.development.lifecycle import stage_at
from evolzen.schemas.development import BrainSnapshot, EvolutionAssessment, LifeStage


@dataclass(frozen=True)
class DevelopmentElite:
    """Frozen snapshot and external evidence for one measured behavior cell."""

    snapshot: BrainSnapshot
    descriptor: tuple[float, ...]
    assessment: EvolutionAssessment


class DevelopmentArchive:
    """Bounded archive, separate from the legacy five-drive archive.

    Descriptor dimensions and validation suite are fixed for the entire archive.
    A replacement never destroys the caller's original snapshot or run artifacts.
    """

    def __init__(
        self, suite_id: str, *, dimensions: int = 2, bins: int = 5,
        capacity: int = 25, min_gain: float = 0.0, max_retention_drop: float = 0.05,
    ) -> None:
        if not suite_id or len(suite_id) > 128:
            raise ValueError("A bounded validation-suite identifier is required")
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 1
               for v in (dimensions, bins, capacity)):
            raise ValueError("Dimensions, bins and capacity must be positive integers")
        if dimensions > 8 or bins > 100 or capacity > 10000:
            raise ValueError("Archive budget exceeded")
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in (min_gain, max_retention_drop)):
            raise ValueError("Validation thresholds must lie in [0, 1]")
        self.suite_id = suite_id
        self.dimensions = dimensions
        self.bins = bins
        self.capacity = capacity
        self.min_gain = min_gain
        self.max_retention_drop = max_retention_drop
        self._cells: dict[tuple[int, ...], DevelopmentElite] = {}

    def consider(
        self, snapshot: BrainSnapshot, descriptor: tuple[float, ...],
        assessment: EvolutionAssessment,
    ) -> bool:
        """Accept externally evaluated improvements without exceeding capacity."""
        if len(descriptor) != self.dimensions or any(
            not math.isfinite(v) or not 0 <= v <= 1 for v in descriptor
        ):
            raise ValueError("Descriptor must match normalized archive dimensions")
        if assessment.agent_id != snapshot.birth.agent_id or assessment.suite_id != self.suite_id:
            raise ValueError("Assessment identity or validation suite mismatch")
        if snapshot.pending is not None or stage_at(snapshot, snapshot.tick) not in (
            LifeStage.ADULT, LifeStage.ELDER,
        ):
            raise ValueError("Archive candidates must be mature with settled actions")
        if (not assessment.verified or not assessment.safety_passed
                or assessment.retention_drop > self.max_retention_drop
                or assessment.score - assessment.baseline <= self.min_gain):
            return False
        cell = tuple(min(self.bins - 1, int(v * self.bins)) for v in descriptor)
        old = self._cells.get(cell)
        if old is None and len(self._cells) >= self.capacity:
            return False
        if old is not None and assessment.score <= old.assessment.score:
            return False
        self._cells[cell] = DevelopmentElite(snapshot, descriptor, assessment)
        return True

    def entries(self) -> tuple[DevelopmentElite, ...]:
        """Return elites in deterministic cell order for a host reproduction policy."""
        return tuple(self._cells[key] for key in sorted(self._cells))
