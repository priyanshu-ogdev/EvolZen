"""Repo-wide configuration.

One `EvolZenSettings` root, composed of one nested settings group per subsystem that actually
needs configuration, loaded from:

1. CLI flags (highest precedence — set by `evolzen.cli`)
2. Environment variables, prefixed `EVOLZEN_` (e.g. ``EVOLZEN_AGENTS__POPULATION_SIZE=15``,
   using pydantic-settings' nested-delimiter convention)
3. The YAML files under ``configs/`` (e.g. ``configs/agents.yaml``)
4. The class defaults below

Layers 2-4 are handled by ``load_settings`` below; layer 1 is `evolzen.cli`'s job.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Device(StrEnum):
    """Where a subsystem's compute-heavy code should run.

    Maps loosely onto the project's three-device hardware topology (AGX Spark, DGX Spark,
    A6000) — see docs/ARCHITECTURE.md §6 — but is intentionally generic so the same code runs
    on a laptop for local development.
    """

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


class EnvironmentSettings(BaseModel):
    """Phase 1.1 — evolzen.environment."""

    device: Device = Device.CPU
    data_dir: Path = Path("data/environment")
    transition_log_path: Path = Path("data/environment/transitions.duckdb")


class AgentsSettings(BaseModel):
    """Phase 1.2 — evolzen.agents."""

    device: Device = Device.CPU
    population_size: int = Field(default=20, ge=10, le=30, description="Phase 1.2 success metric range.")


class EconomySettings(BaseModel):
    """Phase 1.3 — evolzen.economy."""

    real_data_floor: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Minimum fraction of each generation's training corpus that must be real, "
        "non-agent-generated material (model-collapse safeguard).",
    )


class PredictorSettings(BaseModel):
    """Phase 2.1 — evolzen.predictor."""

    device: Device = Device.CPU
    checkpoint_dir: Path = Path("checkpoints/predictor")
    rehearsal_buffer_size: int = Field(default=10_000, ge=1)


class LibrarySettings(BaseModel):
    """Phase 1.5 — evolzen.library.

    Configuration for the append-only verified-rule library. All paths are
    relative to the working directory unless absolute paths are supplied.
    """

    db_path: Path = Path("data/library.duckdb")
    audit_log_path: Path = Path("data/library_audit.jsonl")
    routing_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0–1) for routing a candidate to an existing entry "
        "instead of spawning a new one. Default uses SequenceMatcher on rule code.",
    )
    max_regression_rounds: int = Field(
        default=3,
        ge=1,
        description="Minimum number of successive addition rounds that must show zero forgetting "
        "for the Phase 1.5 success metric to be considered met (untested until CI runs).",
    )


class RecognitionSettings(BaseModel):
    """Phase 2.3 — evolzen.recognition."""

    device: Device = Device.CPU
    ablation_enabled: bool = Field(
        default=True,
        description="If true, run the with/without/JEPA-only/wake-sleep-only ablation matrix "
        "rather than a single configuration.",
    )


class EvolZenSettings(BaseSettings):
    """Root settings object, composed of one group per subsystem that needs configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EVOLZEN_", env_nested_delimiter="__", env_file=".env", extra="ignore"
    )

    environment: EnvironmentSettings = EnvironmentSettings()
    agents: AgentsSettings = AgentsSettings()
    economy: EconomySettings = EconomySettings()
    library: LibrarySettings = LibrarySettings()
    predictor: PredictorSettings = PredictorSettings()
    recognition: RecognitionSettings = RecognitionSettings()


_SettingsT = TypeVar("_SettingsT", bound=BaseModel)


def load_settings(settings_cls: type[_SettingsT] = EvolZenSettings, yaml_path: Path | None = None) -> _SettingsT:  # type: ignore[assignment]
    """Construct settings, layering a YAML file under environment-variable overrides.

    Args:
        settings_cls: defaults to `EvolZenSettings`; a specific subsystem group can be passed
            for isolated construction in tests.
        yaml_path: path to a YAML file (e.g. ``configs/agents.yaml``). If ``None`` or the file
            doesn't exist, this is equivalent to ``settings_cls()``.
    """
    yaml_overrides: dict[str, Any] = {}
    if yaml_path is not None and yaml_path.exists():
        loaded = yaml.safe_load(yaml_path.read_text())
        if loaded:
            yaml_overrides = loaded
    return settings_cls(**yaml_overrides)
