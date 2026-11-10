.PHONY: setup setup-gpu lint format test typecheck check docs clean

setup:       ## Install uv (if missing) and sync CPU + development deps
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	uv sync --extra cpu
	uv run pre-commit install

setup-gpu:   ## Also pull GPU-only extras — run on the actual rig only
	uv sync --extra gpu

lint:        ## Ruff lint (no fixes)
	uv run ruff check .

format:      ## Ruff format + autofix
	uv run ruff check . --fix
	uv run ruff format .

typecheck:   ## mypy, strict
	uv run mypy src

test:        ## pytest with coverage
	uv run pytest --cov=src --cov-report=term-missing

docs:        ## Serve the mkdocs site locally
	uv run --group docs mkdocs serve

check: lint typecheck test  ## everything CI runs

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov site
	find . -type d -name __pycache__ -exec rm -rf {} +
