#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing uv (skips if already installed)"
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

echo "==> Syncing CPU profile and development dependencies"
uv sync --extra cpu

if [[ "${EVOLZEN_INSTALL_GPU_EXTRAS:-0}" == "1" ]]; then
  echo "==> EVOLZEN_INSTALL_GPU_EXTRAS=1: also syncing GPU-only extras"
  uv sync --extra gpu
else
  echo "==> Skipping GPU extras (set EVOLZEN_INSTALL_GPU_EXTRAS=1 on the actual rig to install them)"
fi

echo "==> Installing pre-commit hooks"
uv run pre-commit install

echo "==> Running the test suite"
uv run pytest

echo "==> Done. See README.md for next steps."
