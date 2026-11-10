import pytest

from evolzen.agents.development import advance, born, stage_at
from evolzen.schemas.development import DevelopmentConfig, LifeStage


@pytest.mark.parametrize("tick,stage", [
    (0, LifeStage.CHILD), (99, LifeStage.CHILD), (100, LifeStage.ADOLESCENT),
    (300, LifeStage.ADULT), (1000, LifeStage.ELDER), (1500, LifeStage.DEAD),
])
def test_stage_boundaries(tick: int, stage: LifeStage) -> None:
    assert stage_at(born("a", 1), tick) == stage


def test_child_has_lineage_but_no_learned_experience() -> None:
    parent = advance(born("parent", 1), 300)
    child = born("child", 2, 300, parents=(parent,))
    assert stage_at(child, 300) == LifeStage.CHILD
    assert child.birth.parents == ("parent",)
    assert child.birth.generation == 1
    assert child.knowledge == ()
    assert child.recent == ()
    assert child.lessons == ()


def test_rejects_immature_dead_or_duplicate_parents() -> None:
    parent = born("p", 1)
    with pytest.raises(ValueError):
        born("c", 2, 100, parents=(parent,))
    with pytest.raises(ValueError):
        born("c", 2, 1500, parents=(parent,))
    with pytest.raises(ValueError):
        born("c", 2, 300, parents=(parent, parent))


def test_age_does_not_grant_skills_and_clock_cannot_reverse() -> None:
    adult = advance(born("a", 1), 300)
    assert adult.knowledge == ()
    with pytest.raises(ValueError):
        advance(adult, 299)
    with pytest.raises(ValueError):
        DevelopmentConfig(adulthood=100)
