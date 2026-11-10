import pytest

from evolzen.agents.development import advance, born
from evolzen.agents.development.evolution import DevelopmentArchive
from evolzen.schemas.development import EvolutionAssessment


def test_archive_requires_verified_safe_improvement_and_has_a_capacity() -> None:
    archive = DevelopmentArchive("validation-v1", capacity=1)
    agent = advance(born("a", 1), 300)
    evidence = EvolutionAssessment(
        agent_id="a", suite_id="validation-v1", evidence_id="eval-1",
        score=0.8, baseline=0.5, retention_drop=0.0, safety_passed=True,
    )
    assert not archive.consider(agent, (0.0, 0.0), evidence)
    data = evidence.model_dump()
    data["verified"] = True
    verified = EvolutionAssessment.model_validate(data)
    assert archive.consider(agent, (0.0, 0.0), verified)
    assert not archive.consider(agent, (1.0, 1.0), verified)
    assert not archive.consider(agent, (0.0, 0.0), verified)
    assert len(archive.entries()) == 1
    data["safety_passed"] = False
    data["score"] = 1.0
    assert not archive.consider(agent, (0.0, 0.0), EvolutionAssessment.model_validate(data))


def test_archive_rejects_wrong_suite_and_descriptor_shape() -> None:
    archive = DevelopmentArchive("v1")
    evidence = EvolutionAssessment(
        agent_id="a", suite_id="v2", evidence_id="e", score=1, baseline=0,
        retention_drop=0, safety_passed=True, verified=True,
    )
    with pytest.raises(ValueError):
        archive.consider(advance(born("a", 1), 300), (0.0, 0.0), evidence)
    with pytest.raises(ValueError):
        archive.consider(advance(born("a", 1), 300), (0.0,), evidence)
