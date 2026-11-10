#!/usr/bin/env bash
set -euo pipefail

echo "==> ruff check"
uv run --extra cpu ruff check .

echo "==> mypy"
uv run --extra cpu mypy .

echo "==> pytest"
uv run --extra cpu pytest --cov=src --cov-report=term-missing

echo "==> all checks passed"
