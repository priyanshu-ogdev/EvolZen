"""Tests for Phase 2.2 hardware-isolated execution interface and gVisor driver."""
from __future__ import annotations

import json
import subprocess
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from evolzen.containment.sandbox import (
    ExecutionResult,
    GVisorSandbox,
    Sandbox,
    is_gvisor_available,
)
from tests.containment.conftest import MockSandbox

# ---------------------------------------------------------------------------
# ExecutionResult tests
# ---------------------------------------------------------------------------

def test_execution_result_fields_and_immutability() -> None:
    res = ExecutionResult(
        stdout="hello\n",
        stderr="",
        exit_code=0,
        wall_time_seconds=0.042,
        resource_ceiling_hit=False,
        structured_output={"key": "val"},
    )
    assert res.stdout == "hello\n"
    assert res.stderr == ""
    assert res.exit_code == 0
    assert res.wall_time_seconds == 0.042
    assert res.resource_ceiling_hit is False
    assert res.structured_output == {"key": "val"}

    with pytest.raises(FrozenInstanceError):
        # ExecutionResult is frozen per ADR and specification
        res.exit_code = 1  # type: ignore[misc]


def test_execution_result_is_success() -> None:
    success = ExecutionResult("out", "", 0, 0.1, False)
    assert success.is_success is True

    failed_exit = ExecutionResult("", "err", 1, 0.1, False)
    assert failed_exit.is_success is False

    oom_exit = ExecutionResult("", "OOM", 0, 0.1, True)
    assert oom_exit.is_success is False

    both_failed = ExecutionResult("", "err", 137, 0.1, True)
    assert both_failed.is_success is False


def test_execution_result_get_json_output() -> None:
    # 1. Pre-populated structured output takes priority
    res_structured = ExecutionResult(
        stdout="ignore me",
        stderr="",
        exit_code=0,
        wall_time_seconds=0.01,
        resource_ceiling_hit=False,
        structured_output={"source": "structured"},
    )
    assert res_structured.get_json_output() == {"source": "structured"}

    # 2. Parsed directly from stdout
    payload = {"emission": {"data": {"val": 1}}, "state": {"data": {}}}
    res_stdout = ExecutionResult(
        stdout=json.dumps(payload),
        stderr="",
        exit_code=0,
        wall_time_seconds=0.01,
        resource_ceiling_hit=False,
    )
    assert res_stdout.get_json_output() == payload

    # 3. Parsed from last JSON line among log output
    multiline = "DEBUG: startup\nINFO: running\n" + json.dumps({"result": 42})
    res_multiline = ExecutionResult(
        stdout=multiline,
        stderr="",
        exit_code=0,
        wall_time_seconds=0.01,
        resource_ceiling_hit=False,
    )
    assert res_multiline.get_json_output() == {"result": 42}

    # 4. Empty or invalid JSON yields None
    res_empty = ExecutionResult("", "", 0, 0.01, False)
    assert res_empty.get_json_output() is None

    res_invalid = ExecutionResult("not json at all", "", 0, 0.01, False)
    assert res_invalid.get_json_output() is None

    # Line starting with { and ending with } but invalid JSON inside
    res_broken_brackets = ExecutionResult("header\n{invalid: json: here}\nfooter", "", 0, 0.01, False)
    assert res_broken_brackets.get_json_output() is None

    # 5. Non-dict JSON yields None
    res_array = ExecutionResult("[1, 2, 3]", "", 0, 0.01, False)
    assert res_array.get_json_output() is None


# ---------------------------------------------------------------------------
# Sandbox protocol conformance
# ---------------------------------------------------------------------------

def test_sandbox_protocol_conformance(mock_sandbox: MockSandbox) -> None:
    assert isinstance(mock_sandbox, Sandbox)
    assert isinstance(GVisorSandbox(), Sandbox)

    class NonSandbox:
        pass

    assert not isinstance(NonSandbox(), Sandbox)


# ---------------------------------------------------------------------------
# is_gvisor_available tests
# ---------------------------------------------------------------------------

def test_is_gvisor_available_nonexistent() -> None:
    assert is_gvisor_available("nonexistent_runsc_binary_xyz_12345") is False


def test_is_gvisor_available_probed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test True when runsc returns 0
    monkeypatch.setattr(
        "shutil.which", lambda cmd: "/usr/bin/runsc" if cmd == "runsc" else None
    )
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(["runsc", "--version"], 0, stdout="runsc version 2026"))
    monkeypatch.setattr("subprocess.run", mock_run)
    assert is_gvisor_available("runsc") is True

    # Test False when runsc returns non-zero
    mock_run.return_value = subprocess.CompletedProcess(["runsc", "--version"], 1, stderr="error")
    assert is_gvisor_available("runsc") is False

    # Test False when subprocess raises OSError
    mock_run.side_effect = OSError("executable not found")
    assert is_gvisor_available("runsc") is False


# ---------------------------------------------------------------------------
# GVisorSandbox initialization & security flags
# ---------------------------------------------------------------------------

def test_gvisor_sandbox_initialization() -> None:
    default_box = GVisorSandbox()
    assert default_box.runsc_path == "runsc"
    assert default_box.default_timeout_seconds == 2.0
    assert default_box.default_resource_ceiling_mb == 128

    custom_box = GVisorSandbox(
        runsc_path="/usr/local/bin/runsc",
        default_timeout_seconds=5.0,
        default_resource_ceiling_mb=256,
    )
    assert custom_box.runsc_path == "/usr/local/bin/runsc"
    assert custom_box.default_timeout_seconds == 5.0
    assert custom_box.default_resource_ceiling_mb == 256


def test_gvisor_sandbox_security_flags_and_command() -> None:
    sandbox = GVisorSandbox(runsc_path="runsc")
    cmd = sandbox.build_command(
        "x = 1",
        resource_ceiling_mb=64,
        input_data={"param": "test"},
    )

    # Security check: must invoke runsc with --net=none
    assert cmd[0] == "runsc"
    assert "--net=none" in cmd
    assert "do" in cmd
    assert "python3" in cmd
    assert "-c" in cmd

    script = cmd[-1]
    # Enforces memory ceiling via setrlimit
    assert "64 * 1024 * 1024" in script
    assert "resource.RLIMIT_AS" in script
    assert 'param": "test"' in script


def test_gvisor_sandbox_fail_closed_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": False)
    sandbox = GVisorSandbox(runsc_path="runsc")

    with pytest.raises(RuntimeError, match="gVisor \\(runsc\\) is not installed or available"):
        sandbox.run("print('untrusted')")


def test_gvisor_sandbox_mocked_execution_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": True)
    sandbox = GVisorSandbox(runsc_path="runsc")

    mock_proc = subprocess.CompletedProcess(
        args=["runsc", "do"],
        returncode=0,
        stdout=json.dumps({"emission": {"val": 10}}),
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", MagicMock(return_value=mock_proc))

    res = sandbox.run("print('hello')", timeout_seconds=1.5, resource_ceiling_mb=128)
    assert res.is_success is True
    assert res.exit_code == 0
    assert res.structured_output == {"emission": {"val": 10}}
    assert res.resource_ceiling_hit is False

    # Plain-text non-JSON stdout
    mock_proc_text = subprocess.CompletedProcess(
        args=["runsc", "do"],
        returncode=0,
        stdout="raw plain text output",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", MagicMock(return_value=mock_proc_text))
    res_text = sandbox.run("print('raw')")
    assert res_text.is_success is True
    assert res_text.structured_output is None


def test_gvisor_sandbox_mocked_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": True)
    sandbox = GVisorSandbox(runsc_path="runsc")

    timeout_exc = subprocess.TimeoutExpired(cmd=["runsc", "do"], timeout=2.0)
    monkeypatch.setattr("subprocess.run", MagicMock(side_effect=timeout_exc))

    res = sandbox.run("while True: pass", timeout_seconds=2.0)
    assert res.exit_code == 124
    assert res.is_success is False
    assert "timed out" in res.stderr.lower()


def test_gvisor_sandbox_mocked_oom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": True)
    sandbox = GVisorSandbox(runsc_path="runsc")

    mock_proc = subprocess.CompletedProcess(
        args=["runsc", "do"],
        returncode=137,
        stdout="",
        stderr="MemoryError: Out of memory",
    )
    monkeypatch.setattr("subprocess.run", MagicMock(return_value=mock_proc))

    res = sandbox.run("big_alloc = [0] * 10**9")
    assert res.exit_code == 137
    assert res.resource_ceiling_hit is True
    assert res.is_success is False


def test_gvisor_sandbox_mocked_generic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": True)
    sandbox = GVisorSandbox(runsc_path="runsc")

    monkeypatch.setattr("subprocess.run", MagicMock(side_effect=OSError("system fault")))

    res = sandbox.run("code")
    assert res.exit_code == 1
    assert res.is_success is False
    assert "Sandbox execution error: system fault" in res.stderr


# ---------------------------------------------------------------------------
# Live gVisor test (skipped when runsc is unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not is_gvisor_available(), reason="runsc not available")
def test_gvisor_sandbox_live() -> None:
    sandbox = GVisorSandbox()
    result = sandbox.run(
        "import json; print(json.dumps({'status': 'live_gvisor_ok'}))",
        timeout_seconds=5.0,
        resource_ceiling_mb=128,
    )
    assert result.is_success is True
    assert result.get_json_output() == {"status": "live_gvisor_ok"}


# ---------------------------------------------------------------------------
# MockSandbox tests
# ---------------------------------------------------------------------------

def test_mock_sandbox_normal_execution(mock_sandbox: MockSandbox) -> None:
    code = 'print(\'{"emission": {"step": 1}, "state": {"alive": true}}\')'
    res = mock_sandbox.run(code, timeout_seconds=1.0, resource_ceiling_mb=64)

    assert res.is_success is True
    assert res.exit_code == 0
    assert res.get_json_output() == {
        "emission": {"step": 1},
        "state": {"alive": True},
    }
    assert len(mock_sandbox.call_history) == 1
    record = mock_sandbox.call_history[0]
    assert record["code"] == code
    assert record["timeout_seconds"] == 1.0
    assert record["resource_ceiling_mb"] == 64
    assert record["input_data"] is None


def test_mock_sandbox_input_data_and_scope(mock_sandbox: MockSandbox) -> None:
    input_data = {"key": 100}
    code = "output = {'doubled': input_data['key'] * 2}"
    res = mock_sandbox.run(code, input_data=input_data)

    assert res.is_success is True
    assert res.structured_output == {"doubled": 200}
    assert res.get_json_output() == {"doubled": 200}


def test_mock_sandbox_fails_closed_on_error(mock_sandbox: MockSandbox) -> None:
    code = "raise ValueError('malformed logic')"
    res = mock_sandbox.run(code)

    assert res.exit_code == 1
    assert res.is_success is False
    assert "malformed logic" in res.stderr


def test_mock_sandbox_simulate_timeout() -> None:
    sandbox = MockSandbox(simulate_timeout=True)
    res = sandbox.run("code", timeout_seconds=3.0)

    assert res.exit_code == 124
    assert res.is_success is False
    assert res.resource_ceiling_hit is False
    assert res.wall_time_seconds == 3.0
    assert "timed out after 3.0 seconds" in res.stderr


def test_mock_sandbox_simulate_oom() -> None:
    sandbox = MockSandbox(simulate_oom=True)
    res = sandbox.run("code", resource_ceiling_mb=256)

    assert res.exit_code == 137
    assert res.resource_ceiling_hit is True
    assert res.is_success is False
    assert "memory ceiling (256 MB) exceeded" in res.stderr


def test_mock_sandbox_custom_result() -> None:
    custom = ExecutionResult(
        stdout="custom_stdout",
        stderr="",
        exit_code=0,
        wall_time_seconds=0.123,
        resource_ceiling_hit=False,
        structured_output={"custom": True},
    )
    sandbox = MockSandbox(custom_result=custom)
    res = sandbox.run("any_code")

    assert res == custom
    assert res.get_json_output() == {"custom": True}
    assert len(sandbox.call_history) == 1


def test_mock_sandbox_history_and_clear(mock_sandbox: MockSandbox) -> None:
    mock_sandbox.run("code_1", timeout_seconds=1.0)
    mock_sandbox.run("code_2", timeout_seconds=2.0)
    assert len(mock_sandbox.call_history) == 2

    mock_sandbox.clear()
    assert len(mock_sandbox.call_history) == 0
