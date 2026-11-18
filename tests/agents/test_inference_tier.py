"""Unit tests for Tier-1 / Tier-2 adapter architecture (Phase 1.2).

Covers the tier-aware constants, prompt builders, tier switching,
and TransformersBackend adapter_tier parameter that were introduced
when finalising the Qwen 3.5 9B VL AWQ unified base architecture.
"""
from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from evolzen.agents.inference import (
    QWEN_9B_VL_AWQ,
    TIER1_ADAPTER_ALPHA,
    TIER1_ADAPTER_RANK,
    TIER1_MAX_NEW_TOKENS,
    TIER1_TEMPERATURE,
    TIER2_ADAPTER_ALPHA,
    TIER2_ADAPTER_RANK,
    TIER2_MAX_NEW_TOKENS,
    TIER2_TEMPERATURE,
    TransformersBackend,
    VLLMBackend,
)
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_vllm_module() -> types.ModuleType:  # type: ignore[return]
    """Minimal vllm mock so VLLMBackend can be constructed without GPU."""
    vllm = types.ModuleType("vllm")

    class _FakeLLM:
        def __init__(self, model: str, **kwargs: Any) -> None:
            self.model = model
            self.kwargs = kwargs

    class _FakeSamplingParams:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    vllm.LLM = _FakeLLM  # type: ignore[attr-defined]
    vllm.SamplingParams = _FakeSamplingParams  # type: ignore[attr-defined]
    sys.modules["vllm"] = vllm
    yield vllm
    del sys.modules["vllm"]


def _make_profile() -> AgentProfile:
    return AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-0",
        roles=("scout",),
        adopted_norms=("conserve",),
        institutional_affiliations=(),
    )


def _make_signal() -> tuple[float, ...]:
    """Signal is a plain 8-float tuple (motive deltas), not a dataclass."""
    return (0.1, -0.2, 0.3, 0.0, -0.5, 0.4, 0.0, 0.1)


def _make_candidates() -> tuple[Candidate, ...]:
    return (
        Candidate(
            action_id="wait",
            context_key="world:loc-0",
            skill_key="wait:v1",
            predicted=(0.0,) * 8,
            cost=0.0,
            minimum_age=0,
            permitted=True,
        ),
    )


def _make_world_context() -> dict[str, Any]:
    return {"tick": 1, "population": 5}


# ---------------------------------------------------------------------------
# Architecture constants
# ---------------------------------------------------------------------------


def test_canonical_model_id() -> None:
    """QWEN_9B_VL_AWQ must match the declared canonical identifier."""
    assert QWEN_9B_VL_AWQ == "Qwen/Qwen3.5-9B-VL-AWQ"


def test_tier1_constants() -> None:
    """Tier-1 LoRA constants match the finalised architecture specification."""
    assert TIER1_ADAPTER_RANK == 8
    assert TIER1_ADAPTER_ALPHA == 16
    assert TIER1_MAX_NEW_TOKENS == 256
    assert pytest.approx(0.4) == TIER1_TEMPERATURE


def test_tier2_constants() -> None:
    """Tier-2 DoRA constants match the finalised architecture specification."""
    assert TIER2_ADAPTER_RANK == 16
    assert TIER2_ADAPTER_ALPHA == 32
    assert TIER2_MAX_NEW_TOKENS == 2048
    assert pytest.approx(0.7) == TIER2_TEMPERATURE


# ---------------------------------------------------------------------------
# TransformersBackend — adapter_tier
# ---------------------------------------------------------------------------


def test_transformers_backend_default_tier() -> None:
    """TransformersBackend defaults to tier1."""
    backend = TransformersBackend()
    assert backend.adapter_tier == "tier1"


def test_transformers_backend_explicit_tier2() -> None:
    """TransformersBackend accepts adapter_tier='tier2'."""
    backend = TransformersBackend(adapter_tier="tier2")
    assert backend.adapter_tier == "tier2"


def test_transformers_backend_uses_qwen_vl_default() -> None:
    """Default model ID is the canonical Qwen 3.5 9B VL AWQ identifier."""
    backend = TransformersBackend()
    assert backend._model_id == QWEN_9B_VL_AWQ


# ---------------------------------------------------------------------------
# VLLMBackend — adapter_tier & tier switching
# ---------------------------------------------------------------------------


def test_vllm_backend_default_tier(mock_vllm_module: types.ModuleType) -> None:
    """VLLMBackend defaults to tier1 on construction."""
    backend = VLLMBackend()
    assert backend.adapter_tier == "tier1"


def test_vllm_backend_explicit_tier2(mock_vllm_module: types.ModuleType) -> None:
    """VLLMBackend accepts adapter_tier='tier2' on construction."""
    backend = VLLMBackend(adapter_tier="tier2")
    assert backend.adapter_tier == "tier2"


def test_vllm_backend_switch_tier(mock_vllm_module: types.ModuleType) -> None:
    """switch_tier() correctly updates _adapter_tier."""
    backend = VLLMBackend()
    assert backend.adapter_tier == "tier1"
    backend.switch_tier("tier2")
    assert backend.adapter_tier == "tier2"
    backend.switch_tier("tier1")
    assert backend.adapter_tier == "tier1"


def test_vllm_backend_uses_qwen_vl_default(mock_vllm_module: types.ModuleType) -> None:
    """Default VLLMBackend model is Qwen 3.5 9B VL AWQ."""
    backend = VLLMBackend()
    assert backend._model_id == QWEN_9B_VL_AWQ


# ---------------------------------------------------------------------------
# VLLMBackend — prompt builders (using real structured arguments)
# ---------------------------------------------------------------------------


def test_tier1_prompt_has_no_deliberate_tag(mock_vllm_module: types.ModuleType) -> None:
    """Tier-1 compact prompt must NOT contain the <deliberate> tag."""
    backend = VLLMBackend()
    prompt = backend._build_tier1_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "<deliberate>" not in prompt


def test_tier1_prompt_references_json_format(mock_vllm_module: types.ModuleType) -> None:
    """Tier-1 prompt must reference constrained JSON output."""
    backend = VLLMBackend()
    prompt = backend._build_tier1_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "json" in prompt.lower() or "output_format" in prompt.lower()


def test_tier2_prompt_has_deliberate_tag(mock_vllm_module: types.ModuleType) -> None:
    """Tier-2 deliberative prompt must contain the <deliberate> reasoning tag."""
    backend = VLLMBackend(adapter_tier="tier2")
    prompt = backend._build_tier2_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "<deliberate>" in prompt


def test_tier2_prompt_references_output_format(mock_vllm_module: types.ModuleType) -> None:
    """Tier-2 prompt must include an 'output_format' key hint."""
    backend = VLLMBackend(adapter_tier="tier2")
    prompt = backend._build_tier2_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "output_format" in prompt


def test_build_prompt_routes_to_tier1(mock_vllm_module: types.ModuleType) -> None:
    """build_prompt() with tier1 uses the compact prompt builder."""
    backend = VLLMBackend(adapter_tier="tier1")
    prompt = backend.build_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "<deliberate>" not in prompt


def test_build_prompt_routes_to_tier2(mock_vllm_module: types.ModuleType) -> None:
    """build_prompt() with tier2 uses the deliberative prompt builder."""
    backend = VLLMBackend(adapter_tier="tier2")
    prompt = backend.build_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "<deliberate>" in prompt


def test_switch_tier_changes_prompt_routing(mock_vllm_module: types.ModuleType) -> None:
    """After switch_tier, build_prompt routes to the new tier's builder."""
    backend = VLLMBackend(adapter_tier="tier1")
    tier1_prompt = backend.build_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    backend.switch_tier("tier2")
    tier2_prompt = backend.build_prompt(
        _make_profile(), _make_signal(), _make_candidates(), (0.5,) * 8, _make_world_context()
    )
    assert "<deliberate>" not in tier1_prompt
    assert "<deliberate>" in tier2_prompt
