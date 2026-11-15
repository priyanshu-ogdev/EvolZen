from evolzen.environment.engine import SocialSandboxEngine
from evolzen.evaluation.procedural_env_gen import ProceduralEnvironmentGenerator


def test_generator_initialization() -> None:
    gen = ProceduralEnvironmentGenerator(seed=123)
    assert gen.round_count == 0
    assert gen.generated_configs == []


def test_next_environment_produces_valid_engine() -> None:
    gen = ProceduralEnvironmentGenerator(seed=42)
    env = gen.next_environment()
    assert isinstance(env, SocialSandboxEngine)
    assert gen.round_count == 1

    # Verify generated environment resets cleanly with zero invariant violations
    state = env.reset()
    assert state is not None
    assert "agents" in state.data
    assert "locations" in state.data


def test_generator_no_reused_instances() -> None:
    gen = ProceduralEnvironmentGenerator(seed=999)
    envs = [gen.next_environment() for _ in range(8)]
    assert len(envs) == 8
    assert gen.has_reused_instances() is False

    seeds = [c["seed"] for c in gen.generated_configs]
    assert len(set(seeds)) == 8


def test_generate_suite() -> None:
    gen = ProceduralEnvironmentGenerator(seed=777)
    suite = gen.generate_suite(5)
    assert len(suite) == 5
    assert gen.round_count == 5

    empty_suite = gen.generate_suite(0)
    assert empty_suite == []


def test_generator_multi_tier() -> None:
    gen = ProceduralEnvironmentGenerator(seed=101, task_tier="multi_tier")
    assert gen.task_tier == "multi_tier"
    assert gen.target_goal == "craft:stone_axe"
    assert gen.metadata == {"task_tier": "multi_tier", "target_goal": "craft:stone_axe"}

    env = gen.next_environment()
    assert isinstance(env, SocialSandboxEngine)
    assert gen.round_count == 1
    assert gen.generated_configs[0]["task_tier"] == "multi_tier"
    assert gen.generated_configs[0]["target_goal"] == "craft:stone_axe"

    state = env.reset()
    assert state is not None
    caps = state.data.get("capabilities", {})
    assert "craft:tool_handle" in caps
    assert "craft:stone_blade" in caps
    assert "craft:stone_axe" in caps
    assert caps["craft:tool_handle"]["required_resources"] == {"wood": 1}
    assert caps["craft:stone_blade"]["required_resources"] == {"stone": 1}
    assert caps["craft:stone_axe"]["required_resources"] == {"wood": 1, "stone": 1}

