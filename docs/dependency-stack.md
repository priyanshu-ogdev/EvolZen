# Dependency Stack — What's Here and Why

One package, one dependency set, one lockfile. Every dependency below is tied to a specific
subsystem's actual requirement — "latest stable" is resolved by `uv.lock` at sync time from the
version *ranges* in `pyproject.toml`; this table documents the *reasoning*.

## Base dependencies (install everywhere, including a CPU-only laptop)

The root `pyproject.toml` is the package authority. Torch is intentionally not in the shared
base list: choose exactly one profile, `cpu` or `gpu`, so the resolver cannot silently mix CPU
and CUDA wheels. uv supports pinning a dependency to a named package index and declaring mutually
exclusive extras; the manifest uses that mechanism for the official PyTorch indexes.

| Package | Used by | Why |
|---|---|---|
| `pydantic` / `pydantic-settings` | shared foundation | Typed, validated schemas as the cross-subsystem data contract; settings loaded from env + YAML. |
| `pyyaml` | shared foundation | Backs YAML config loading in `evolzen.config` (the `configs/` tree). |
| `loguru` | shared foundation | Structured, consistently-formatted logs across every subsystem. |
| `duckdb` | shared foundation | Embedded, zero-ops storage for the transition log — no server, fast enough for this project's environment scale. |
| `numpy` | shared foundation | Numeric plumbing (behavioral descriptors, embeddings, reward math). |
| `typer` | `cli` | The `evolzen` console command. |
| `gymnasium` | `environment` | Standard single-agent env API. |
| `pettingzoo` | `agents` | Standard **multi-agent** env API — the project's original blueprint specified Gymnasium/PettingZoo explicitly; the agent population is multi-agent from the start. |
| `transformers` | `agents`, `predictor`, `recognition` | HuggingFace model loading — the default, CPU-friendly inference/training backend. |
| `peft` | `agents`, `predictor` | LoRA adapters — parameter-efficient adaptation, never full fine-tunes of the base model. |
| `accelerate` | `agents`, `predictor`, `recognition` | Device placement and mixed precision without hand-written `.to(device)` scattered through the codebase. |
| `outlines` | `agents` | Constrains agent LLM output to valid JSON matching `evolzen.schemas.transition.Action`. |
| `ray[default]` | `agents` | Actor-model orchestration for a 10-30 agent population — the standard tool for exactly this scale of concurrent, stateful workers. |
| `trl` | `predictor` | PPO/GRPO training loop for the grounded predictor. |
| `faiss-cpu` | `recognition` | Nearest-neighbor search backing the sparse-MoE `ExpertRouter`. CPU build is base so routing logic is testable without a GPU. |
| `sentence-transformers` | `recognition` | Produces the query/library embeddings `faiss-cpu` indexes and searches. |
| `polars` | `evaluation` | Fast aggregation over evaluation-round records. |

## Compute profiles

| Profile | Install | Intended host |
|---|---|---|
| `cpu` | `uv sync --extra cpu` | Development and CPU-only Conda environment; official PyTorch CPU index |
| `gpu` | `uv sync --extra gpu` | CUDA-capable Linux host after hardware validation; official CUDA PyTorch index plus GPU-only packages |

Do not activate both profiles in one environment. `pip` does not read uv's source table, so the
Conda procedure installs the CPU torch wheel from the official PyTorch CPU index first, then
installs the project without the `cpu` extra. The source table is for uv; other installers need
their own index argument.

## Optional GPU packages (install only on GPU-equipped hardware — the actual rig)

Declared under `[project.optional-dependencies]`, never in the base list, because they require
CUDA, a specific platform, or both — a CPU-only laptop must still be able to `uv sync` and get a
working dev environment.

| Package | Used by | Why |
|---|---|---|
| `vllm` | `agents` | High-throughput batched inference for a live 10-30 agent population on the AGX Spark. |
| `bitsandbytes` | `agents` | Quantized loading of the small local agent LLMs. |
| `deepspeed` | `predictor`, `recognition` | Multi-GPU training efficiency for the A6000. |
| `flash-attn` | `recognition` | Attention-kernel speedup for the JEPA encoder and wake-sleep components — the project's most compute-heavy training loop. |
| `faiss-gpu-cu12` | `recognition` | GPU-accelerated routing once the library grows large enough that CPU search becomes the bottleneck. |

Install with `uv sync --extra gpu` on the actual rig after confirming the CUDA/Python combination.

## Dev / docs dependency groups

| Group | Package | Why |
|---|---|---|
| `dev` | `pytest`, `pytest-cov` | Test running + coverage. |
| `dev` | `hypothesis` | Property-based testing — schema and verifier invariants (e.g. "a `Transition` round-trips through JSON unchanged"). |
| `dev` | `ruff` | Lint + format, single tool for both. |
| `dev` | `mypy`, `types-PyYAML` | Strict static typing, including the YAML configuration loader. |
| `dev` | `pre-commit` | Runs the above on every commit. |
| `docs` | `mkdocs`, `mkdocs-material` | Docs site. |
| `docs` | `mkdocstrings[python]` | Turns the docstrings throughout `src/evolzen/` into browsable API reference. |

For a Conda environment that must include every runtime, development and documentation package:

```powershell
conda create -n evol python=3.12 pip -y
conda run -n evol python -m pip install --upgrade pip
conda run -n evol python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5"
conda run -n evol python -m pip install -e ".[dev,docs,tracking]"
```

The command is intentionally two-stage so the CPU wheel is selected explicitly; do not pass the
GPU extra on this machine. Future CUDA setup should use the `gpu` profile on the CUDA host rather
than copying this CPU environment. The repository remains a single installable package; no nested
agent package or second TOML manifest is introduced.
