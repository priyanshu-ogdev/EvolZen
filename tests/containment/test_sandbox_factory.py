"""Unit tests for versatile deployment sandbox factory in Phase 2.2."""
from __future__ import annotations

import pytest

from evolzen.containment.sandbox import (
    GVisorSandbox,
    MockSandbox,
    Sandbox,
    create_sandbox,
    is_gvisor_available,
)


def test_create_sandbox_mock() -> None:
    """Verifies that create_sandbox(backend='mock') returns a functional MockSandbox."""
    box = create_sandbox(backend="mock")
    assert isinstance(box, MockSandbox)
    assert isinstance(box, Sandbox)
    res = box.run("x = 1")
    assert res.is_success is True


def test_create_sandbox_auto() -> None:
    """Verifies that create_sandbox(backend='auto') returns a valid Sandbox without crashing."""
    box = create_sandbox(backend="auto")
    assert isinstance(box, Sandbox)
    if is_gvisor_available():
        assert isinstance(box, GVisorSandbox)
    else:
        assert isinstance(box, MockSandbox)


def test_create_sandbox_strict_fail_closed_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that enforce_strict_containment raises RuntimeError if gVisor is unavailable."""
    monkeypatch.setattr("evolzen.containment.sandbox.is_gvisor_available", lambda path="runsc": False)
    with pytest.raises(RuntimeError, match="Hardware-isolated containment backend"):
        create_sandbox(backend="gvisor", enforce_strict_containment=True)
