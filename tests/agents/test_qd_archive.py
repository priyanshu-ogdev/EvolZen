from evolzen.agents.qd_archive import QDArchiveEntry, QualityDiversityArchive
from evolzen.schemas.drive_vector import DriveVector


def test_archive_keeps_higher_fitness_in_same_cell() -> None:
    archive = QualityDiversityArchive(cell_resolution=0.5)
    dv = DriveVector(resource_seeking=0.1)
    low = QDArchiveEntry("a1", dv, behavioral_descriptor=(0.2, 0.2), fitness=1.0)
    high = QDArchiveEntry("a2", dv, behavioral_descriptor=(0.25, 0.2), fitness=5.0)

    assert archive.consider(low) is True
    assert archive.consider(high) is True  # same cell, higher fitness replaces
    assert archive.coverage() == 1
    assert archive.entries()[0].agent_id == "a2"


def test_archive_tracks_coverage_across_distinct_cells() -> None:
    archive = QualityDiversityArchive(cell_resolution=0.5)
    dv = DriveVector()
    archive.consider(QDArchiveEntry("a1", dv, (0.0, 0.0), fitness=1.0))
    archive.consider(QDArchiveEntry("a2", dv, (5.0, 5.0), fitness=1.0))
    assert archive.coverage() == 2
