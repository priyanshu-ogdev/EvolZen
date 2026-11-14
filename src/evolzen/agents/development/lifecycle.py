"""Phase 1.2 simulation-age and birth operations; untested developmental policy.

Implements child/adolescent/adult/elder/dead life staging on a monotonic shared
world clock, and zero-mastery infant birth operations.

Citations:
- Cook et al. (Artificial Generational Intelligence, arXiv:2406.00392, 2024) for
  developmental lifetime boundaries, zero birth-time mastery copying, and separating
  cultural transmission from genetic inheritance.

No biological interpretation, age-dependent neural rank, or competence grant
is implied. Cultural inheritance is handled separately from birth.
All lifecycle dynamics remain empirically untested until Phase 1.2 population experiments are run.
"""

from __future__ import annotations

from evolzen.agents.development.motivation import inherit_genome, sample_genome
from evolzen.schemas.development import (
    BirthRecord,
    BrainSnapshot,
    DevelopmentConfig,
    LifeStage,
)


def stage_at(snapshot: BrainSnapshot, tick: int) -> LifeStage:
    """Return a stage on a monotonic shared world clock, including terminal death."""
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < snapshot.tick:
        raise ValueError("Tick must be an integer at or after the current clock")
    age = tick - snapshot.birth.born_at
    config = snapshot.config
    if age >= config.lifespan:
        return LifeStage.DEAD
    if age >= config.elderhood:
        return LifeStage.ELDER
    if age >= config.adulthood:
        return LifeStage.ADULT
    if age >= config.adolescence:
        return LifeStage.ADOLESCENT
    return LifeStage.CHILD


def born(
    agent_id: str,
    seed: int,
    tick: int = 0,
    *,
    config: DevelopmentConfig | None = None,
    parents: tuple[BrainSnapshot, ...] = (),
    mutation: float = 0.05,
) -> BrainSnapshot:
    """Create an empty-minded child; adult living parents transmit temperament only.

    The population owner must additionally enforce global ID uniqueness, resources,
    birth rate and population ceilings. This function allocates no models or workers.
    """
    if len(parents) > 2:
        raise ValueError("At most two parents are supported")
    for parent in parents:
        if parent.pending is not None:
            raise ValueError("Parents must settle pending actions before reproduction")
        if stage_at(parent, tick) not in (LifeStage.ADULT, LifeStage.ELDER):
            raise ValueError("Parents must be alive and mature at birth")
    genome = (
        inherit_genome(tuple(p.birth.genome for p in parents), seed, mutation)
        if parents else sample_genome(seed)
    )
    birth = BirthRecord(
        agent_id=agent_id, born_at=tick, genome=genome,
        parents=tuple(p.birth.agent_id for p in parents),
        generation=1 + max(p.birth.generation for p in parents) if parents else 0,
    )
    return BrainSnapshot(birth=birth, tick=tick, config=config or DevelopmentConfig())
