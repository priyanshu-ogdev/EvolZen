"""Quality-Diversity archives for agent-population selection (Phase 1.2).

Replaces plain fitness-based selection, which the diversity-collapse literature identifies as
a driver of premature convergence in multi-agent populations. Implements:
1. `QualityDiversityArchive`: Grid-based MAP-Elites (arXiv:2406.03731) keyed on behavioral descriptors;
2. `CVTArchive`: Centroidal Voronoi Tessellations MAP-Elites (Vassiliades et al., IEEE TEVC 2018,
   DOI:10.1109/TEVC.2017.2735550) scaling to high-dimensional behavioral spaces.

Behavioral descriptors measure phenotypic behavior (e.g., risk-tolerance, cooperativeness,
specialization, exploration rate), separating diversity maintenance from direct fitness.

Design authority: docs/phases/1.2-agents.md, ADR 0006, ADR 0008.
All archive selection dynamics remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import BirthGenome


@dataclass
class QDArchiveEntry:
    """Entry stored in a Quality-Diversity archive cell."""

    agent_id: str
    profile: AgentProfile
    behavioral_descriptor: tuple[float, ...]
    fitness: float
    metadata: dict[str, Any] = field(default_factory=dict)


class QualityDiversityArchive:
    """Grid-based MAP-Elites archive over agent behavioral descriptors."""

    def __init__(self, cell_resolution: float = 0.1) -> None:
        if cell_resolution <= 0.0 or not math.isfinite(cell_resolution):
            raise ValueError(f"cell_resolution must be positive and finite: {cell_resolution}")
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
        """Return all occupied archive entries."""
        return list(self._cells.values())

    def get(self, descriptor: tuple[float, ...]) -> QDArchiveEntry | None:
        """Retrieve the occupant of the cell corresponding to `descriptor`."""
        return self._cells.get(self._cell_key(descriptor))


class CVTArchive:
    """Centroidal Voronoi Tessellation (CVT) MAP-Elites archive for high-dimensional descriptors.

    Uses fixed centroid niches in descriptor space to prevent exponential cell explosion
    (Vassiliades et al., 2018).
    """

    def __init__(
        self,
        centroids: tuple[tuple[float, ...], ...],
    ) -> None:
        if not centroids:
            raise ValueError("CVTArchive requires at least one centroid")
        self._dimension = len(centroids[0])
        if any(len(c) != self._dimension for c in centroids):
            raise ValueError("All centroids must share the same dimensionality")
        self._centroids = centroids
        self._cells: dict[int, QDArchiveEntry] = {}

    @classmethod
    def uniform_hypercube(
        cls,
        num_centroids: int,
        dimensions: int = 5,
        *,
        seed: int = 42,
    ) -> CVTArchive:
        """Generate deterministic pseudo-random centroid niches in [0, 1]^d."""
        import random

        rng = random.Random(seed)
        generated: list[tuple[float, ...]] = []
        for _ in range(num_centroids):
            point = tuple(round(rng.uniform(0.0, 1.0), 4) for _ in range(dimensions))
            generated.append(point)
        return cls(tuple(generated))

    def _nearest_centroid_index(self, descriptor: tuple[float, ...]) -> int:
        if len(descriptor) != self._dimension:
            raise ValueError(
                f"Descriptor dimension {len(descriptor)} != centroid dimension {self._dimension}"
            )
        best_idx = 0
        min_dist = float("inf")
        for idx, centroid in enumerate(self._centroids):
            dist = sum((a - b) ** 2 for a, b in zip(descriptor, centroid, strict=True))
            if dist < min_dist:
                min_dist = dist
                best_idx = idx
        return best_idx

    def consider(self, entry: QDArchiveEntry) -> bool:
        """Insert `entry` into its nearest centroid Voronoi cell if fitness exceeds incumbent."""
        idx = self._nearest_centroid_index(entry.behavioral_descriptor)
        current = self._cells.get(idx)
        if current is None or entry.fitness > current.fitness:
            self._cells[idx] = entry
            return True
        return False

    def coverage(self) -> int:
        """Number of populated Voronoi cells."""
        return len(self._cells)

    def total_niches(self) -> int:
        """Total number of centroid niches in the tessellation."""
        return len(self._centroids)

    def entries(self) -> list[QDArchiveEntry]:
        """Return all occupied entries."""
        return list(self._cells.values())


def compute_behavioral_descriptor(
    genome: BirthGenome,
    profile: AgentProfile,
    dimension: int = 5,
) -> tuple[float, ...]:
    """Compute normalized [0.0, 1.0]^d behavioral descriptor from agent genome and social profile.

    Measures phenotypic behavior across orthogonal dimensions (risk-tolerance, status-drive,
    social-cooperativeness, norm-adherence, and resource accumulation momentum).
    """
    if dimension < 1:
        raise ValueError("dimension must be at least 1")
    # Coord 0: Greed/Risk bias (normalized to [0, 1])
    d0 = max(0.0, min(1.0, round((genome.equations[1].bias + 1.0) / 2.0, 4)))
    # Coord 1: Pride/Status momentum
    d1 = max(0.0, min(1.0, round(genome.equations[0].momentum, 4)))
    # Coord 2: Lust/Social affinity context sensitivity
    d2 = max(0.0, min(1.0, round(sum(abs(c) for c in genome.equations[2].context) / 8.0, 4)))
    # Coord 3: Institutional norm cooperativeness
    d3 = max(0.0, min(1.0, round(min(1.0, len(profile.adopted_norms) * 0.25 + len(profile.institutional_affiliations) * 0.25), 4)))
    # Coord 4: Gluttony/Resource accumulation momentum
    d4 = max(0.0, min(1.0, round(genome.equations[4].momentum, 4)))
    coords = [d0, d1, d2, d3, d4]
    while len(coords) < dimension:
        coords.append(0.5)
    return tuple(coords[:dimension])
