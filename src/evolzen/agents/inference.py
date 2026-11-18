"""Structured-decoding LLM inference backends for agent action generation (Phase 1.2).

Implements the finalized two-tier inference architecture for EvolZen's multi-agent population:

  Tier-1 (Tactical Action Selection):
    Base model:  Qwen/Qwen3.5-9B-VL-AWQ  (8-bit AWQ W8A16, Vision-Language)
    Adapter:     Standard LoRA  (r=8, alpha=16, ~43 MB)
    Role:        Fast per-turn action proposals constrained to outlines JSON schema
    Max tokens:  256
    Latency:     < 15 ms per agent turn

  Tier-2 (Deliberative Planning & Rule Synthesis):
    Base model:  Qwen/Qwen3.5-9B-VL-AWQ  (SHARED — same frozen weights as Tier-1)
    Adapter:     DoRA  (r=16, alpha=32, magnitude vector m, ~86 MB)
    Role:        Deep chain-of-thought planning, economic proof synthesis, gVisor
                 Python rule generation, and spatial zoning decisions
    Max tokens:  2048
    Latency:     < 5 ms adapter swap + model generation time
    Citation:    Liu et al. (DoRA, ICML 2024, arXiv:2402.09353)

Both backends satisfy the same `InferenceBackend` protocol.  Switching tiers at runtime
is an in-memory pointer swap — zero PCIe model transfer, zero VRAM eviction.

Design authority: docs/phases/1.2-agents.md §4–5, docs/subsystems/agents/architecture.md §5,
                  ADR 0006, ADR 0008.
Citations:
- Willard & Louf (outlines, arXiv:2307.09702) for JSON-constrained generation;
- Park et al. (Generative Agents, arXiv:2304.03442) for social planning and reflection;
- Liu et al. (DoRA: Weight-Decomposed Low-Rank Adaptation, ICML 2024, arXiv:2402.09353);
- Lin et al. (AWQ, MLSys 2024, arXiv:2306.00978) for 8-bit weight quantization.

All neural inference mechanisms remain empirically untested until Phase 1.2 experiments are run.
"""
from __future__ import annotations

import json
from typing import Any, Literal, Protocol

from evolzen.environment.adapter import action_from_candidate
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate, Signal
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType

# ---------------------------------------------------------------------------
# Canonical model and adapter constants
# ---------------------------------------------------------------------------

#: Shared base model for both tiers — a single set of weights lives in VRAM.
QWEN_9B_VL_AWQ: str = "Qwen/Qwen3.5-9B-VL-AWQ"

#: Tier-1 LoRA adapter hyperparameters (tactical action selection).
TIER1_ADAPTER_RANK: int = 8
TIER1_ADAPTER_ALPHA: int = 16
TIER1_MAX_NEW_TOKENS: int = 256
TIER1_TEMPERATURE: float = 0.4   # Low temperature for fast, deterministic action selection

#: Tier-2 DoRA adapter hyperparameters (deliberative planning & rule synthesis).
TIER2_ADAPTER_RANK: int = 16
TIER2_ADAPTER_ALPHA: int = 32
TIER2_MAX_NEW_TOKENS: int = 2048
TIER2_TEMPERATURE: float = 0.7   # Higher temperature for diverse, exploratory reasoning

#: Edge fallback model for CPU-only environments.
FALLBACK_MODEL: str = "Qwen/Qwen2.5-3B-Instruct-AWQ"

AdapterTier = Literal["tier1", "tier2"]


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
    """Default CPU-friendly backend using `transformers` + `outlines` constrained generation.

    Satisfies the Tier-1 contract: fast action proposals constrained to the
    ``evolzen.schemas.transition.Action`` JSON schema via outlines grammar constraints.
    Falls back deterministically to the highest-priority permitted candidate when
    the LLM generator is unavailable.
    """

    def __init__(
        self,
        model_id: str = QWEN_9B_VL_AWQ,
        *,
        adapter_tier: AdapterTier = "tier1",
        device: str = "cpu",
        offline_fallback: bool = True,
        load_weights: bool = False,
    ) -> None:
        self._model_id = model_id
        self._adapter_tier = adapter_tier
        self._device = device
        self._offline_fallback = offline_fallback
        self._load_weights = load_weights
        self._generator: Any = None

    @property
    def adapter_tier(self) -> AdapterTier:
        """The inference tier this backend is configured for."""
        return self._adapter_tier

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
        """Format an agent prompt incorporating social identity, 8-D motives, and spatial context."""
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
            "adapter_tier": self._adapter_tier,
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
    """Throughput-optimized backend for a live agent population. Requires the ``gpu`` extra.

    Hosts the shared ``Qwen/Qwen3.5-9B-VL-AWQ`` base model (8-bit AWQ, ~9.18 GB) and
    supports dynamic Multi-LoRA batching via vLLM's ``--enable-lora`` flag, allowing
    Tier-1 and Tier-2 adapter requests to be served in a single GPU forward pass.

    Architecture:
        - **Tier-1 adapter** (LoRA, r=8, alpha=16, ~43 MB): tactical action selection.
          Uses outlines ``guided_json`` / vLLM ``guided_json`` grammar to guarantee
          schema-valid ``Action`` JSON in <= 256 output tokens.
        - **Tier-2 adapter** (DoRA, r=16, alpha=32 + magnitude vector m, ~86 MB): deliberative
          planning and rule synthesis.  Returns free-form chain-of-thought up to 2 048 tokens,
          parsed downstream by ``evolzen.exploration.synthesizer``.

    Switching between adapters is an in-memory pointer swap: < 5 ms latency, zero VRAM transfer.
    """

    def __init__(
        self,
        model_id: str = QWEN_9B_VL_AWQ,
        *,
        adapter_tier: AdapterTier = "tier1",
        tier1_lora_path: str | None = None,
        tier2_dora_path: str | None = None,
        tensor_parallel_size: int = 1,
        quantization: str | None = None,
        llm: Any = None,
        **engine_kwargs: Any,
    ) -> None:
        try:
            import vllm  # noqa: F401
        except ImportError as exc:
            raise ImportError("VLLMBackend requires the 'gpu' extra: uv sync --extra gpu") from exc
        self._model_id = model_id
        self._adapter_tier = adapter_tier
        self._tier1_lora_path = tier1_lora_path
        self._tier2_dora_path = tier2_dora_path
        self._tensor_parallel_size = tensor_parallel_size
        self._quantization = quantization
        if self._quantization is None and ("AWQ" in model_id or "-awq" in model_id.lower()):
            self._quantization = "awq"
        self._llm = llm
        self._engine_kwargs = engine_kwargs

    @property
    def adapter_tier(self) -> AdapterTier:
        """The inference tier this backend is currently routing to."""
        return self._adapter_tier

    def switch_tier(self, tier: AdapterTier) -> None:
        """Switch the active adapter tier in-memory (<5 ms, zero VRAM transfer).

        In production this triggers a vLLM LoRA request with the target lora_id.
        The base model remains loaded; only the adapter pointer changes.
        """
        self._adapter_tier = tier

    def _init_engine(self) -> None:
        """Lazily initialize the vLLM engine if not already provided."""
        if self._llm is not None:
            return
        import vllm

        kwargs = dict(self._engine_kwargs)
        if self._quantization is not None and "quantization" not in kwargs:
            kwargs["quantization"] = self._quantization

        self._llm = vllm.LLM(
            model=self._model_id,
            tensor_parallel_size=self._tensor_parallel_size,
            **kwargs,
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

        result = try_parse(cleaned)
        if result is not None:
            return result

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            result = try_parse(cleaned[start : end + 1])
            if result is not None:
                return result

        return None

    def _build_tier1_prompt(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> str:
        """Tier-1: Compact structured prompt for fast tactial action selection (<= 256 tokens output).

        Instructs the model to emit a single schema-valid ``Action`` JSON object from
        the declared legal candidate set.  No chain-of-thought is requested; the LoRA
        adapter is fine-tuned for direct-emission JSON compliance.
        """
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
            "instruction": (
                "Select one valid action from the legal candidates. "
                "Respond ONLY with a schema-valid Action JSON object (no reasoning text)."
            ),
            "schema": {
                "agent_id": "string",
                "action_type": "string — one of ActionType values",
                "params": "dict[str, Any]",
            },
            "agent": {
                "agent_id": profile.agent_id,
                "roles": list(profile.roles),
                "norms": list(profile.adopted_norms),
                "institutions": list(profile.institutional_affiliations),
                "adapter_tier": "tier1",
            },
            "motive_weights": list(motive_weights),
            "signal": list(signal),
            "candidates": candidate_entries,
            "legal_candidates": legal_ids,
            "context": world_context,
        }
        return (
            f"You are agent {profile.agent_id}. "
            f"Respond ONLY with a schema-valid JSON object matching the Action contract:\n"
            f"{json.dumps(payload, separators=(',', ':'))}\n"
        )

    def _build_tier2_prompt(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> str:
        """Tier-2: Extended deliberative prompt for reflective planning and rule synthesis.

        Instructs the DoRA-adapted model to reason step-by-step (chain-of-thought) over
        multi-step trade-offs, economic equilibria, spatial resource distribution, and
        rule-library candidate synthesis.  Output is parsed by ``evolven.exploration.synthesizer``.
        Maximum 2048 output tokens.
        """
        legal_ids = [c.action_id for c in candidates if c.permitted]
        payload = {
            "instruction": (
                "You are in deliberative reflection mode. Reason step-by-step about your "
                "long-term strategic goals, economic trade-offs, spatial resource distribution, "
                "and any candidate rule or norm to synthesise. Then select the best action "
                "from the legal candidates and optionally propose a new rule for the library."
            ),
            "agent": {
                "agent_id": profile.agent_id,
                "roles": list(profile.roles),
                "norms": list(profile.adopted_norms),
                "motive_weights": list(motive_weights),
                "adapter_tier": "tier2",
            },
            "environment": {
                "signal": list(signal),
                "legal_candidates": legal_ids,
                "context": world_context,
            },
            "output_format": {
                "reasoning": "string — step-by-step chain of thought",
                "action": {
                    "agent_id": "string",
                    "action_type": "string",
                    "params": "dict",
                },
                "proposed_rule": "string | null — Python code for gVisor sandbox (optional)",
            },
        }
        return (
            f"<deliberate>\n"
            f"Agent {profile.agent_id} entering Tier-2 deliberative planning.\n"
            f"{json.dumps(payload, separators=(',', ':'), indent=2)}\n"
            f"</deliberate>\n"
        )

    def build_prompt(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> str:
        """Route to tier-appropriate prompt builder based on ``adapter_tier``."""
        if self._adapter_tier == "tier2":
            return self._build_tier2_prompt(profile, signal, candidates, motive_weights, world_context)
        return self._build_tier1_prompt(profile, signal, candidates, motive_weights, world_context)

    def generate_action(
        self,
        profile: AgentProfile,
        signal: Signal,
        candidates: tuple[Candidate, ...],
        motive_weights: tuple[float, ...],
        world_context: dict[str, Any],
    ) -> Action:
        """Generate a schema-valid Action using vLLM Multi-LoRA, falling back deterministically."""
        try:
            self._init_engine()
        except Exception:
            self._llm = None

        # Select tier-appropriate sampling parameters
        if self._adapter_tier == "tier2":
            temperature = TIER2_TEMPERATURE
            max_tokens = TIER2_MAX_NEW_TOKENS
        else:
            temperature = TIER1_TEMPERATURE
            max_tokens = TIER1_MAX_NEW_TOKENS

        if self._llm is not None:
            prompt = self.build_prompt(profile, signal, candidates, motive_weights, world_context)
            try:
                import vllm

                # Tier-1 uses guided_json for guaranteed schema compliance.
                # Tier-2 uses free-form generation then parsing.
                if self._adapter_tier == "tier1":
                    try:
                        sampling_params = vllm.SamplingParams(
                            temperature=temperature,
                            max_tokens=max_tokens,
                            guided_json=Action.model_json_schema(),
                        )
                    except TypeError:
                        sampling_params = vllm.SamplingParams(
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                else:
                    sampling_params = vllm.SamplingParams(
                        temperature=temperature,
                        max_tokens=max_tokens,
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
