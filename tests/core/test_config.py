"""Phase 0 sanity tests: settings load with defaults, YAML overrides, and env-var overrides."""
from pathlib import Path

from evolzen.config import AgentsSettings, Device, EvolZenSettings, load_settings


def test_defaults() -> None:
    settings = EvolZenSettings()
    assert settings.agents.device == Device.CPU
    assert 10 <= settings.agents.population_size <= 30
    assert 0.0 <= settings.economy.real_data_floor <= 1.0
    assert settings.predictor.rehearsal_buffer_size > 0


def test_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("EVOLZEN_AGENTS__POPULATION_SIZE", "15")
    settings = EvolZenSettings()
    assert settings.agents.population_size == 15


def test_load_settings_missing_yaml_falls_back_to_defaults(tmp_path: Path) -> None:
    settings = load_settings(AgentsSettings, tmp_path / "does-not-exist.yaml")
    assert settings.population_size == 20


def test_load_settings_applies_yaml_overrides(tmp_path: Path) -> None:
    yaml_path = tmp_path / "agents.yaml"
    yaml_path.write_text("population_size: 12\n")
    settings = load_settings(AgentsSettings, yaml_path)
    assert settings.population_size == 12
