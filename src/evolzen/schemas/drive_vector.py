"""The evolvable drive-vector schema (Phase 1.2).

Motivational diversity across the `evolzen.agents` population is evolved as this
low-dimensional coefficient vector over a fixed reward-shaping basis — deliberately never as
crossover of raw neural network weights (independently trained networks don't share an aligned
parameter space; naive weight crossover reliably breaks both parents' behavior). Selection over
these vectors runs through a Quality-Diversity archive (`evolzen.agents.qd_archive`), not plain
fitness, to guard against the population diversity collapse documented in a 2026 ACL Findings
study (see docs/dependency-stack.md).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DriveVector(BaseModel):
    """A fixed-length set of reward-shaping coefficients for one agent.

    Field values are unconstrained coefficients (positive values increase the weight of that
    motivation in the agent's reward shaping; negative values suppress it), not probabilities —
    they need not sum to 1.
    """

    resource_seeking: float = 0.0
    status: float = 0.0
    effort_avoidance: float = 0.0
    aggression: float = 0.0
    comparison_driven_utility: float = 0.0

    def as_vector(self) -> list[float]:
        """Return the coefficients in a fixed order, for use as a QD-archive behavioral key."""
        return [
            self.resource_seeking,
            self.status,
            self.effort_avoidance,
            self.aggression,
            self.comparison_driven_utility,
        ]


class AgentLineage(BaseModel):
    """Tracks an agent's weight- and data-inheritance separately (Phase 1.2).

    The two inheritance tracks are kept structurally distinct on purpose — conflating "which
    checkpoint did this agent's weights come from" with "which curated text did this agent
    train on" was a source of confusion in earlier design iterations.
    """

    agent_id: str
    parent_weight_checkpoint: str | None = Field(
        default=None, description="Checkpoint this agent's weights were fine-tuned from, if any."
    )
    parent_data_sources: list[str] = Field(
        default_factory=list, description="Curated text sources this agent trained on."
    )
    generation: int = Field(default=0, ge=0)
