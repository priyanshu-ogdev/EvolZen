"""Test fixtures and mock sandbox for Phase 2.2 Containment testing."""
from __future__ import annotations

import pytest

from evolzen.containment.sandbox import MockSandbox


@pytest.fixture
def mock_sandbox() -> MockSandbox:
    """Fixture providing a clean MockSandbox instance."""
    return MockSandbox()
