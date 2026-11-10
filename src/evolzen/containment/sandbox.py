"""Hardware-isolated execution interface (Phase 2.2).

The 2026 default for untrusted, autonomous, code-generating agents is hardware-isolated
execution (Firecracker microVMs or gVisor), not a kernel-sharing container — a container-level
exploit can escape to the host, and this project's agent population is both self-modifying
(`evolzen.agents`) and code-writing (`evolzen.exploration`, `evolzen.library`), which is a
materially higher risk profile than a single sandboxed script.

This module is an **interface only**. Provisioning the actual microVM/gVisor infrastructure on
the DGX Spark is an infrastructure task, not a Python dependency — see
docs/phases/2.2-containment.md and CORAL's safeguard checklist (arXiv:2604.01658).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    wall_time_seconds: float
    resource_ceiling_hit: bool


class Sandbox(Protocol):
    """Protocol satisfied by a concrete Firecracker/gVisor-backed executor.

    Never execute code from `evolzen.exploration.synthesizer` or
    `evolzen.agents.self_modification` outside an implementation of this protocol, even during
    early development with toy code.
    """

    def run(self, code: str, *, timeout_seconds: float, resource_ceiling_mb: int) -> ExecutionResult:
        """Execute `code` in full isolation and return the result, never raising on the code's
        own errors (surface those via `ExecutionResult.stderr` / `exit_code` instead)."""
        ...
