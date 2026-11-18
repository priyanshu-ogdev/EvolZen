"""Unit tests for standalone SVG training telemetry graphs (Phase 1.2 & 2.1)."""
from __future__ import annotations

from pathlib import Path

from evolzen.cli.viz_graphs import (
    generate_all_training_graphs,
    generate_continual_retention_svg,
    generate_environmental_motives_svg,
    generate_grpo_gradient_dynamics_svg,
    generate_jepa_variance_svg,
    generate_loss_convergence_svg,
    generate_policy_entropy_svg,
    generate_rule_impact_svg,
)


def _sample_telemetry() -> dict[str, object]:
    return {
        "history": [
            {
                "step": 1,
                "planner_loss": 0.45,
                "policy_entropy": 1.78,
                "jepa_variance": 0.082,
                "active_dimensions": 16,
                "bc_loss": 0.41,
            },
            {
                "step": 2,
                "planner_loss": 0.32,
                "policy_entropy": 1.62,
                "jepa_variance": 0.079,
                "active_dimensions": 16,
                "bc_loss": 0.35,
            },
            {
                "step": 3,
                "planner_loss": 0.18,
                "policy_entropy": 1.35,
                "jepa_variance": 0.075,
                "active_dimensions": 16,
                "bc_loss": 0.28,
            },
        ],
        "lineages": {
            "lineage-alpha": {
                "trajectories": 4,
                "initial_loss": 0.41,
                "final_loss": 0.28,
                "task_accuracy": 0.85,
                "retention_score": 0.98,
                "promoted": True,
            },
            "lineage-beta": {
                "trajectories": 3,
                "initial_loss": 0.38,
                "final_loss": 0.29,
                "task_accuracy": 0.78,
                "retention_score": 0.96,
                "promoted": True,
            },
        },
        "motive_vectors": [
            {
                "agent_id": "agent-0",
                "pre_signal": [0.1, 0.4, -0.2, 0.0, 0.5, -0.1, 0.3, 0.0],
                "post_signal": [0.15, 0.6, -0.2, -0.05, 0.2, -0.1, 0.1, 0.0],
                "rewards_vec": [0.0, 0.8, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0],
            }
        ],
    }


def test_generate_loss_convergence_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "loss.svg"
    res = generate_loss_convergence_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "GRPO Planner Loss" in content
    assert "Lineage BC Loss" in content


def test_generate_policy_entropy_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "entropy.svg"
    res = generate_policy_entropy_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "POLICY ENTROPY" in content
    assert "Min Entropy Floor" in content


def test_generate_jepa_variance_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "jepa.svg"
    res = generate_jepa_variance_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "JEPA REPRESENTATION VARIANCE" in content
    assert "Collapse Guard" in content


def test_generate_environmental_motives_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "motives.svg"
    res = generate_environmental_motives_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "ENVIRONMENTAL MOTIVE VECTORS" in content
    assert "Pride" in content
    assert "Greed" in content


def test_generate_continual_retention_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "retention.svg"
    res = generate_continual_retention_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "LINEAGE RETENTION" in content
    assert "Retention Gate" in content
    assert "lineage-alpha" in content


def test_generate_grpo_gradient_dynamics_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "grpo_grad.svg"
    res = generate_grpo_gradient_dynamics_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "GRPO GRADIENT UPDATES" in content
    assert "Gradient Step Norm" in content


def test_generate_rule_impact_svg(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out = tmp_path / "rule_impact.svg"
    res = generate_rule_impact_svg(telemetry, out)
    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "RULE & ENVIRONMENT DATA INGESTION IMPACT" in content
    assert "RECOGNITION ADAPTATION LATENCY" in content


def test_generate_all_training_graphs(tmp_path: Path) -> None:
    telemetry = _sample_telemetry()
    out_dir = tmp_path / "charts"
    paths = generate_all_training_graphs(telemetry, out_dir)
    assert len(paths) == 7
    for _name, p in paths.items():
        assert p.exists()
        assert p.stat().st_size > 0
