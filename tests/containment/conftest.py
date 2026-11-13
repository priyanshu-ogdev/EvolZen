"""Test fixtures and mock sandbox for Phase 2.2 Containment testing."""
from __future__ import annotations

import io
import json
import time
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

import pytest

from evolzen.containment.sandbox import ExecutionResult


class MockSandbox:
    """Deterministic mock sandbox satisfying the :class:`Sandbox` protocol.

    Provides hermetic execution for test suites without requiring gVisor / runsc or Firecracker,
    while accurately recording calls and simulating edge cases (timeouts, OOMs, and custom results).
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
                stderr=f"Execution timed out after {timeout_seconds} seconds.",
                exit_code=124,
                wall_time_seconds=timeout_seconds,
                resource_ceiling_hit=False,
                structured_output=None,
            )

        if self.simulate_oom:
            return ExecutionResult(
                stdout="",
                stderr=f"MemoryError: memory ceiling ({resource_ceiling_mb} MB) exceeded.",
                exit_code=137,
                wall_time_seconds=0.001,
                resource_ceiling_hit=True,
                structured_output=None,
            )

        if self.default_structured_output is not None:
            return ExecutionResult(
                stdout=json.dumps(self.default_structured_output),
                stderr="",
                exit_code=0,
                wall_time_seconds=0.001,
                resource_ceiling_hit=False,
                structured_output=self.default_structured_output,
            )

        # Deterministic execution of safe test code
        buffer_out = io.StringIO()
        buffer_err = io.StringIO()
        start = time.perf_counter()
        scope: dict[str, Any] = {
            "__name__": "__main__",
            "input_data": input_data,
        }
        exit_code = 0
        try:
            with redirect_stdout(buffer_out), redirect_stderr(buffer_err):
                exec(compile(code, "<mock_sandbox>", "exec"), scope)
        except Exception as exc:
            exit_code = 1
            buffer_err.write(str(exc))

        wall_time = time.perf_counter() - start
        stdout_str = buffer_out.getvalue()
        stderr_str = buffer_err.getvalue()

        # Extract structured JSON payload from stdout, scope, or input_data
        structured: dict[str, Any] | None = None
        if stdout_str:
            try:
                parsed = json.loads(stdout_str.strip())
                if isinstance(parsed, dict):
                    structured = parsed
            except Exception:
                pass

        if structured is None:
            if "emission" in scope and "state" in scope:
                structured = {
                    "emission": getattr(scope["emission"], "model_dump", lambda: scope["emission"])(),
                    "state": getattr(scope["state"], "model_dump", lambda: scope["state"])(),
                }
            elif "output" in scope and isinstance(scope["output"], dict):
                structured = scope["output"]
            elif "result" in scope and isinstance(scope["result"], dict):
                structured = scope["result"]
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


@pytest.fixture
def mock_sandbox() -> MockSandbox:
    """Fixture providing a clean MockSandbox instance."""
    return MockSandbox()
