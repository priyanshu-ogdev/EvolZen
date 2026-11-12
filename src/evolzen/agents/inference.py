"""Structured-decoding LLM inference backends for agent action generation (Phase 1.2).

Every agent action must be a schema-valid `evolzen.schemas.transition.Action` — that's what
makes the Phase 1.1 environment verifiable and `evolzen.exploration.verifier` meaningful.
Rather than parsing free-text model output and hoping it matches the schema, this module uses
`outlines` to constrain generation so the model can only produce valid Action JSON.

Two backends satisfy the same protocol: `TransformersBackend` (CPU-friendly default) and
`VLLMBackend` (throughput-optimized for a live population on GPU hardware; requires the `gpu`
extra). Callers depend on `InferenceBackend`, not either concrete class, so switching
backends is a config change, not a code change.

Design authority: docs/phases/1.2-agents.md, ADR 0006, ADR 0008.
Citations:
- Willard & Louf (outlines, arXiv:2307.09702) for efficient guided generation with regular
  expressions and context-free grammars;
- Park et al. (Generative Agents, arXiv:2304.03442) for agent reflection and social planning.

All neural inference mechanisms remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from evolzen.environment.adapter import action_from_candidate
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate, Signal
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType


class InferenceBackend(Protocol):
    """Protocol satisfied by any backend turning profile, motives, and context into an Action."""

    def generate_action(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> Action:
        """Generate a schema-valid Action, constrained by the agent's profile and motives."""
        ...


class TransformersBackend:
    """Default, CPU-friendly backend using `transformers` + `outlines` constrained generation."""

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-0.5B-Instruct",
        *,
        device: str = "cpu",
        offline_fallback: bool = True,
        load_weights: bool = False,
    ) -> None:
        self._model_id = model_id
        self._device = device
        self._offline_fallback = offline_fallback
        self._load_weights = load_weights
        self._generator: Any = None

    def _init_generator(self) -> None:
        if self._generator is not None or not self._load_weights:
            return
        try:
            import outlines
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(self._model_id)
            model = AutoModelForCausalLM.from_pretrained(
                self._model_id,
                torch_dtype=torch.float32,
                device_map=self._device,
            )
            outlines_model = outlines.models.Transformers(model, tokenizer)  # type: ignore[arg-type]
            generate_mod = getattr(outlines, "generate", None)
            if generate_mod is not None:
                self._generator = generate_mod.json(outlines_model, Action)
        except Exception as exc:
            if not self._offline_fallback:
                raise RuntimeError(
                    f"Failed to initialize outlines generator for {self._model_id}: {exc}"
                ) from exc
            self._generator = None

    def build_prompt(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> str:
        """Format the agent prompt incorporating social identity, motives, and context."""
        legal_ids = [c.action_id for c in candidates if c.permitted]
        payload = {
            "agent_id": profile.agent_id,
            "roles": profile.roles,
            "norms": profile.adopted_norms,
            "institutions": profile.institutional_affiliations,
            "motive_weights": list(motive_weights),
            "signal": list(signal),
            "legal_candidates": legal_ids,
            "context": world_context,
        }
        return (
            f"You are agent {profile.agent_id}. Given your state and motives, "
            f"choose a valid Action from the legal candidates:\n"
            f"{json.dumps(payload, separators=(',', ':'))}\n"
        )

    def generate_action(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> Action:
        """Generate a schema-valid Action constrained by outlines, with deterministic safe fallback."""
        self._init_generator()
        if self._generator is not None:
            prompt = self.build_prompt(profile, signal, candidates, motive_weights, world_context)
            try:
                result: Action = self._generator(prompt)
                if isinstance(result, Action) and any(result.action_type == at.value for at in ActionType):
                    return result
            except Exception:
                pass  # Fall through to deterministic safe fallback

        # Deterministic fallback: choose the highest-priority permitted candidate
        permitted = [c for c in candidates if c.permitted]
        chosen = permitted[0] if permitted else (candidates[0] if candidates else None)
        if chosen is None:
            return Action(agent_id=profile.agent_id, action_type=ActionType.WAIT)
        return action_from_candidate(chosen.action_id, profile.agent_id)


class VLLMBackend:
    """Throughput-optimized backend for a live agent population. Requires the `gpu` extra."""

    def __init__(self, model_id: str, *, tensor_parallel_size: int = 1) -> None:
        try:
            import vllm  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise ImportError("VLLMBackend requires the 'gpu' extra: uv sync --extra gpu") from exc
        self._model_id = model_id
        self._tensor_parallel_size = tensor_parallel_size

    def generate_action(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> Action:
        raise NotImplementedError(
            "VLLM live population generation requires GPU hardware and live server initialization. "
            "See docs/phases/1.2-agents.md."
        )
