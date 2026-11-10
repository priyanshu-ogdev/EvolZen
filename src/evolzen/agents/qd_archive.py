"""Quality-Diversity archive for agent-population selection (Phase 1.2).

Replaces plain fitness-based selection, which the diversity-collapse literature identifies as
a driver of premature convergence in multi-agent LLM populations. A MAP-Elites-style archive
(arXiv:2406.03731) keyed on behavioral descriptors maintains a grid of diverse, locally-optimal
behaviors instead of letting the whole population converge on one peak.
"""
from __future__ import annotations

from dataclasses import dataclass

from evolzen.schemas.drive_vector import DriveVector


@dataclass
class QDArchiveEntry:
    agent_id: str
    drive_vector: DriveVector
    behavioral_descriptor: tuple[float, ...]
    fitness: float


class QualityDiversityArchive:
    """A MAP-Elites-style archive over agent behavioral descriptors.

    `behavioral_descriptor` is a low-dimensional summary of *how* an agent behaves (e.g.
    risk-tolerance x cooperativeness), distinct from `drive_vector`, which is the underlying
    cause of that behavior. The archive keeps at most one entry per descriptor-space cell,
    replacing an entry only when a new agent both lands in the same cell and has higher
    fitness — this is what "coverage" means in the Phase 1.2 success metric.
    """

    def __init__(self, cell_resolution: float = 0.1) -> None:
        self._cell_resolution = cell_resolution
        self._cells: dict[tuple[int, ...], QDArchiveEntry] = {}

    def _cell_key(self, descriptor: tuple[float, ...]) -> tuple[int, ...]:
        return tuple(round(d / self._cell_resolution) for d in descriptor)

    def consider(self, entry: QDArchiveEntry) -> bool:
        """Insert `entry` if its cell is empty or it beats the current occupant.

        Returns True if the archive changed.
        """
        key = self._cell_key(entry.behavioral_descriptor)
        current = self._cells.get(key)
        if current is None or entry.fitness > current.fitness:
            self._cells[key] = entry
            return True
        return False

    def coverage(self) -> int:
        """Number of occupied cells — the diversity-collapse signal to track."""
        return len(self._cells)

    def entries(self) -> list[QDArchiveEntry]:
        return list(self._cells.values())
