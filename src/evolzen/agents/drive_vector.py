"""Evolvable drive-vector agents (Phase 1.2).

Each agent pairs a small quantized local LLM with an evolvable `DriveVector`
(`evolzen.schemas.drive_vector`). Motivational diversity is evolved on the vector itself —
literal LoRA weight crossover is deliberately never used (see the module-level note in
evolzen.schemas.drive_vector for why). Action generation is delegated to an
`evolzen.agents.inference.InferenceBackend` so the agent itself doesn't hard-code a specific
model-serving stack.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evolzen.agents.inference import InferenceBackend
from evolzen.schemas.drive_vector import AgentLineage, DriveVector
from evolzen.schemas.transition import Action


@dataclass
class Agent:
    """One agent in the population."""

    agent_id: str
    base_model_id: str
    drive_vector: DriveVector
    lineage: AgentLineage
    inference_backend: InferenceBackend

    def act(self, observation: dict[str, Any]) -> Action:
        """Produce a schema-valid action given an observation, via the configured backend."""
        return self.inference_backend.generate_action(observation, self.drive_vector)
