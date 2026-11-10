"""Phase 1.2 developmental-agent contracts.

The eight-drive ontology and equations are untested EvolZen design choices,
not a psychological model. Cultural transfer is motivated by Cook et al.
(arXiv:2406.00392); these records do not imply replication of that work.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Unit = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
SignedUnit = Annotated[float, Field(ge=-1.0, le=1.0, allow_inf_nan=False)]
Signal = Annotated[tuple[SignedUnit, ...], Field(min_length=8, max_length=8)]
Ratios = Annotated[tuple[Unit, ...], Field(min_length=8, max_length=8)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
Tick = Annotated[int, Field(ge=0, strict=True)]
ZERO: tuple[float, ...] = (0.0,) * 8


class Motive(StrEnum):
    """Stable coordinate order; lust is nonsexual attraction/affiliation here."""

    PRIDE = "pride"
    GREED = "greed"
    LUST = "lust"
    ENVY = "envy"
    GLUTTONY = "gluttony"
    WRATH = "wrath"
    SLOTH = "sloth"
    NULL = "null"


class LifeStage(StrEnum):
    """Simulation stages, not biological ages."""

    CHILD = "child"
    ADOLESCENT = "adolescent"
    ADULT = "adult"
    ELDER = "elder"
    DEAD = "dead"


class Record(BaseModel):
    """Immutable, finite, closed-schema records with validated defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)


class DriveEquation(Record):
    """One bounded row of a birth-time equation; never executable text."""

    bias: SignedUnit
    context: Signal
    age_weight: SignedUnit
    momentum: Unit


class BirthGenome(Record):
    """Immutable temperament; coefficients, not neural weights, are inherited."""

    version: Literal["eight-drive-v1"] = "eight-drive-v1"
    seed: Tick
    equations: Annotated[tuple[DriveEquation, ...], Field(min_length=8, max_length=8)]
    temperature: Annotated[float, Field(ge=0.1, le=5.0, allow_inf_nan=False)] = 1.0


class DevelopmentConfig(Record):
    """Illustrative tick budgets; none is a measured human development law."""

    adolescence: Tick = 100
    adulthood: Tick = 300
    elderhood: Tick = 1000
    lifespan: Tick = 1500
    learning_rate: Annotated[float, Field(gt=0.0, le=1.0, allow_inf_nan=False)] = 0.2
    memory_limit: Annotated[int, Field(ge=1, le=10000, strict=True)] = 128
    knowledge_limit: Annotated[int, Field(ge=1, le=10000, strict=True)] = 128
    lesson_limit: Annotated[int, Field(ge=1, le=1000, strict=True)] = 32
    max_candidates: Annotated[int, Field(ge=1, le=256, strict=True)] = 32
    advice_weight: Annotated[float, Field(ge=0.0, le=0.25, allow_inf_nan=False)] = 0.1

    @model_validator(mode="after")
    def ordered_stages(self) -> Self:
        """Reject overlapping stages and nonpositive childhood duration."""
        if not 0 < self.adolescence < self.adulthood < self.elderhood < self.lifespan:
            raise ValueError("Stage thresholds must strictly increase from zero")
        return self


class BirthRecord(Record):
    """Lineage, temperament, and world-clock origin, separate from teaching."""

    agent_id: Identifier
    born_at: Tick
    genome: BirthGenome
    parents: Annotated[tuple[Identifier, ...], Field(max_length=2)] = ()
    generation: Tick = 0

    @model_validator(mode="after")
    def valid_parents(self) -> Self:
        """Reject duplicate parents, self-parenting, and inconsistent generations."""
        if self.agent_id in self.parents or len(set(self.parents)) != len(self.parents):
            raise ValueError("Parents must be distinct and cannot include the child")
        if bool(self.parents) != (self.generation > 0):
            raise ValueError("Only non-founders have parents and positive generations")
        return self


class Candidate(Record):
    """Domain-supplied safe action proposal; not executable code or a permission."""

    action_id: Identifier
    context_key: Identifier
    skill_key: Identifier
    predicted: Signal = ZERO
    cost: Unit = 0.0
    minimum_age: Tick = 0
    permitted: bool = True


class Decision(Record):
    """Compact numerical decision trace, not private chain-of-thought."""

    agent_id: Identifier
    sequence: Annotated[int, Field(ge=1, strict=True)]
    tick: Tick
    candidate: Candidate
    activation: Signal
    ratios: Ratios
    score: Annotated[float, Field(allow_inf_nan=False)]


class Outcome(Record):
    """Trusted-host feedback. A verified flag alone is not a security boundary."""

    agent_id: Identifier
    sequence: Annotated[int, Field(ge=1, strict=True)]
    tick: Tick
    action_id: Identifier
    evidence_id: Identifier
    rewards: Signal
    verified: bool = False


class SkillEstimate(Record):
    """Context-specific empirical outcome estimate, not a competence certificate."""

    context_key: Identifier
    skill_key: Identifier
    values: Signal
    samples: Annotated[int, Field(ge=1, strict=True)]
    evidence_id: Identifier


class Lesson(Record):
    """Advice from a living parent; receipt never certifies mastery."""

    teacher_id: Identifier
    learner_id: Identifier
    taught_at: Tick
    estimate: SkillEstimate


class EvolutionAssessment(Record):
    """Host-owned validation evidence, never a candidate's self-awarded score."""

    agent_id: Identifier
    suite_id: Identifier
    evidence_id: Identifier
    score: Unit
    baseline: Unit
    retention_drop: Unit
    safety_passed: bool
    verified: bool = False


class BrainSnapshot(Record):
    """Serializable in-memory state; persistent event storage remains an integration task."""

    birth: BirthRecord
    config: DevelopmentConfig = DevelopmentConfig()
    tick: Tick
    sequence: Tick = 0
    activation: Signal = ZERO
    knowledge: tuple[SkillEstimate, ...] = ()
    lessons: tuple[Lesson, ...] = ()
    recent: tuple[Outcome, ...] = ()
    pending: Decision | None = None

    @model_validator(mode="after")
    def consistent_snapshot(self) -> Self:
        """Validate restoration boundaries; authenticity still belongs to the host."""
        if self.tick < self.birth.born_at:
            raise ValueError("Clock predates birth")
        if len(self.knowledge) > self.config.knowledge_limit:
            raise ValueError("Knowledge budget exceeded")
        if len(self.lessons) > self.config.lesson_limit or len(self.recent) > self.config.memory_limit:
            raise ValueError("Memory budget exceeded")
        keys = [(item.context_key, item.skill_key) for item in self.knowledge]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate knowledge keys")
        if self.pending is not None and (
            self.pending.agent_id != self.birth.agent_id
            or self.pending.sequence != self.sequence
            or self.pending.tick != self.tick
            or self.pending.activation != self.activation
        ):
            raise ValueError("Pending decision does not match snapshot")
        for item in self.recent:
            if (item.agent_id != self.birth.agent_id or not item.verified
                    or item.tick > self.tick or item.sequence > self.sequence):
                raise ValueError("Invalid outcome history")
        for lesson in self.lessons:
            if (lesson.learner_id != self.birth.agent_id
                    or lesson.teacher_id not in self.birth.parents
                    or not self.birth.born_at <= lesson.taught_at <= self.tick):
                raise ValueError("Invalid lesson history")
        return self
