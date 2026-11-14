"""Phase 1.2 bounded eight-drive dynamics; an untested EvolZen hypothesis.

Implements homeostatic internal drive dynamics over eight coordinates (pride, greed,
lust, envy, gluttony, wrath, sloth, Null), producing bounded activations and normalized
priority ratios for multi-objective action evaluation.

Citations:
- Keramati & Gutkin (eLife 2014, DOI:10.7554/eLife.04811) for homeostatic drive-reduction
  utility modulating multi-objective priorities;
- Merrick (IEEE TAMD/TCDS 2010, DOI:10.1109/TAMD.2010.2051435) for comparative intrinsic
  value-system benchmarking in autonomous developmental agents.

Random coefficients are data, never source code. No eval/exec, global RNG,
network, model loading, or environment actions occur in this module.
All drive dynamics remain empirically untested until Phase 1.2 population experiments are run.
"""

from __future__ import annotations

import math
import random

from evolzen.schemas.development import BirthGenome, DriveEquation


def validate_signal(values: tuple[float, ...]) -> None:
    """Reject wrong dimensions, nonfinite values and out-of-range coordinates."""
    if len(values) != 8 or any(not math.isfinite(v) or not -1.0 <= v <= 1.0 for v in values):
        raise ValueError("Expected eight finite values in [-1, 1]")


def sample_genome(seed: int) -> BirthGenome:
    """Create a reproducible founder; persist coefficients as well as seed."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("Seed must be a nonnegative integer")
    rng = random.Random(seed)
    rows = tuple(
        DriveEquation(
            bias=rng.uniform(-0.5, 0.5),
            context=tuple(rng.uniform(-1.0, 1.0) for _ in range(8)),
            age_weight=rng.uniform(-0.5, 0.5),
            momentum=rng.uniform(0.0, 0.5),
        )
        for _ in range(8)
    )
    return BirthGenome(seed=seed, equations=rows)


def drive_step(
    genome: BirthGenome,
    context: tuple[float, ...],
    previous: tuple[float, ...],
    age_fraction: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return bounded activations and normalized ratios for one decision step."""
    validate_signal(context)
    validate_signal(previous)
    if not math.isfinite(age_fraction) or not 0.0 <= age_fraction <= 1.0:
        raise ValueError("Age fraction must be finite and in [0, 1]")
    activation = tuple(
        math.tanh(
            row.bias
            + sum(w * x for w, x in zip(row.context, context, strict=True)) / 8.0
            + row.age_weight * age_fraction
            + row.momentum * previous[index]
        )
        for index, row in enumerate(genome.equations)
    )
    maximum = max(activation)
    weights = tuple(math.exp((v - maximum) / genome.temperature) for v in activation)
    total = sum(weights)
    return activation, tuple(v / total for v in weights)


def inherit_genome(
    parents: tuple[BirthGenome, ...], seed: int, mutation: float = 0.05
) -> BirthGenome:
    """Mix aligned numeric coefficients, never neural weights or learned memories."""
    if not 1 <= len(parents) <= 2:
        raise ValueError("Inheritance requires one or two parent genomes")
    if not math.isfinite(mutation) or not 0.0 <= mutation <= 0.25:
        raise ValueError("Mutation must be in [0, 0.25]")
    # Reuse seed validation without consuming any shared/global RNG state.
    sample_genome(seed)
    rng = random.Random(seed)

    def mix(values: tuple[float, ...], lower: float = -1.0) -> float:
        return min(1.0, max(lower, sum(values) / len(values) + rng.uniform(-mutation, mutation)))

    rows = tuple(
        DriveEquation(
            bias=mix(tuple(p.equations[i].bias for p in parents)),
            context=tuple(mix(tuple(p.equations[i].context[j] for p in parents)) for j in range(8)),
            age_weight=mix(tuple(p.equations[i].age_weight for p in parents)),
            momentum=mix(tuple(p.equations[i].momentum for p in parents), 0.0),
        )
        for i in range(8)
    )
    return BirthGenome(
        seed=seed, equations=rows,
        temperature=sum(p.temperature for p in parents) / len(parents),
    )
