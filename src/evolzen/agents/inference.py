"""Structured-decoding LLM inference backends for agent action generation (Phase 1.2).

Every agent action must be a schema-valid `evolzen.schemas.transition.Action` — that's what
makes the Phase 1.1 environment verifiable and `evolzen.exploration.verifier` meaningful.
Rather than parsing free-text model output and hoping it matches the schema, this module uses
`outlines` to *constrain* generation so the model can only produce valid Action JSON.

Two backends satisfy the same protocol: `TransformersBackend` (CPU-friendly default) and
`VLLMBackend` (throughput-optimized for a live population on the AGX Spark; requires the `gpu`
extra). Callers (`evolzen.agents.drive_vector.Agent.act`) depend on `InferenceBackend`, not
either concrete class, so switching backends is a config change, not a code change.
"""
from __future__ import annotations

from typing import Any, Protocol

from evolzen.schemas.drive_vector import DriveVector
from evolzen.schemas.transition import Action


class InferenceBackend(Protocol):
    """Protocol satisfied by any backend that turns (observation, drive_vector) into an Action."""

    def generate_action(self, observation: dict[str, Any], drive_vector: DriveVector) -> Action:
        """Generate a schema-valid Action, constrained by the agent's drive-vector-shaped prompt."""
        ...


class TransformersBackend:
    """Default, CPU-friendly backend using `transformers` + `outlines`.

    Phase 0 stub: model loading and the outlines-constrained generation call are left
    unimplemented pending the Phase 1.1 domain choice, since the exact Action schema's
    `action_type` / `params` shape (and therefore the outlines grammar passed to the
    constrained generator) depends on it.
    """

    def __init__(self, model_id: str, *, device: str = "cpu") -> None:
        self._model_id = model_id
        self._device = device

    def generate_action(self, observation: dict[str, Any], drive_vector: DriveVector) -> Action:
        raise NotImplementedError(
            "Implement once the Phase 1.1 domain's Action shape is finalized. "
            "See docs/phases/1.2-agents.md and docs/dependency-stack.md (outlines)."
        )


class VLLMBackend:
    """Throughput-optimized backend for a live agent population. Requires the `gpu` extra.

    Import of `vllm` is deferred to `__init__` so this module remains importable without the
    `gpu` extra installed.
    """

    def __init__(self, model_id: str, *, tensor_parallel_size: int = 1) -> None:
        try:
            import vllm  # noqa: F401
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise ImportError("VLLMBackend requires the 'gpu' extra: uv sync --extra gpu") from exc
        self._model_id = model_id
        self._tensor_parallel_size = tensor_parallel_size

    def generate_action(self, observation: dict[str, Any], drive_vector: DriveVector) -> Action:
        raise NotImplementedError(
            "Implement once the Phase 1.1 domain's Action shape is finalized. "
            "See docs/phases/1.2-agents.md."
        )
