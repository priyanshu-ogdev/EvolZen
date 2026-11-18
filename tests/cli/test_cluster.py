from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from evolzen.cli.cluster import (
    TargetNodeRole,
    benchmark_neural_inference,
    diagnose_host_node,
    format_cluster_report,
    verify_cluster_connectivity,
)
from evolzen.cli.main import app

runner = CliRunner()


def test_verify_cluster_connectivity_unreachable() -> None:
    # Target an unreachable port
    result = verify_cluster_connectivity(address="127.0.0.1:59998", timeout=0.5)
    assert result["connected"] is False
    assert result["address"] == "127.0.0.1:59998"
    assert result["nodes_count"] == 0
    assert result["active_nodes"] == []
    assert result["total_cpus"] == 0.0
    assert result["total_gpus"] == 0.0
    assert result["remote_healthcheck"]["status"] == "FAIL"
    assert result["error"] is not None


def test_verify_cluster_connectivity_ray_not_installed() -> None:
    with patch.dict("sys.modules", {"ray": None}):
        result = verify_cluster_connectivity(address="127.0.0.1:6379")
        assert result["connected"] is False
        assert "Ray is not installed" in str(result["error"])
        assert result["remote_healthcheck"]["status"] == "FAIL"


def test_verify_cluster_connectivity_mock_cluster() -> None:
    mock_ray = MagicMock()
    mock_ray.is_initialized.return_value = False

    ctx = MagicMock()
    ctx.gcs_address = "192.168.1.100:6379"
    mock_ray.get_runtime_context.return_value = ctx

    mock_nodes = [
        {
            "NodeID": "head-dgx-spark-node",
            "Alive": True,
            "NodeManagerAddress": "192.168.1.100",
            "NodeManagerHostname": "dgx-spark-head",
            "Resources": {
                "node:__internal_head__": 1.0,
                "CPU": 32.0,
                "GPU": 0.0,
                "memory": 64.0 * (1024**3),
                "object_store_memory": 16.0 * (1024**3),
            },
        },
        {
            "NodeID": "worker-jetson-orin",
            "Alive": True,
            "NodeManagerAddress": "192.168.1.101",
            "NodeManagerHostname": "jetson-agx-spark",
            "Resources": {
                "CPU": 8.0,
                "GPU": 1.0,
                "memory": 32.0 * (1024**3),
                "object_store_memory": 8.0 * (1024**3),
                "jetson_inference": 1.0,
            },
        },
        {
            "NodeID": "worker-rtx-a6000",
            "Alive": True,
            "NodeManagerAddress": "192.168.1.102",
            "NodeManagerHostname": "rtx-a6000-node",
            "Resources": {
                "CPU": 16.0,
                "GPU": 1.0,
                "memory": 64.0 * (1024**3),
                "object_store_memory": 16.0 * (1024**3),
                "a6000_training": 1.0,
            },
        },
        {
            "NodeID": "stale-dead-node",
            "Alive": False,
            "NodeManagerAddress": "192.168.1.199",
            "NodeManagerHostname": "dead-node",
            "Resources": {"CPU": 4.0},
        },
    ]
    mock_ray.nodes.return_value = mock_nodes

    mock_resources = {
        "node:__internal_head__": 1.0,
        "CPU": 56.0,
        "GPU": 2.0,
        "memory": 160.0 * (1024**3),
        "object_store_memory": 40.0 * (1024**3),
        "jetson_inference": 1.0,
        "a6000_training": 1.0,
    }
    mock_ray.cluster_resources.return_value = mock_resources

    # Remote function decorator mock
    def fake_remote(*args: Any, **kwargs: Any) -> Any:
        def decorator(fn: Any) -> Any:
            mock_task = MagicMock()
            mock_task.remote.return_value = "object_ref_123"
            return mock_task

        return decorator

    mock_ray.remote = fake_remote
    mock_ray.get.return_value = {
        "status": "HEALTHY",
        "node_ip": "192.168.1.100",
        "timestamp": 1700000000.0,
    }

    with patch.dict("sys.modules", {"ray": mock_ray}):
        # Use an address without host:port or mock socket so socket.create_connection is skipped
        res = verify_cluster_connectivity(address="auto", timeout=2.0, disconnect=True)

    assert res["connected"] is True
    assert res["address"] == "192.168.1.100:6379"
    assert res["nodes_count"] == 3  # dead node filtered out
    assert res["total_cpus"] == 56.0
    assert res["total_gpus"] == 2.0
    assert res["object_store_memory_gb"] == 40.0
    assert res["custom_resources"] == {"jetson_inference": 1.0, "a6000_training": 1.0}
    assert res["remote_healthcheck"]["status"] == "PASS"
    assert res["remote_healthcheck"]["worker_node"] == "192.168.1.100"
    assert res["error"] is None

    # Check active node details
    head_node = next(n for n in res["active_nodes"] if n["node_id"] == "head-dgx-spark-node")
    assert head_node["is_head"] is True
    assert head_node["cpus"] == 32.0
    assert head_node["hostname"] == "dgx-spark-head"

    jetson_node = next(n for n in res["active_nodes"] if n["node_id"] == "worker-jetson-orin")
    assert jetson_node["is_head"] is False
    assert jetson_node["gpus"] == 1.0
    assert jetson_node["resources"].get("jetson_inference") == 1.0

    # Ensure ray.shutdown was called gracefully
    mock_ray.shutdown.assert_called_once()


def test_diagnose_host_node_with_ray_address() -> None:
    # Diagnose with unreachable address
    diag = diagnose_host_node(
        role=TargetNodeRole.DGX_SPARK,
        ray_address="127.0.0.1:59997",
    )
    assert diag["role"] == "dgx_spark"
    assert "ray" in diag
    assert "cluster_connectivity" in diag["ray"]
    conn = diag["ray"]["cluster_connectivity"]
    assert conn["connected"] is False

    checks = diag["readiness"]["checks"]
    conn_check = next((c for c in checks if c["name"] == "Ray Cluster Connectivity"), None)
    assert conn_check is not None
    assert conn_check["status"] == "FAIL"


def test_format_cluster_report_with_connectivity() -> None:
    mock_diag: dict[str, Any] = {
        "role": "dgx_spark",
        "role_subsystems": "environment, economy, exploration, library, containment",
        "role_responsibilities": "Cluster head and containment coordinator",
        "timestamp": "2026-11-15T18:00:00Z",
        "host": {
            "os_name": "Linux",
            "os_release": "6.5.0",
            "architecture": "x86_64",
            "processor": "AMD EPYC",
            "cpu_logical": 32,
            "cpu_physical": 16,
            "memory_total_gb": 64.0,
            "memory_available_gb": 48.0,
            "memory_used_percent": 25.0,
            "python_version": "3.12.0",
        },
        "gvisor": {"available": True, "binary_path": "/usr/bin/runsc", "version": "runsc 2024"},
        "accelerators": {"cuda_available": False, "devices": [], "torch_version": "2.4.0"},
        "ray": {
            "installed": True,
            "version": "2.38.0",
            "cluster_running": True,
            "status_summary": "Ray cluster active",
            "cluster_connectivity": {
                "connected": True,
                "address": "192.168.1.100:6379",
                "nodes_count": 3,
                "total_cpus": 56.0,
                "total_gpus": 2.0,
                "object_store_memory_gb": 40.0,
                "custom_resources": {"a6000_training": 1.0, "jetson_inference": 1.0},
                "remote_healthcheck": {
                    "status": "PASS",
                    "latency_ms": 12.5,
                    "worker_node": "192.168.1.100",
                    "detail": "Remote task completed in 12.5ms",
                },
                "active_nodes": [
                    {
                        "node_id": "head-dgx",
                        "address": "192.168.1.100",
                        "hostname": "dgx-spark-head",
                        "is_head": True,
                        "cpus": 32.0,
                        "gpus": 0.0,
                        "memory_gb": 64.0,
                    },
                    {
                        "node_id": "worker-jetson",
                        "address": "192.168.1.101",
                        "hostname": "jetson-orin",
                        "is_head": False,
                        "cpus": 8.0,
                        "gpus": 1.0,
                        "memory_gb": 32.0,
                    },
                ],
            },
        },
        "storage": {"healthy": True, "version": "1.0.0", "write_latency_ms": 1.2, "read_latency_ms": 0.8},
        "readiness": {
            "status": "READY",
            "is_ready": True,
            "checks": [
                {
                    "name": "Ray Cluster Connectivity",
                    "status": "PASS",
                    "requirement": "Connected to Ray cluster",
                    "actual": "3 node(s), 56.0 CPUs, 2.0 GPUs",
                    "detail": "Head: 192.168.1.100:6379; Healthcheck: PASS (12.5ms)",
                }
            ],
            "recommendations": [],
        },
    }

    report = format_cluster_report(mock_diag)
    assert "Ray Cluster Head:  192.168.1.100:6379" in report
    assert "Cluster Topology:  3 Active Node(s) | Total CPUs: 56.0 | Total GPUs: 2.0 | Object Store: 40.0 GB" in report
    assert "Custom Resources:  a6000_training: 1.0, jetson_inference: 1.0" in report
    assert "Remote Healthcheck: PASS (12.5ms on 192.168.1.100)" in report
    assert "Active Cluster Nodes:" in report
    assert "Node 1 [HEAD]: dgx-spark-head (192.168.1.100) | CPUs: 32.0 | GPUs: 0.0 | Mem: 64.0GB" in report
    assert "Node 2 [WORKER]: jetson-orin (192.168.1.101) | CPUs: 8.0 | GPUs: 1.0 | Mem: 32.0GB" in report


def test_cli_cluster_export_json(tmp_path: Path) -> None:
    export_file = tmp_path / "cluster_test.json"
    result = runner.invoke(
        app,
        ["cluster", "--role", "dgx_spark", "--export-json", str(export_file)],
    )
    assert result.exit_code == 0
    assert f"Cluster diagnostics exported to: {export_file}" in result.stdout
    assert export_file.exists()

    data = json.loads(export_file.read_text(encoding="utf-8"))
    assert data["role"] == "dgx_spark"
    assert "host" in data
    assert "gvisor" in data
    assert "accelerators" in data
    assert "ray" in data
    assert "storage" in data
    assert "readiness" in data


def test_cli_cluster_with_address_and_export(tmp_path: Path) -> None:
    export_file = tmp_path / "cluster_conn_test.json"
    result = runner.invoke(
        app,
        [
            "cluster",
            "--role",
            "standalone",
            "--address",
            "127.0.0.1:59996",
            "--export-json",
            str(export_file),
        ],
    )
    assert result.exit_code == 0
    assert export_file.exists()
    assert "FAILED to connect to 127.0.0.1:59996" in result.stdout

    data = json.loads(export_file.read_text(encoding="utf-8"))
    assert "cluster_connectivity" in data["ray"]
    assert data["ray"]["cluster_connectivity"]["connected"] is False


def test_benchmark_neural_inference_transformers() -> None:
    """Verifies that benchmark_neural_inference measures throughput, latency, and valid schema."""
    result = benchmark_neural_inference(backend_type="transformers", batch_size=4)
    assert result["backend_type"] == "transformers"
    assert result["model_id"] == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    assert result["batch_size"] == 4
    assert result["total_time_seconds"] > 0
    assert result["throughput_actions_per_sec"] > 0
    assert result["mean_latency_ms"] >= 0
    assert result["p95_latency_ms"] >= 0
    assert result["schema_validity_rate"] == 1.0
    assert result["valid_actions_count"] == 4
    assert result["error"] is None


def test_benchmark_neural_inference_invalid_backend() -> None:
    """Verifies that benchmark_neural_inference reports error for unsupported backends."""
    result = benchmark_neural_inference(backend_type="unsupported_backend")
    assert result["error"] is not None
    assert result["schema_validity_rate"] == 0.0
    assert result["throughput_actions_per_sec"] == 0.0


def test_cli_cluster_benchmark_inference() -> None:
    """Verifies that evolzen cluster --benchmark-inference outputs the neural benchmark section."""
    result = runner.invoke(app, ["cluster", "--benchmark-inference"])
    assert result.exit_code == 0
    assert "Neural LLM Inference Benchmark" in result.stdout
    assert "transformers" in result.stdout
    assert "actions/sec" in result.stdout
    assert "Schema Validity:" in result.stdout


def test_cli_cluster_benchmark_inference_json() -> None:
    """Verifies that evolzen cluster --benchmark-inference with --json outputs valid JSON."""
    result = runner.invoke(app, ["cluster", "--benchmark-inference", "--json"])
    assert result.exit_code == 0
    stdout_data = json.loads(result.stdout)
    assert "neural_inference_benchmark" in stdout_data
    assert stdout_data["neural_inference_benchmark"]["schema_validity_rate"] == 1.0
    assert stdout_data["neural_inference_benchmark"]["valid_actions_count"] == 4


def test_cli_cluster_benchmark_inference_export_json(tmp_path: Path) -> None:
    """Verifies that evolzen cluster --benchmark-inference exports JSON file."""
    export_file = tmp_path / "cluster_bench.json"
    result = runner.invoke(
        app,
        ["cluster", "--benchmark-inference", "--export-json", str(export_file)],
    )
    assert result.exit_code == 0
    assert export_file.exists()
    exported_data = json.loads(export_file.read_text(encoding="utf-8"))
    assert "neural_inference_benchmark" in exported_data
    assert exported_data["neural_inference_benchmark"]["backend_type"] == "transformers"
    assert exported_data["neural_inference_benchmark"]["schema_validity_rate"] == 1.0


