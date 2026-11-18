"""Unit tests for AdapterTrainingConfig.tier1() and tier2() classmethods.

Verifies that the canonical preset classmethod factories return the
exact configuration values specified in the Qwen 3.5 9B VL AWQ
dual-tier finalised architecture (Phase 1.2).
"""
from __future__ import annotations

from evolzen.agents.trainer import AdapterTrainingConfig


def test_tier1_preset_adapter_type() -> None:
    """Tier-1 preset uses standard LoRA (not DoRA)."""
    cfg = AdapterTrainingConfig.tier1()
    assert cfg.adapter_type == "lora"


def test_tier1_preset_dora_magnitude_false() -> None:
    """Tier-1 preset must have dora_magnitude=False."""
    cfg = AdapterTrainingConfig.tier1()
    assert cfg.dora_magnitude is False


def test_tier1_preset_rank_and_alpha() -> None:
    """Tier-1 LoRA rank=8, alpha=16 per finalised spec."""
    cfg = AdapterTrainingConfig.tier1()
    assert cfg.lora_rank == 8
    assert cfg.lora_alpha == 16


def test_tier1_preset_learning_rate() -> None:
    """Tier-1 learning_rate is 1e-4."""
    cfg = AdapterTrainingConfig.tier1()
    assert abs(cfg.learning_rate - 1e-4) < 1e-10


def test_tier1_preset_epochs() -> None:
    """Tier-1 trains for 3 epochs."""
    cfg = AdapterTrainingConfig.tier1()
    assert cfg.epochs == 3


def test_tier2_preset_adapter_type() -> None:
    """Tier-2 preset uses DoRA."""
    cfg = AdapterTrainingConfig.tier2()
    assert cfg.adapter_type == "dora"


def test_tier2_preset_dora_magnitude_true() -> None:
    """Tier-2 preset must have dora_magnitude=True (decoupled magnitude)."""
    cfg = AdapterTrainingConfig.tier2()
    assert cfg.dora_magnitude is True


def test_tier2_preset_rank_and_alpha() -> None:
    """Tier-2 DoRA rank=16, alpha=32 per finalised spec."""
    cfg = AdapterTrainingConfig.tier2()
    assert cfg.lora_rank == 16
    assert cfg.lora_alpha == 32


def test_tier2_preset_learning_rate() -> None:
    """Tier-2 learning_rate is 5e-5 (conservative for deliberative planning)."""
    cfg = AdapterTrainingConfig.tier2()
    assert abs(cfg.learning_rate - 5e-5) < 1e-11


def test_tier2_preset_epochs() -> None:
    """Tier-2 trains for 5 epochs."""
    cfg = AdapterTrainingConfig.tier2()
    assert cfg.epochs == 5


def test_tier2_preset_max_rehearsal_samples() -> None:
    """Tier-2 uses rehearsal buffer of 1000 samples to prevent forgetting."""
    cfg = AdapterTrainingConfig.tier2()
    assert cfg.max_rehearsal_samples == 1000


def test_tier1_and_tier2_are_independent_instances() -> None:
    """Each classmethod call returns a fresh independent frozen instance."""
    t1a = AdapterTrainingConfig.tier1()
    t1b = AdapterTrainingConfig.tier1()
    t2 = AdapterTrainingConfig.tier2()
    # Frozen dataclass — verify values are independent (same type, correct defaults)
    assert t1a.epochs == t1b.epochs == 3
    assert t2.epochs == 5
    assert t1a is not t1b  # separate instances


def test_tier1_vs_tier2_differ_on_key_fields() -> None:
    """Tier-1 and Tier-2 presets produce meaningfully different configs."""
    t1 = AdapterTrainingConfig.tier1()
    t2 = AdapterTrainingConfig.tier2()
    assert t1.adapter_type != t2.adapter_type
    assert t1.lora_rank < t2.lora_rank
    assert t1.learning_rate > t2.learning_rate  # tier2 is more conservative
    assert t1.epochs < t2.epochs
