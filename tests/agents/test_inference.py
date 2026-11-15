"""Unit tests for structured inference backends (Phase 1.2)."""
from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from evolzen.agents.inference import TransformersBackend, VLLMBackend
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate
from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType


def _make_sample_profile() -> AgentProfile:
    return AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-0",
        roles=("scout",),
        adopted_norms=("conserve",),
        institutional_affiliations=("guild-1",),
    )


def _make_sample_candidates() -> tuple[Candidate, ...]:
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
        Candidate(
            action_id="gather:food:1",
            context_key="world:loc-0",
            skill_key="gather:food:v1",
            predicted=(0.1,) * 8,
            cost=0.05,
            minimum_age=0,
            permitted=True,
        ),
    )


def test_transformers_backend_build_prompt_and_offline_fallback() -> None:
    backend = TransformersBackend(offline_fallback=True)
    profile = _make_sample_profile()
    signal = (0.1, -0.2, 0.3, 0.0, -0.5, 0.4, 0.0, 0.1)
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    prompt = backend.build_prompt(profile, signal, candidates, motive_weights, world_ctx)
    assert "agent-0" in prompt
    assert "wait" in prompt
    assert "gather:food:1" in prompt

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT


# --- VLLMBackend Test Doubles & Fixtures ------------------------------------


class MockCompletionOutput:
    """Mock for vLLM CompletionOutput."""

    def __init__(self, text: str) -> None:
        self.text = text


class MockRequestOutput:
    """Mock for vLLM RequestOutput."""

    def __init__(self, text: str) -> None:
        self.outputs = [MockCompletionOutput(text)]


class MockSamplingParams:
    """Mock for vLLM SamplingParams."""

    def __init__(self, temperature: float = 0.7, max_tokens: int = 256, **kwargs: Any) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs


class MockLLM:
    """Mock for vLLM LLM engine."""

    def __init__(self, model: str = "", tensor_parallel_size: int = 1, **kwargs: Any) -> None:
        self.model = model
        self.tensor_parallel_size = tensor_parallel_size
        self.kwargs = kwargs
        self.return_texts: list[str] = []
        self.should_raise: Exception | None = None
        self.recorded_prompts: list[list[str]] = []

    def generate(self, prompts: list[str], sampling_params: Any) -> list[MockRequestOutput]:
        if self.should_raise is not None:
            raise self.should_raise
        self.recorded_prompts.append(prompts)
        text = self.return_texts.pop(0) if self.return_texts else "{}"
        return [MockRequestOutput(text)]


@pytest.fixture
def mock_vllm_module(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Inject a mock vLLM module into sys.modules."""
    module = types.ModuleType("vllm")
    module.LLM = MockLLM  # type: ignore[attr-defined]
    module.SamplingParams = MockSamplingParams  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "vllm", module)
    return module


# --- VLLMBackend Unit Tests ------------------------------------------------


def test_vllm_backend_import_guard_raises_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "vllm", None)
    with pytest.raises(ImportError, match="VLLMBackend requires the 'gpu' extra"):
        VLLMBackend(model_id="Qwen/Qwen2.5-0.5B-Instruct")


def test_vllm_backend_build_prompt(mock_vllm_module: types.ModuleType) -> None:
    backend = VLLMBackend(model_id="test-model", llm=MockLLM())
    profile = _make_sample_profile()
    signal = (0.1, -0.2, 0.3, 0.0, -0.5, 0.4, 0.0, 0.1)
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    prompt = backend.build_prompt(profile, signal, candidates, motive_weights, world_ctx)
    assert "agent-0" in prompt
    assert "wait" in prompt
    assert "gather:food:1" in prompt
    assert "guild-1" in prompt
    assert "Action" in prompt


def test_vllm_backend_generate_action_success(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    valid_payload = {
        "agent_id": "agent-0",
        "action_type": "gather",
        "params": {"resource": "food", "amount": 1},
    }
    mock_llm.return_texts = [json.dumps(valid_payload)]
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert isinstance(action, Action)
    assert action.agent_id == "agent-0"
    assert action.action_type == "gather"
    assert action.params == {"resource": "food", "amount": 1}
    assert len(mock_llm.recorded_prompts) == 1


def test_vllm_backend_generate_action_fenced_markdown_json(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    payload = {
        "agent_id": "agent-0",
        "action_type": "move",
        "params": {"destination": "loc-1"},
    }
    mock_llm.return_texts = [f"```json\n{json.dumps(payload)}\n```"]
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == "move"
    assert action.params == {"destination": "loc-1"}


def test_vllm_backend_fallback_on_unparseable_text(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    mock_llm.return_texts = ["I think I will gather food because I'm hungry."]
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    # Highest-priority permitted candidate in _make_sample_candidates() is "wait"
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT


def test_vllm_backend_fallback_on_invalid_action_type(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    payload = {
        "agent_id": "agent-0",
        "action_type": "teleport_dimension",
        "params": {},
    }
    mock_llm.return_texts = [json.dumps(payload)]
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT


def test_vllm_backend_fallback_on_mismatched_agent_id(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    payload = {
        "agent_id": "different-agent",
        "action_type": "gather",
        "params": {"resource": "food", "amount": 1},
    }
    mock_llm.return_texts = [json.dumps(payload)]
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    candidates = _make_sample_candidates()
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT


def test_vllm_backend_fallback_on_engine_exception(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    mock_llm.should_raise = RuntimeError("CUDA out of memory in worker 0")
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    # Test fallback to gather when gather is the first permitted candidate
    candidates = (
        Candidate(
            action_id="gather:food:1",
            context_key="world:loc-0",
            skill_key="gather:food:v1",
            predicted=(0.1,) * 8,
            cost=0.05,
            minimum_age=0,
            permitted=True,
        ),
    )
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, candidates, motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.GATHER
    assert action.params == {"resource": "food", "amount": 1}


def test_vllm_backend_fallback_no_candidates(mock_vllm_module: types.ModuleType) -> None:
    mock_llm = MockLLM()
    mock_llm.should_raise = RuntimeError("GPU failure")
    backend = VLLMBackend(model_id="test-model", llm=mock_llm)

    profile = _make_sample_profile()
    signal = (0.0,) * 8
    motive_weights = (0.125,) * 8
    world_ctx = {"location_id": "loc-0"}

    action = backend.generate_action(profile, signal, (), motive_weights, world_ctx)
    assert action.agent_id == "agent-0"
    assert action.action_type == ActionType.WAIT


def test_vllm_backend_lazy_init_engine(mock_vllm_module: types.ModuleType) -> None:
    backend = VLLMBackend("test-model", tensor_parallel_size=2, max_model_len=2048)
    assert backend._llm is None

    backend._init_engine()
    assert isinstance(backend._llm, MockLLM)
    assert backend._llm.model == "test-model"
    assert backend._llm.tensor_parallel_size == 2
    assert backend._llm.kwargs["max_model_len"] == 2048

    # Second call should be a no-op
    first_instance = backend._llm
    backend._init_engine()
    assert backend._llm is first_instance
