"""Tests for Quality-Diversity archives (Phase 1.2)."""
from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry, QualityDiversityArchive
from evolzen.schemas.agent_profile import AgentProfile


def _make_profile(agent_id: str) -> AgentProfile:
    return AgentProfile(agent_id=agent_id, lineage_id=f"lineage-{agent_id}")


def test_archive_keeps_higher_fitness_in_same_cell() -> None:
    archive = QualityDiversityArchive(cell_resolution=0.5)
    p1 = _make_profile("a1")
    p2 = _make_profile("a2")
    low = QDArchiveEntry("a1", p1, behavioral_descriptor=(0.2, 0.2), fitness=1.0)
    high = QDArchiveEntry("a2", p2, behavioral_descriptor=(0.25, 0.2), fitness=5.0)

    assert archive.consider(low) is True
    assert archive.consider(high) is True  # same cell, higher fitness replaces
    assert archive.coverage() == 1
    assert archive.entries()[0].agent_id == "a2"


def test_archive_tracks_coverage_across_distinct_cells() -> None:
    archive = QualityDiversityArchive(cell_resolution=0.5)
    p1 = _make_profile("a1")
    p2 = _make_profile("a2")
    archive.consider(QDArchiveEntry("a1", p1, (0.0, 0.0), fitness=1.0))
    archive.consider(QDArchiveEntry("a2", p2, (5.0, 5.0), fitness=1.0))
    assert archive.coverage() == 2


def test_cvt_archive_voronoi_tessellation() -> None:
    centroids = (
        (0.0, 0.0, 0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0, 1.0, 1.0),
        (0.5, 0.5, 0.5, 0.5, 0.5),
    )
    cvt = CVTArchive(centroids)
    assert cvt.total_niches() == 3
    assert cvt.coverage() == 0

    p1 = _make_profile("a1")
    p2 = _make_profile("a2")

    # Point close to centroid 0
    entry1 = QDArchiveEntry("a1", p1, (0.1, 0.05, 0.0, 0.1, 0.0), fitness=10.0)
    assert cvt.consider(entry1) is True
    assert cvt.coverage() == 1

    # Point close to centroid 1
    entry2 = QDArchiveEntry("a2", p2, (0.9, 0.95, 1.0, 0.85, 0.9), fitness=20.0)
    assert cvt.consider(entry2) is True
    assert cvt.coverage() == 2

    # Higher fitness point close to centroid 0 replaces entry1
    entry3 = QDArchiveEntry("a3", _make_profile("a3"), (0.05, 0.0, 0.0, 0.05, 0.0), fitness=30.0)
    assert cvt.consider(entry3) is True
    assert cvt.coverage() == 2
