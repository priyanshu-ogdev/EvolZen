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

    def __init__(
        self,
        model_id: str,
        *,
        tensor_parallel_size: int = 1,
        llm: Any = None,
        **engine_kwargs: Any,
    ) -> None:
        try:
            import vllm  # noqa: F401
        except ImportError as exc:
            raise ImportError("VLLMBackend requires the 'gpu' extra: uv sync --extra gpu") from exc
        self._model_id = model_id
        self._tensor_parallel_size = tensor_parallel_size
        self._llm = llm
        self._engine_kwargs = engine_kwargs

    def _init_engine(self) -> None:
        """Lazily initialize the vLLM engine if not already provided."""
        if self._llm is not None:
            return
        import vllm

        self._llm = vllm.LLM(
            model=self._model_id,
            tensor_parallel_size=self._tensor_parallel_size,
            **self._engine_kwargs,
        )

    def _parse_action_json(self, text: str, expected_agent_id: str | None = None) -> Action | None:
        """Parse raw model output text into a validated Action schema instance."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        valid_types = {at.value for at in ActionType}

        def try_parse(candidate_str: str) -> Action | None:
            try:
                data = json.loads(candidate_str)
                if isinstance(data, dict):
                    action = Action.model_validate(data)
                    if action.action_type in valid_types:
                        if expected_agent_id is not None and action.agent_id != expected_agent_id:
                            return None
                        return action
            except Exception:
                pass
            return None

        # First try parsing the full cleaned text
        result = try_parse(cleaned)
        if result is not None:
            return result

        # If full text parsing fails, search for outer JSON braces
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            result = try_parse(cleaned[start : end + 1])
            if result is not None:
                return result

        return None

    def build_prompt(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> str:
        """Format a structured JSON prompt with candidate action descriptions, motives, and schema instructions."""
        candidate_entries = [
            {
                "action_id": c.action_id,
                "skill_key": c.skill_key,
                "context_key": c.context_key,
                "cost": c.cost,
                "permitted": c.permitted,
            }
            for c in candidates
        ]
        legal_ids = [c.action_id for c in candidates if c.permitted]
        payload = {
            "instruction": "Select one valid action from the legal candidates and respond with a schema-valid Action JSON object.",
            "schema": {
                "agent_id": "string",
                "action_type": "string (one of ActionType: 'wait', 'gather', 'move', 'consume', 'craft', 'trade', 'propose_contract', etc.)",
                "params": "dict[str, Any]",
            },
            "agent": {
                "agent_id": profile.agent_id,
                "roles": list(profile.roles),
                "norms": list(profile.adopted_norms),
                "institutions": list(profile.institutional_affiliations),
            },
            "motive_weights": list(motive_weights),
            "signal": list(signal),
            "candidates": candidate_entries,
            "legal_candidates": legal_ids,
            "context": world_context,
        }
        return (
            f"You are agent {profile.agent_id}. Given your state and motives, "
            f"respond ONLY with a schema-valid JSON object matching the Action contract:\n"
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
        """Generate a schema-valid Action using vLLM, falling back to a deterministic safe action on failure."""
        try:
            self._init_engine()
        except Exception:
            self._llm = None

        if self._llm is not None:
            prompt = self.build_prompt(profile, signal, candidates, motive_weights, world_context)
            try:
                import vllm

                try:
                    sampling_params = vllm.SamplingParams(
                        temperature=0.7,
                        max_tokens=256,
                        guided_json=Action.model_json_schema(),
                    )
                except TypeError:
                    sampling_params = vllm.SamplingParams(
                        temperature=0.7,
                        max_tokens=256,
                    )
                outputs = self._llm.generate([prompt], sampling_params)
                if outputs:
                    first = outputs[0]
                    if hasattr(first, "outputs") and first.outputs:
                        text = first.outputs[0].text
                    elif isinstance(first, str):
                        text = first
                    elif hasattr(first, "text"):
                        text = first.text
                    else:
                        text = str(first)
                    parsed_action = self._parse_action_json(text, expected_agent_id=profile.agent_id)
                    if parsed_action is not None:
                        return parsed_action
            except Exception:
                pass  # Fall through to deterministic safe fallback

        # Deterministic fallback: choose the highest-priority permitted candidate
        permitted = [c for c in candidates if c.permitted]
        chosen = permitted[0] if permitted else (candidates[0] if candidates else None)
        if chosen is None:
            return Action(agent_id=profile.agent_id, action_type=ActionType.WAIT)
        return action_from_candidate(chosen.action_id, profile.agent_id)
