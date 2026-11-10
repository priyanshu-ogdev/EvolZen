# ADR 0002: Conservative Python range; heavy GPU deps as optional extras, not base deps

**Status:** Accepted

## Context

Packages like `vllm`, `deepspeed`, `bitsandbytes`, and `flash-attn` require CUDA and, in
several cases, a specific Linux + GPU-architecture combination. Declaring them as base
dependencies would break `uv sync` for anyone doing schema, logic, or documentation work on a
CPU-only laptop — exactly the kind of contributor this project most wants to make it easy for.
Separately, Ray, vLLM, and DeepSpeed's CUDA-extension builds have historically lagged new
CPython minor releases by two to four months. Targeting the newest CPython release ("latest
stable Python") is a different, and for this project less useful, goal than targeting the
newest *ecosystem-compatible* stack ("latest stable AI/ML libraries").

## Decision

- Supported Python range: `>=3.11,<3.13`, with `3.12` pinned in `.python-version`.
- Every heavy, GPU-and-platform-specific package (`vllm`, `deepspeed`, `bitsandbytes`,
  `flash-attn`, `faiss-gpu-cu12`) lives in `[project.optional-dependencies] gpu`, never the base
  dependency list.

## Consequences

- `uv sync` succeeds on any contributor's laptop and is sufficient for all schema, logic, and
  test work.
- `uv sync --extra gpu` is the one additional command the actual AGX Spark / DGX Spark / A6000
  rig runs.
- Bumping the Python range when the ecosystem catches up is a deliberate, reviewed decision
  (edit `pyproject.toml`'s `requires-python`), not a silent side effect of `uv lock --upgrade`.
