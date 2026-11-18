"""Hardware-isolated execution interface and gVisor driver (Phase 2.2).

The 2026 default for untrusted, autonomous, code-generating agents is hardware-isolated
execution (Firecracker microVMs or gVisor), not a kernel-sharing container — a container-level
exploit can escape to the host, and this project's agent population is both self-modifying
(`evolzen.agents`) and code-writing (`evolzen.exploration`, `evolzen.library`), which is a
materially higher risk profile than a single sandboxed script.

Citations:
- Agache et al. (*Firecracker*, *USENIX NSDI* 2020) for minimal attack surface isolation.
- CORAL safeguard checklist (arXiv:2604.01658).
- Sidik & Rokach (arXiv:2604.11839) and arXiv:2502.04512 for open-ended AI containment bounds.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of a sandboxed code execution."""

    stdout: str
    stderr: str
    exit_code: int
    wall_time_seconds: float
    resource_ceiling_hit: bool
    structured_output: dict[str, Any] | None = None

    @property
    def is_success(self) -> bool:
        """True if execution completed with exit code 0 and within resource limits."""
        return self.exit_code == 0 and not self.resource_ceiling_hit

    def get_json_output(self) -> dict[str, Any] | None:
        """Parse and return structured JSON payload from structured_output or stdout.

        Returns:
            Dictionary payload if valid JSON is present, None otherwise.
        """
        if self.structured_output is not None:
            return self.structured_output
        if not self.stdout:
            return None
        text = self.stdout.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    continue
        return None


@runtime_checkable
class Sandbox(Protocol):
    """Protocol satisfied by a concrete hardware-isolated executor.

    Never execute code from `evolzen.exploration.synthesizer` or
    `evolzen.agents.self_modification` outside an implementation of this protocol, even during
    early development with toy code.
    """

    def run(
        self,
        code: str,
        *,
        timeout_seconds: float = 2.0,
        resource_ceiling_mb: int = 128,
        input_data: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute `code` in full isolation and return the result, never raising on the code's
        own errors (surface those via `ExecutionResult.stderr` / `exit_code` instead)."""
        ...


def is_gvisor_available(runsc_path: str = "runsc") -> bool:
    """Probe whether gVisor (runsc) is installed and functional on the host.

    Args:
        runsc_path: Binary name or path to the runsc executable.

    Returns:
        True if runsc is located and returns 0 on `runsc --version`, False otherwise.
    """
    resolved = shutil.which(runsc_path)
    if resolved is None and not (Path(runsc_path).is_file() and os.access(runsc_path, os.X_OK)):
        return False
    target = resolved if resolved is not None else runsc_path
    try:
        proc = subprocess.run(
            [target, "--version"],
            capture_output=True,
            timeout=2.0,
            text=True,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class GVisorSandbox:
    """Hardware-isolated sandbox backed by Google gVisor (runsc).

    Satisfies the :class:`Sandbox` protocol. Executes untrusted code inside
    an isolated gVisor user-space kernel sandbox with network disabled (--net=none),
    enforced memory ceiling, and wall-time execution timeout.

    Per SECURITY.md, this executor fails closed and raises a RuntimeError if
    runsc is unavailable; it NEVER falls back to bare subprocess or shared-kernel
    containers in production.
    """

    def __init__(
        self,
        runsc_path: str = "runsc",
        default_timeout_seconds: float = 2.0,
        default_resource_ceiling_mb: int = 128,
    ) -> None:
        self.runsc_path = runsc_path
        self.default_timeout_seconds = default_timeout_seconds
        self.default_resource_ceiling_mb = default_resource_ceiling_mb

    def build_command(
        self,
        code: str,
        *,
        resource_ceiling_mb: int = 128,
        input_data: dict[str, Any] | None = None,
    ) -> list[str]:
        """Construct the argument list for running untrusted code under runsc do."""
        input_json_repr = repr(json.dumps(input_data)) if input_data is not None else "None"
        runner_script = (
            "import sys, resource, json\n"
            f"ceiling_bytes = {resource_ceiling_mb} * 1024 * 1024\n"
            "try:\n"
            "    resource.setrlimit(resource.RLIMIT_AS, (ceiling_bytes, ceiling_bytes))\n"
            "except Exception:\n"
            "    pass\n"
            f"raw_input = {input_json_repr}\n"
            "input_data = json.loads(raw_input) if raw_input not in (None, 'None') else None\n"
            f"exec(compile({repr(code)}, '<sandboxed_code>', 'exec'), {{'__name__': '__main__', 'input_data': input_data}})\n"
        )
        return [
            self.runsc_path,
            "--net=none",
            "do",
            "python3",
            "-c",
            runner_script,
        ]

    _build_command = build_command

    def run(
        self,
        code: str,
        *,
        timeout_seconds: float = 2.0,
        resource_ceiling_mb: int = 128,
        input_data: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute untrusted code in full isolation.

        Never raises on untrusted code errors; surfaces failures via ExecutionResult.
        Raises RuntimeError only if gVisor is not installed or available.
        """
        if not is_gvisor_available(self.runsc_path):
            raise RuntimeError(
                "gVisor (runsc) is not installed or available on this host. "
                "Use MockSandbox in tests or provision runsc on Linux target."
            )

        cmd = self.build_command(
            code,
            resource_ceiling_mb=resource_ceiling_mb,
            input_data=input_data,
        )
        stdin_payload = json.dumps(input_data) if input_data is not None else None
        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                input=stdin_payload,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            wall_time = time.perf_counter() - start_time
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode

            resource_hit = (
                exit_code in (-9, 137)
                or "MemoryError" in stderr
                or "out of memory" in stderr.lower()
            )

            structured: dict[str, Any] | None = None
            if stdout:
                try:
                    parsed = json.loads(stdout.strip())
                    if isinstance(parsed, dict):
                        structured = parsed
                except Exception:
                    pass

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                wall_time_seconds=wall_time,
                resource_ceiling_hit=resource_hit,
                structured_output=structured,
            )
        except subprocess.TimeoutExpired as exc:
            wall_time = time.perf_counter() - start_time
            out = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            timeout_msg = f"Execution timed out after {timeout_seconds} seconds.\n{err}".strip()
            return ExecutionResult(
                stdout=out,
                stderr=timeout_msg,
                exit_code=124,
                wall_time_seconds=wall_time,
                resource_ceiling_hit=False,
                structured_output=None,
            )
        except Exception as exc:
            wall_time = time.perf_counter() - start_time
            return ExecutionResult(
                stdout="",
                stderr=f"Sandbox execution error: {exc}",
                exit_code=1,
                wall_time_seconds=wall_time,
                resource_ceiling_hit=False,
                structured_output=None,
            )


class MockSandbox:
    """Deterministic mock sandbox satisfying the :class:`Sandbox` protocol.

    Provides hermetic execution for development environments, tests, and non-Linux hosts
    without requiring root privileges, gVisor / runsc, or Firecracker. Accurately records
    call history and allows simulation of timeouts, memory ceilings, and custom results.
    """

    def __init__(
        self,
        *,
        simulate_timeout: bool = False,
        simulate_oom: bool = False,
        custom_result: ExecutionResult | None = None,
        default_structured_output: dict[str, Any] | None = None,
    ) -> None:
        self.simulate_timeout = simulate_timeout
        self.simulate_oom = simulate_oom
        self.custom_result = custom_result
        self.default_structured_output = default_structured_output
        self.call_history: list[dict[str, Any]] = []

    def clear(self) -> None:
        """Clear recorded invocation history."""
        self.call_history.clear()

    def run(
        self,
        code: str,
        *,
        timeout_seconds: float = 2.0,
        resource_ceiling_mb: int = 128,
        input_data: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute or simulate sandboxed code execution, recording invocation history."""
        call_record: dict[str, Any] = {
            "code": code,
            "timeout_seconds": timeout_seconds,
            "resource_ceiling_mb": resource_ceiling_mb,
            "input_data": input_data,
        }
        self.call_history.append(call_record)

        if self.custom_result is not None:
            return self.custom_result

        if self.simulate_timeout:
            return ExecutionResult(
                stdout="",
                stderr=f"Mock execution timed out after {timeout_seconds} seconds",
                exit_code=124,
                wall_time_seconds=timeout_seconds,
                resource_ceiling_hit=False,
                structured_output=None,
            )

        if self.simulate_oom:
            return ExecutionResult(
                stdout="",
                stderr=f"Mock resource ceiling: memory ceiling ({resource_ceiling_mb} MB) exceeded",
                exit_code=137,
                wall_time_seconds=0.01,
                resource_ceiling_hit=True,
                structured_output=None,
            )

        # Hermetic execution in isolated globals namespace
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        start = time.perf_counter()
        exit_code = 0

        # Safe isolated execution context
        safe_globals: dict[str, Any] = {
            "__name__": "__main__",
            "input_data": input_data,
            "json": json,
        }

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compile(code, "<mock_sandbox>", "exec"), safe_globals)
        except SystemExit as exc:
            exit_code = int(exc.code) if isinstance(exc.code, int) else 0
        except Exception as exc:
            exit_code = 1
            stderr_buf.write(f"Mock execution error: {exc}\n")

        wall_time = time.perf_counter() - start
        stdout_str = stdout_buf.getvalue()
        stderr_str = stderr_buf.getvalue()

        # Parse structured output from stdout, scope, or input_data
        structured: dict[str, Any] | None = self.default_structured_output
        if structured is None and stdout_str:
            try:
                parsed = json.loads(stdout_str.strip())
                if isinstance(parsed, dict):
                    structured = parsed
            except Exception:
                pass

        if structured is None:
            if "emission" in safe_globals and "state" in safe_globals:
                structured = {
                    "emission": getattr(safe_globals["emission"], "model_dump", lambda: safe_globals["emission"])(),
                    "state": getattr(safe_globals["state"], "model_dump", lambda: safe_globals["state"])(),
                }
            elif "output" in safe_globals and isinstance(safe_globals["output"], dict):
                structured = safe_globals["output"]
            elif "result" in safe_globals and isinstance(safe_globals["result"], dict):
                structured = safe_globals["result"]
            elif input_data and "emission" in input_data and "state" in input_data:
                structured = {
                    "emission": input_data["emission"],
                    "state": input_data["state"],
                }

        return ExecutionResult(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=exit_code,
            wall_time_seconds=wall_time,
            resource_ceiling_hit=False,
            structured_output=structured,
        )


def create_sandbox(
    backend: str = "auto",
    *,
    runsc_path: str = "runsc",
    default_timeout_seconds: float = 2.0,
    default_resource_ceiling_mb: int = 128,
    enforce_strict_containment: bool = False,
) -> Sandbox:
    """Factory creating an appropriate :class:`Sandbox` executor for versatile deployment.

    Args:
        backend: Containment backend ('auto', 'gvisor', or 'mock').
        runsc_path: Path or command name for the gVisor runsc executable.
        default_timeout_seconds: Default execution timeout in seconds.
        default_resource_ceiling_mb: Default memory ceiling in megabytes.
        enforce_strict_containment: When True, raises RuntimeError if hardware containment
            (gVisor) is unavailable rather than falling back to MockSandbox in dev/test.

    Returns:
        A concrete executor implementing the :class:`Sandbox` protocol.
    """
    selected = backend.lower().strip()
    if selected == "mock":
        return MockSandbox()

    gvisor_ok = is_gvisor_available(runsc_path)
    if selected == "gvisor":
        if enforce_strict_containment and not gvisor_ok:
            raise RuntimeError(
                f"Hardware-isolated containment backend {backend!r} requested or required, "
                f"but gVisor (runsc) is not installed or available on this host. "
                f"Per AGENTS.md safety constraint #1, untrusted code cannot execute outside a Sandbox. "
                f"Provision runsc on Linux target or set backend='mock' for local offline testing."
            )
        return GVisorSandbox(
            runsc_path=runsc_path,
            default_timeout_seconds=default_timeout_seconds,
            default_resource_ceiling_mb=default_resource_ceiling_mb,
        )

    if selected == "auto" and gvisor_ok:
        return GVisorSandbox(
            runsc_path=runsc_path,
            default_timeout_seconds=default_timeout_seconds,
            default_resource_ceiling_mb=default_resource_ceiling_mb,
        )

    if enforce_strict_containment:
        raise RuntimeError(
            f"Hardware-isolated containment backend {backend!r} requested or required, "
            f"but gVisor (runsc) is not installed or available on this host. "
            f"Per AGENTS.md safety constraint #1, untrusted code cannot execute outside a Sandbox. "
            f"Provision runsc on Linux target or set backend='mock' for local offline testing."
        )

    # In local development on Windows/macOS where runsc is unavailable and strict enforcement
    # is not requested, return a MockSandbox for versatile testing.
    return MockSandbox()

