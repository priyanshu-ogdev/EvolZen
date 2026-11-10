import math

import pytest

from evolzen.agents.development.motivation import drive_step, inherit_genome, sample_genome
from evolzen.schemas.development import ZERO, BirthGenome, DriveEquation


def test_seed_reproducibility_and_serialization() -> None:
    genome = sample_genome(42)
    assert genome == sample_genome(42)
    assert genome != sample_genome(43)
    assert BirthGenome.model_validate_json(genome.model_dump_json()) == genome


def test_bounded_dynamics_and_normalization() -> None:
    genome = sample_genome(3)
    activation, ratios = drive_step(genome, (1.0,) * 8, ZERO, 0.5)
    assert all(math.isfinite(value) and -1 <= value <= 1 for value in activation)
    assert all(0 <= value <= 1 for value in ratios)
    assert sum(ratios) == pytest.approx(1.0)
    assert drive_step(genome, (-1.0,) * 8, ZERO, 0.5)[0] != activation


def test_age_is_an_explicit_equation_input() -> None:
    row = DriveEquation(bias=0, context=ZERO, age_weight=1, momentum=0)
    genome = BirthGenome(seed=0, equations=(row,) * 8)
    assert drive_step(genome, ZERO, ZERO, 0)[0] == ZERO
    assert all(value > 0 for value in drive_step(genome, ZERO, ZERO, 1)[0])


@pytest.mark.parametrize("values", [(0.0,) * 7, (math.nan,) * 8, (math.inf,) * 8, (2.0,) * 8])
def test_rejects_invalid_context(values: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        drive_step(sample_genome(0), values, ZERO, 0)


def test_inheritance_is_bounded_and_does_not_mutate_parents() -> None:
    parent = sample_genome(7)
    original = parent.model_dump_json()
    assert inherit_genome((parent,), 8, mutation=0).equations == parent.equations
    child = inherit_genome((parent,), 8)
    assert child == inherit_genome((parent,), 8)
    assert child.equations != parent.equations
    assert parent.model_dump_json() == original
    with pytest.raises(ValueError):
        inherit_genome((parent,), 9, mutation=math.nan)


def test_invalid_seed_and_empty_parents() -> None:
    with pytest.raises(ValueError):
        sample_genome(-1)
    with pytest.raises(ValueError):
        inherit_genome((), 1)
