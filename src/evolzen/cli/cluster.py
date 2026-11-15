"""Distributed GPU cluster activation and pre-flight diagnostics (Horizon 4).

Provides hardware topology probes, containment validation, and readiness checking
against physical rig specifications documented in docs/hardware-deployment.md:
- DGX Spark (Linux x86_64: Environment, Economy, Exploration, Library, Containment coordinator)
- Jetson AGX Spark (Linux aarch64 Orin: 8-drive population scheduler, Ray worker, vLLM inference)
- RTX A6000 (Linux x86_64: Predictor GRPO training, JEPA representation, dual-track evaluation)
- Standalone (Single-node local development and simulation)

Citations:
- docs/hardware-deployment.md for hardware topology and deployment specifications.
- AGENTS.md Rule #1 for strict gVisor runsc containment boundary.
- Agache et al. (USENIX NSDI 2020) for hardware-isolated microVM sandboxing.
"""
from __future__ import annotations

import contextlib
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from evolzen.containment import is_gvisor_available

__all__ = [
    "TargetNodeRole",
    "diagnose_host_node",
    "format_cluster_report",
    "verify_cluster_connectivity",
]


class TargetNodeRole(StrEnum):
    """Target hardware node role within the distributed cluster topology."""

    DGX_SPARK = "dgx_spark"
    JETSON_AGX = "jetson_agx"
    RTX_A6000 = "rtx_a6000"
    STANDALONE = "standalone"


def _probe_host_environment() -> dict[str, Any]:
    """Probe host operating system, architecture, CPU, and physical memory."""
    os_name = platform.system()
    os_release = platform.release()
    arch = platform.machine()
    proc = platform.processor() or "Unknown"
    py_ver = platform.python_version()

    cpu_logical = os.cpu_count() or 1
    cpu_physical: int | None = None
    mem_total_gb = 0.0
    mem_avail_gb = 0.0
    mem_percent = 0.0

    try:
        import psutil  # type: ignore[import-untyped]

        cpu_physical = psutil.cpu_count(logical=False) or cpu_logical
        vm = psutil.virtual_memory()
        mem_total_gb = round(vm.total / (1024**3), 2)
        mem_avail_gb = round(vm.available / (1024**3), 2)
        mem_percent = round(vm.percent, 1)
    except ImportError:
        pass

    return {
        "os_name": os_name,
        "os_release": os_release,
        "architecture": arch,
        "processor": proc,
        "python_version": py_ver,
        "cpu_logical": cpu_logical,
        "cpu_physical": cpu_physical,
        "memory_total_gb": mem_total_gb,
        "memory_available_gb": mem_avail_gb,
        "memory_used_percent": mem_percent,
    }


def _probe_gvisor() -> dict[str, Any]:
    """Probe gVisor runsc installation, path, and version."""
    available = is_gvisor_available()
    bin_path = shutil.which("runsc")
    version_str: str | None = None

    if bin_path or available:
        target_bin = bin_path or "runsc"
        try:
            res = subprocess.run(
                [target_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if res.returncode == 0:
                first_line = res.stdout.strip().splitlines()
                if first_line:
                    version_str = first_line[0].strip()
        except Exception:
            pass

    return {
        "available": available,
        "binary_path": bin_path,
        "version": version_str,
    }


def _probe_accelerators() -> dict[str, Any]:
    """Probe PyTorch installation, CUDA availability, GPU devices, and VRAM."""
    torch_available = False
    torch_version: str | None = None
    cuda_available = False
    device_count = 0
    devices: list[dict[str, Any]] = []
    mps_available = False

    try:
        import torch

        torch_available = True
        torch_version = torch.__version__
        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            device_count = torch.cuda.device_count()
            for idx in range(device_count):
                props = torch.cuda.get_device_properties(idx)
                devices.append(
                    {
                        "index": idx,
                        "name": torch.cuda.get_device_name(idx),
                        "total_vram_gb": round(props.total_memory / (1024**3), 2),
                        "compute_capability": f"{props.major}.{props.minor}",
                    }
                )
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            mps_available = True
    except ImportError:
        pass

    return {
        "torch_available": torch_available,
        "torch_version": torch_version,
        "cuda_available": cuda_available,
        "device_count": device_count,
        "devices": devices,
        "mps_available": mps_available,
    }


def _probe_ray() -> dict[str, Any]:
    """Probe Ray distributed runtime installation, process status, and cluster daemon."""
    ray_available = False
    ray_version: str | None = None
    ray_initialized = False
    cluster_running = False
    status_summary: str | None = None

    try:
        import ray

        ray_available = True
        ray_version = ray.__version__
        ray_initialized = bool(ray.is_initialized())
    except ImportError:
        pass

    try:
        proc = subprocess.run(
            ["ray", "status"],
            capture_output=True,
            text=True,
            timeout=2.5,
            check=False,
        )
        if proc.returncode == 0:
            cluster_running = True
            lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            status_summary = "; ".join(lines[:3]) if lines else "Ray cluster active"
        else:
            status_summary = "Cluster daemon inactive"
    except Exception:
        status_summary = "Cluster probe timeout or ray CLI unavailable"

    return {
        "installed": ray_available,
        "version": ray_version,
        "initialized": ray_initialized,
        "cluster_running": cluster_running,
        "status_summary": status_summary,
    }


def _parse_host_port(address: str) -> tuple[str, int] | None:
    """Parse host and port from address string if formatted as host:port or ray://host:port."""
    raw = address.strip()
    if raw.startswith("ray://"):
        raw = raw[len("ray://") :]
    if "/" in raw:
        raw = raw.split("/")[0]
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
    return None


def verify_cluster_connectivity(
    address: str | None = None,
    timeout: float = 3.0,
    disconnect: bool = True,
) -> dict[str, Any]:
    """Verify Ray cluster connectivity, cluster topology, and execute a remote healthcheck.

    Checks Ray cluster connectivity (head address, active nodes, total cluster CPUs/GPUs,
    object store memory, custom resources), tests execution of a remote healthcheck task,
    and handles graceful connection/disconnection.

    Args:
        address: Ray cluster head node address (e.g. 'auto', '127.0.0.1:6379',
            'ray://10.0.0.1:10001', or None for local daemon).
        timeout: Timeout in seconds for remote task execution and socket connection.
        disconnect: Whether to disconnect (ray.shutdown) if this call initiated the connection.

    Returns:
        Structured dictionary containing connectivity status, head address,
        active nodes list, resource totals, remote healthcheck metrics, or error details.
    """
    try:
        import ray
    except ImportError:
        return {
            "connected": False,
            "address": address or "auto",
            "nodes_count": 0,
            "active_nodes": [],
            "total_cpus": 0.0,
            "total_gpus": 0.0,
            "object_store_memory_gb": 0.0,
            "custom_resources": {},
            "remote_healthcheck": {
                "status": "FAIL",
                "latency_ms": 0.0,
                "worker_node": None,
                "detail": "Ray package not installed in environment",
            },
            "error": "Ray is not installed. Install ray[default]>=2.38.",
        }

    target_addr = address if address is not None else "auto"
    host_port = _parse_host_port(target_addr)
    if host_port is not None:
        try:
            sock = socket.create_connection(host_port, timeout=timeout)
            sock.close()
        except Exception as sock_err:
            return {
                "connected": False,
                "address": target_addr,
                "nodes_count": 0,
                "active_nodes": [],
                "total_cpus": 0.0,
                "total_gpus": 0.0,
                "object_store_memory_gb": 0.0,
                "custom_resources": {},
                "remote_healthcheck": {
                    "status": "FAIL",
                    "latency_ms": 0.0,
                    "worker_node": None,
                    "detail": f"Socket pre-check failed: {sock_err}",
                },
                "error": f"Failed to connect to Ray address '{target_addr}': {sock_err}",
            }

    was_initialized = bool(ray.is_initialized())
    connected = False
    os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

    try:
        if not was_initialized:
            ray.init(
                address=target_addr,
                ignore_reinit_error=True,
                configure_logging=False,
            )
            connected = True
        else:
            connected = True

        try:
            ctx = ray.get_runtime_context()
            resolved_address = getattr(ctx, "gcs_address", str(target_addr))
        except Exception:
            resolved_address = str(target_addr)

        all_nodes = ray.nodes()  # type: ignore[no-untyped-call]
        active_nodes_raw = [
            n for n in all_nodes
            if bool(n.get("Alive", n.get("alive", False)))
        ]

        active_nodes: list[dict[str, Any]] = []
        for n in active_nodes_raw:
            res = n.get("Resources", {})
            active_nodes.append({
                "node_id": str(n.get("NodeID", "unknown")),
                "address": str(n.get("NodeManagerAddress", "unknown")),
                "hostname": str(n.get("NodeManagerHostname", "unknown")),
                "alive": True,
                "is_head": bool(res.get("node:__internal_head__")),
                "cpus": float(res.get("CPU", 0.0)),
                "gpus": float(res.get("GPU", 0.0)),
                "memory_gb": round(float(res.get("memory", 0.0)) / (1024**3), 2),
                "object_store_gb": round(float(res.get("object_store_memory", 0.0)) / (1024**3), 2),
                "resources": res,
            })

        cluster_resources = ray.cluster_resources()  # type: ignore[no-untyped-call]
        total_cpus = float(cluster_resources.get("CPU", 0.0))
        total_gpus = float(cluster_resources.get("GPU", 0.0))
        object_store_bytes = float(cluster_resources.get("object_store_memory", 0.0))
        object_store_gb = round(object_store_bytes / (1024**3), 2)

        custom_resources: dict[str, float] = {
            k: float(v)
            for k, v in cluster_resources.items()
            if not k.startswith("node:") and k not in ("CPU", "GPU", "memory", "object_store_memory")
        }

        # Remote healthcheck task
        t0 = time.perf_counter()
        try:
            @ray.remote(num_cpus=0)
            def _remote_healthcheck_probe() -> dict[str, Any]:
                import platform as _p
                import time as _t

                try:
                    ip = ray.util.get_node_ip_address()  # type: ignore[no-untyped-call]
                except Exception:
                    ip = _p.node()
                return {
                    "status": "HEALTHY",
                    "node_ip": ip,
                    "timestamp": _t.time(),
                }

            probe_ref = _remote_healthcheck_probe.remote()
            probe_res = ray.get(probe_ref, timeout=timeout)
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            healthcheck_info = {
                "status": "PASS",
                "latency_ms": latency_ms,
                "worker_node": probe_res.get("node_ip"),
                "detail": f"Remote task completed in {latency_ms}ms on {probe_res.get('node_ip')}",
            }
        except Exception as hc_exc:
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            healthcheck_info = {
                "status": "FAIL",
                "latency_ms": latency_ms,
                "worker_node": None,
                "detail": f"Remote healthcheck execution failed: {hc_exc}",
            }

        return {
            "connected": True,
            "address": resolved_address,
            "nodes_count": len(active_nodes),
            "active_nodes": active_nodes,
            "total_cpus": total_cpus,
            "total_gpus": total_gpus,
            "object_store_memory_gb": object_store_gb,
            "custom_resources": custom_resources,
            "remote_healthcheck": healthcheck_info,
            "error": None,
        }
    except Exception as exc:
        return {
            "connected": False,
            "address": target_addr,
            "nodes_count": 0,
            "active_nodes": [],
            "total_cpus": 0.0,
            "total_gpus": 0.0,
            "object_store_memory_gb": 0.0,
            "custom_resources": {},
            "remote_healthcheck": {
                "status": "FAIL",
                "latency_ms": 0.0,
                "worker_node": None,
                "detail": f"Connection failed: {exc}",
            },
            "error": str(exc),
        }
    finally:
        if disconnect and not was_initialized and connected:
            with contextlib.suppress(Exception):
                ray.shutdown()


def _probe_storage_latency() -> dict[str, Any]:
    """Probe DuckDB storage write and read latency on local filesystem."""
    duckdb_installed = False
    duckdb_version: str | None = None
    write_latency_ms = 0.0
    read_latency_ms = 0.0
    healthy = False
    error_message: str | None = None

    try:
        import duckdb

        duckdb_installed = True
        duckdb_version = duckdb.__version__

        with tempfile.TemporaryDirectory() as tmp_dir:
            bench_path = Path(tmp_dir) / "diag_bench.duckdb"
            con = duckdb.connect(str(bench_path))
            con.execute("CREATE TABLE _diag_bench (id INTEGER, payload VARCHAR, ts TIMESTAMP);")

            # Write benchmark: 100 sample transition records
            t0 = time.perf_counter()
            records = [(i, f"agent_transition_payload_{i:04d}") for i in range(100)]
            con.executemany("INSERT INTO _diag_bench VALUES (?, ?, CURRENT_TIMESTAMP);", records)
            write_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            # Read benchmark: aggregate verification
            t1 = time.perf_counter()
            row = con.execute("SELECT COUNT(*), AVG(id) FROM _diag_bench;").fetchone()
            read_latency_ms = round((time.perf_counter() - t1) * 1000.0, 2)
            con.close()

            if row is not None and row[0] == 100:
                healthy = True
    except Exception as exc:
        error_message = str(exc)

    return {
        "installed": duckdb_installed,
        "version": duckdb_version,
        "write_latency_ms": write_latency_ms,
        "read_latency_ms": read_latency_ms,
        "healthy": healthy,
        "error": error_message,
    }


def _evaluate_readiness(
    role: TargetNodeRole,
    host: dict[str, Any],
    gvisor: dict[str, Any],
    accel: dict[str, Any],
    ray_info: dict[str, Any],
    storage: dict[str, Any],
) -> tuple[str, bool, list[dict[str, Any]], list[str]]:
    """Evaluate host deployment readiness against requirements in docs/hardware-deployment.md."""
    checks: list[dict[str, Any]] = []
    recommendations: list[str] = []

    # 1. Host Architecture & OS
    os_name = host.get("os_name", "")
    arch = host.get("architecture", "")
    if role in (TargetNodeRole.DGX_SPARK, TargetNodeRole.RTX_A6000):
        req_arch = "Linux x86_64"
        if os_name == "Linux" and arch in ("x86_64", "AMD64"):
            checks.append({
                "name": "Host Architecture",
                "status": "PASS",
                "requirement": req_arch,
                "actual": f"{os_name} {arch}",
                "detail": f"Matches {role.value} production topology requirement.",
            })
        else:
            checks.append({
                "name": "Host Architecture",
                "status": "FAIL",
                "requirement": req_arch,
                "actual": f"{os_name} {arch}",
                "detail": f"{role.value} requires {req_arch} host per docs/hardware-deployment.md §1.",
            })
            recommendations.append(
                f"[Topology] Node role '{role.value}' specifies {req_arch}; current host is {os_name} {arch}."
            )
    elif role == TargetNodeRole.JETSON_AGX:
        req_arch = "Linux aarch64 (JetPack / Orin)"
        if os_name == "Linux" and arch in ("aarch64", "arm64"):
            checks.append({
                "name": "Host Architecture",
                "status": "PASS",
                "requirement": req_arch,
                "actual": f"{os_name} {arch}",
                "detail": "Matches Jetson AGX ARM64 topology.",
            })
        else:
            checks.append({
                "name": "Host Architecture",
                "status": "FAIL",
                "requirement": req_arch,
                "actual": f"{os_name} {arch}",
                "detail": f"Jetson AGX requires {req_arch} per docs/hardware-deployment.md §1.",
            })
            recommendations.append(
                f"[Topology] Jetson AGX Spark requires Linux aarch64; detected {os_name} {arch}."
            )
    else:  # STANDALONE
        checks.append({
            "name": "Host Architecture",
            "status": "PASS",
            "requirement": "Supported OS (Linux / macOS)",
            "actual": f"{os_name} {arch}",
            "detail": "Supported for local standalone development and simulation.",
        })

    # 2. Host Compute & Memory
    cpus = host.get("cpu_logical", 1)
    mem_gb = host.get("memory_total_gb", 0.0)

    if role == TargetNodeRole.DGX_SPARK:
        req_cpus, req_mem = 16, 32.0
    elif role == TargetNodeRole.JETSON_AGX or role == TargetNodeRole.RTX_A6000:
        req_cpus, req_mem = 8, 32.0
    else:
        req_cpus, req_mem = 2, 4.0

    if cpus >= req_cpus:
        checks.append({
            "name": "CPU Cores",
            "status": "PASS",
            "requirement": f">={req_cpus} logical cores",
            "actual": f"{cpus} cores",
            "detail": "Sufficient CPU concurrency.",
        })
    else:
        checks.append({
            "name": "CPU Cores",
            "status": "WARN",
            "requirement": f">={req_cpus} logical cores",
            "actual": f"{cpus} cores",
            "detail": f"Sub-optimal core count for {role.value} workload.",
        })
        recommendations.append(
            f"[Compute] Detected {cpus} cores; {role.value} recommends >={req_cpus} cores for target concurrency."
        )

    if mem_gb >= req_mem:
        checks.append({
            "name": "Host Memory",
            "status": "PASS",
            "requirement": f">={req_mem} GB RAM",
            "actual": f"{mem_gb} GB",
            "detail": "Meets memory threshold.",
        })
    else:
        status_lvl = "FAIL" if mem_gb < (req_mem / 2) and role != TargetNodeRole.STANDALONE else "WARN"
        checks.append({
            "name": "Host Memory",
            "status": status_lvl,
            "requirement": f">={req_mem} GB RAM",
            "actual": f"{mem_gb} GB",
            "detail": f"Below target memory allocation for {role.value}.",
        })
        recommendations.append(
            f"[Memory] Node has {mem_gb} GB RAM (recommended >={req_mem} GB). Tune batch size or allocate swap."
        )

    # 3. gVisor runsc Containment
    gvisor_ok = gvisor.get("available", False)
    if role == TargetNodeRole.DGX_SPARK:
        if gvisor_ok:
            checks.append({
                "name": "gVisor Sandboxing",
                "status": "PASS",
                "requirement": "runsc binary in PATH",
                "actual": gvisor.get("version") or "Available",
                "detail": "DGX Spark containment coordinator verified.",
            })
        else:
            checks.append({
                "name": "gVisor Sandboxing",
                "status": "FAIL",
                "requirement": "runsc binary in PATH",
                "actual": "Not installed / not in PATH",
                "detail": "AGENTS.md Rule #1: Untrusted agent code must not execute outside gVisor sandbox.",
            })
            recommendations.append(
                "[Containment] Install gVisor runsc per docs/hardware-deployment.md §3: sudo apt-get install -y runsc"
            )
    else:
        if gvisor_ok:
            checks.append({
                "name": "gVisor Sandboxing",
                "status": "PASS",
                "requirement": "Recommended hardware isolation",
                "actual": gvisor.get("version") or "Available",
                "detail": "Hardware-isolated sandbox available.",
            })
        else:
            checks.append({
                "name": "gVisor Sandboxing",
                "status": "WARN",
                "requirement": "Optional / Recommended isolation",
                "actual": "Not installed / not in PATH",
                "detail": "Agent exploration runs in fallback mock mode. Full containment requires runsc.",
            })
            if role != TargetNodeRole.STANDALONE:
                recommendations.append(
                    f"[Containment] Install gVisor runsc on {role.value} per docs/hardware-deployment.md §3."
                )

    # 4. Accelerated Hardware (PyTorch / CUDA)
    cuda_ok = accel.get("cuda_available", False)
    devices = accel.get("devices", [])
    total_vram = sum(d.get("total_vram_gb", 0.0) for d in devices)

    if role in (TargetNodeRole.JETSON_AGX, TargetNodeRole.RTX_A6000):
        if cuda_ok and len(devices) > 0:
            req_vram = 16.0 if role == TargetNodeRole.JETSON_AGX else 24.0
            vram_status = "PASS" if total_vram >= req_vram else "WARN"
            checks.append({
                "name": "CUDA GPU & VRAM",
                "status": vram_status,
                "requirement": f"CUDA GPU (>={req_vram} GB VRAM)",
                "actual": f"{len(devices)} device(s), {total_vram} GB VRAM",
                "detail": ", ".join(d.get("name", "GPU") for d in devices),
            })
            if vram_status == "WARN":
                recommendations.append(
                    f"[GPU] Total VRAM ({total_vram} GB) is below {req_vram} GB recommendation for {role.value}."
                )
        else:
            checks.append({
                "name": "CUDA GPU & VRAM",
                "status": "FAIL",
                "requirement": "NVIDIA CUDA GPU available",
                "actual": "CUDA not available",
                "detail": f"{role.value} requires GPU acceleration per docs/hardware-deployment.md §1.",
            })
            recommendations.append(
                "[GPU] Ensure NVIDIA drivers >=535 are installed and run `uv sync --extra gpu` per §2.2."
            )
    else:  # DGX_SPARK or STANDALONE
        if cuda_ok:
            checks.append({
                "name": "Accelerated Compute",
                "status": "PASS",
                "requirement": "Optional / Available",
                "actual": f"CUDA ({len(devices)} GPUs, {total_vram} GB VRAM)",
                "detail": "CUDA hardware detected.",
            })
        elif accel.get("mps_available", False):
            checks.append({
                "name": "Accelerated Compute",
                "status": "PASS",
                "requirement": "Optional / Available",
                "actual": "Apple Silicon MPS (Metal)",
                "detail": "Apple Silicon GPU acceleration available.",
            })
        else:
            checks.append({
                "name": "Accelerated Compute",
                "status": "PASS",
                "requirement": "Optional (CPU profile active)",
                "actual": "CPU only",
                "detail": "Operating in standard CPU-friendly profile.",
            })

    # 5. Ray Distributed Runtime
    ray_installed = ray_info.get("installed", False)
    cluster_up = ray_info.get("cluster_running", False)
    cluster_conn = ray_info.get("cluster_connectivity")

    if not ray_installed:
        checks.append({
            "name": "Ray Distributed",
            "status": "FAIL",
            "requirement": "ray[default]>=2.38 installed",
            "actual": "Not installed",
            "detail": "Ray package is missing.",
        })
        recommendations.append("[Distributed] Run `uv sync` to install ray[default].")
    elif cluster_conn is not None:
        if cluster_conn.get("connected"):
            hc = cluster_conn.get("remote_healthcheck", {})
            checks.append({
                "name": "Ray Cluster Connectivity",
                "status": "PASS",
                "requirement": "Connected to Ray cluster",
                "actual": (
                    f"{cluster_conn.get('nodes_count')} node(s), "
                    f"{cluster_conn.get('total_cpus')} CPUs, "
                    f"{cluster_conn.get('total_gpus')} GPUs"
                ),
                "detail": (
                    f"Head: {cluster_conn.get('address')}; "
                    f"Healthcheck: {hc.get('status')} ({hc.get('latency_ms')}ms)"
                ),
            })
        else:
            checks.append({
                "name": "Ray Cluster Connectivity",
                "status": "FAIL",
                "requirement": "Connected to Ray cluster",
                "actual": "Connection failed",
                "detail": str(cluster_conn.get("error") or "Could not connect to Ray cluster"),
            })
            recommendations.append(
                f"[Distributed] Verify Ray head at '{cluster_conn.get('address')}' is active and reachable."
            )
    elif role == TargetNodeRole.STANDALONE:
        checks.append({
            "name": "Ray Distributed",
            "status": "PASS",
            "requirement": "Installed",
            "actual": f"Ray {ray_info.get('version')} (Standalone)",
            "detail": "Local multiprocessing ready.",
        })
    else:
        if cluster_up:
            checks.append({
                "name": "Ray Cluster Status",
                "status": "PASS",
                "requirement": "Active cluster daemon",
                "actual": "Cluster active",
                "detail": ray_info.get("status_summary", "Ray operational"),
            })
        else:
            checks.append({
                "name": "Ray Cluster Status",
                "status": "WARN",
                "requirement": "Active cluster daemon",
                "actual": "Daemon inactive / not connected",
                "detail": "Ray cluster has not been launched on this node.",
            })
            if role == TargetNodeRole.DGX_SPARK:
                recommendations.append(
                    "[Distributed] Start cluster head per §5.1: "
                    "ray start --head --port=6379 --dashboard-host=0.0.0.0 --num-cpus=32"
                )
            elif role == TargetNodeRole.JETSON_AGX:
                recommendations.append(
                    "[Distributed] Connect inference worker per §5.1: "
                    "ray start --address='<DGX_SPARK_IP>:6379' --num-gpus=1 --resources='{\"jetson_inference\": 1}'"
                )
            elif role == TargetNodeRole.RTX_A6000:
                recommendations.append(
                    "[Distributed] Connect learning worker per §5.1: "
                    "ray start --address='<DGX_SPARK_IP>:6379' --num-gpus=1 --resources='{\"a6000_training\": 1}'"
                )

    # 6. Storage Performance (DuckDB Latency)
    storage_ok = storage.get("healthy", False)
    w_ms = storage.get("write_latency_ms", 0.0)
    r_ms = storage.get("read_latency_ms", 0.0)

    if storage_ok:
        checks.append({
            "name": "DuckDB Storage",
            "status": "PASS",
            "requirement": "Functional transition store",
            "actual": f"Write: {w_ms}ms, Read: {r_ms}ms",
            "detail": f"DuckDB {storage.get('version')} operational.",
        })
    else:
        checks.append({
            "name": "DuckDB Storage",
            "status": "FAIL",
            "requirement": "Functional transition store",
            "actual": f"Error: {storage.get('error')}",
            "detail": "DuckDB benchmark failed.",
        })
        recommendations.append("[Storage] DuckDB benchmark failed. Verify disk permissions and duckdb installation.")

    # Status summary
    has_fail = any(c["status"] == "FAIL" for c in checks)
    has_warn = any(c["status"] == "WARN" for c in checks)

    if has_fail:
        status = "NOT_READY"
        is_ready = False
    elif has_warn:
        status = "DEGRADED"
        is_ready = True
    else:
        status = "READY"
        is_ready = True

    return status, is_ready, checks, recommendations


def diagnose_host_node(
    role: TargetNodeRole = TargetNodeRole.STANDALONE,
    ray_address: str | None = None,
) -> dict[str, Any]:
    """Diagnose current host node hardware and evaluate readiness for a given cluster role.

    Args:
        role: Target cluster node role (DGX_SPARK, JETSON_AGX, RTX_A6000, or STANDALONE).
        ray_address: Optional Ray cluster head address to verify distributed connectivity.

    Returns:
        Structured dictionary containing hardware attributes, subsystem probes,
        evaluations, and readiness recommendations.
    """
    host = _probe_host_environment()
    gvisor = _probe_gvisor()
    accel = _probe_accelerators()
    ray_info = _probe_ray()
    storage = _probe_storage_latency()

    if ray_address is not None:
        cluster_conn = verify_cluster_connectivity(address=ray_address)
        ray_info["cluster_connectivity"] = cluster_conn

    status, is_ready, checks, recommendations = _evaluate_readiness(
        role=role,
        host=host,
        gvisor=gvisor,
        accel=accel,
        ray_info=ray_info,
        storage=storage,
    )

    role_subsystems = {
        TargetNodeRole.DGX_SPARK: "environment, economy, exploration, library, containment",
        TargetNodeRole.JETSON_AGX: "agents",
        TargetNodeRole.RTX_A6000: "predictor, recognition, evaluation",
        TargetNodeRole.STANDALONE: "all subsystems (local development/simulation)",
    }

    role_responsibilities = {
        TargetNodeRole.DGX_SPARK: "Cluster head, environment Moore machine, DuckDB transition log with SHA-256 hash chains, market clearing, rule library storage, capability verifier, and gVisor containment coordinator.",
        TargetNodeRole.JETSON_AGX: "Population scheduler (10-30 agents), Ray worker, structured LLM inference (VLLMBackend / TransformersBackend), 8-drive developmental decision policies.",
        TargetNodeRole.RTX_A6000: "Grounded world model predictor training (GRPO/PPO), CLEAR rehearsal buffer, Grounded JEPA representation learning (VICReg/LeJEPA), DreamCoder Wake-Sleep MDL compression, and dual-track evaluation harness.",
        TargetNodeRole.STANDALONE: "Local single-machine development, unit/integration testing, and simulation execution.",
    }

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "role": role.value,
        "role_subsystems": role_subsystems.get(role, ""),
        "role_responsibilities": role_responsibilities.get(role, ""),
        "host": host,
        "gvisor": gvisor,
        "accelerators": accel,
        "ray": ray_info,
        "storage": storage,
        "readiness": {
            "status": status,
            "is_ready": is_ready,
            "checks": checks,
            "recommendations": recommendations,
        },
    }


def format_cluster_report(diagnosis: dict[str, Any]) -> str:
    """Format diagnosis dictionary into a clear, structured terminal diagnostic report.

    Args:
        diagnosis: Output of `diagnose_host_node`.

    Returns:
        Formatted multi-line report string.
    """
    role_str = str(diagnosis.get("role", "standalone")).upper()
    subsystems = diagnosis.get("role_subsystems", "All")
    responsibilities = diagnosis.get("role_responsibilities", "")
    ts = diagnosis.get("timestamp", "")
    readiness = diagnosis.get("readiness", {})
    status = readiness.get("status", "UNKNOWN")
    checks: list[dict[str, Any]] = readiness.get("checks", [])
    recommendations: list[str] = readiness.get("recommendations", [])

    host = diagnosis.get("host", {})
    gvisor = diagnosis.get("gvisor", {})
    accel = diagnosis.get("accelerators", {})
    ray_info = diagnosis.get("ray", {})
    storage = diagnosis.get("storage", {})

    lines: list[str] = []
    lines.append("=" * 80)
    lines.append("EVOLZEN DISTRIBUTED CLUSTER PRE-FLIGHT DIAGNOSTICS")
    lines.append("=" * 80)
    lines.append(f"Target Role:        {role_str}")
    lines.append(f"Allocated Modules:  {subsystems}")
    lines.append(f"Primary Duty:       {responsibilities}")
    lines.append(f"Diagnostic Time:    {ts}")
    lines.append(f"Deployment Status:  {status} (Ready: {readiness.get('is_ready', False)})")
    lines.append("")

    lines.append("-" * 80)
    lines.append("1. Host Platform & Environment")
    lines.append("-" * 80)
    lines.append(f"  OS & Kernel:      {host.get('os_name')} {host.get('os_release')}")
    lines.append(f"  Architecture:     {host.get('architecture')} ({host.get('processor')})")
    lines.append(
        f"  CPU Cores:        {host.get('cpu_logical')} logical (Physical: {host.get('cpu_physical')})"
    )
    lines.append(
        f"  System Memory:    {host.get('memory_total_gb')} GB total "
        f"({host.get('memory_available_gb')} GB available, {host.get('memory_used_percent')}% used)"
    )
    lines.append(f"  Python Version:   {host.get('python_version')}")
    lines.append("")

    lines.append("-" * 80)
    lines.append("2. Subsystem Hardware & Containment Probes")
    lines.append("-" * 80)
    gvisor_stat = "AVAILABLE" if gvisor.get("available") else "NOT DETECTED"
    gvisor_path = gvisor.get("binary_path") or "None"
    gvisor_ver = f" ({gvisor.get('version')})" if gvisor.get("version") else ""
    lines.append(f"  gVisor Sandboxing: {gvisor_stat} (Path: {gvisor_path}){gvisor_ver}")

    if accel.get("cuda_available"):
        dev_desc = ", ".join(f"[{d['index']}] {d['name']} ({d['total_vram_gb']}GB)" for d in accel.get("devices", []))
        lines.append(f"  GPU Acceleration:  CUDA DETECTED — {dev_desc}")
    elif accel.get("mps_available"):
        lines.append("  GPU Acceleration:  Apple Silicon MPS (Metal Performance Shaders) AVAILABLE")
    else:
        lines.append("  GPU Acceleration:  CPU-only (No CUDA accelerator detected)")
    lines.append(f"  PyTorch Version:   {accel.get('torch_version') or 'Not installed'}")

    ray_stat = "RUNNING" if ray_info.get("cluster_running") else "INACTIVE / NOT CONNECTED"
    lines.append(
        f"  Ray Distributed:   {ray_stat} (Version: {ray_info.get('version') or 'N/A'}; {ray_info.get('status_summary')})"
    )

    cluster_conn = ray_info.get("cluster_connectivity")
    if cluster_conn and cluster_conn.get("connected"):
        lines.append(f"  Ray Cluster Head:  {cluster_conn.get('address')}")
        lines.append(
            f"  Cluster Topology:  {cluster_conn.get('nodes_count')} Active Node(s) | "
            f"Total CPUs: {cluster_conn.get('total_cpus')} | Total GPUs: {cluster_conn.get('total_gpus')} | "
            f"Object Store: {cluster_conn.get('object_store_memory_gb')} GB"
        )
        custom_res = cluster_conn.get("custom_resources", {})
        if custom_res:
            res_str = ", ".join(f"{k}: {v}" for k, v in sorted(custom_res.items()))
            lines.append(f"  Custom Resources:  {res_str}")
        hc = cluster_conn.get("remote_healthcheck", {})
        lines.append(
            f"  Remote Healthcheck: {hc.get('status')} ({hc.get('latency_ms')}ms on {hc.get('worker_node') or 'local'})"
        )
        active_nodes = cluster_conn.get("active_nodes", [])
        if active_nodes:
            lines.append("  Active Cluster Nodes:")
            for idx, node in enumerate(active_nodes, 1):
                head_flag = " [HEAD]" if node.get("is_head") else " [WORKER]"
                lines.append(
                    f"    - Node {idx}{head_flag}: {node.get('hostname')} ({node.get('address')}) "
                    f"| CPUs: {node.get('cpus')} | GPUs: {node.get('gpus')} | Mem: {node.get('memory_gb')}GB"
                )
    elif cluster_conn and not cluster_conn.get("connected"):
        lines.append(
            f"  Ray Cluster Head:  FAILED to connect to {cluster_conn.get('address')} ({cluster_conn.get('error')})"
        )

    storage_stat = "HEALTHY" if storage.get("healthy") else "DEGRADED / FAILED"
    lines.append(
        f"  DuckDB Storage:    {storage_stat} (v{storage.get('version')}) "
        f"— Write: {storage.get('write_latency_ms')}ms | Read: {storage.get('read_latency_ms')}ms"
    )
    lines.append("")

    lines.append("-" * 80)
    lines.append("3. Pre-Flight Readiness Matrix (docs/hardware-deployment.md)")
    lines.append("-" * 80)
    for c in checks:
        badge = f"[{c['status']}]"
        lines.append(f"  {badge:<7} {c['name']}: {c['actual']} (Requirement: {c['requirement']})")
        if c.get("detail"):
            lines.append(f"          -> {c['detail']}")
    lines.append("")

    lines.append("-" * 80)
    lines.append("4. Deployment Recommendations & Remediations")
    lines.append("-" * 80)
    if recommendations:
        for rec in recommendations:
            lines.append(f"  * {rec}")
    else:
        lines.append("  * All pre-flight deployment checks passed cleanly. Node is fully ready for activation.")
    lines.append("=" * 80)

    return "\n".join(lines)
