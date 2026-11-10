# EvolZen

**A Grounded, Evolutionarily-Diverse, Continually-Learning Multi-Agent Sandbox**

Concept-research testbed for measuring persistent world growth and fresh-world adaptation — not an
AGI, emotional-intelligence, or real-human-simulation claim. **Start here:** [`docs/PRD.md`](docs/PRD.md) (what and why) ->
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (how) -> the subsystem READMEs below (where in
the code). If you're an AI coding agent, read [`AGENTS.md`](AGENTS.md) first.

This repository is a **research scaffold with an initial developmental-agent numerical core**.
It contains no trained models or completed research results. Many world/learning interfaces remain
stubs; `agents/development/` now implements birth equations, lifecycle, feedback learning,
living-parent teaching and a bounded archive. Full social-world, population and neural integration
remain pending.

**Start agent development here:** [seven sins + Null design](docs/subsystems/agents/README.md),
[implementation map](docs/subsystems/agents/engineering.md), and
[evaluation controls](docs/subsystems/agents/evaluation.md).

---

## One project, one package, nine subsystems

EvolZen is **one Python package** (`evolzen`, one `pyproject.toml`, one `uv sync`) — not
several packages bolted together. Inside it, the pipeline your research design actually
describes is organized into nine subsystem folders, plus a shared foundation every one of them
depends on:

```
src/evolzen/
├── config.py, logging.py, tracking.py, schemas/, storage/   # shared foundation
├── environment/     # Phase 1.1 — persistent, event-sourced social sandbox
├── agents/          # Phase 1.2 — typed heterogeneous population + QD archive
├── economy/         # Phase 1.3 — resources, institutions, manuals, provenance
├── exploration/      # Phase 1.4 — actor / synthesizer / verifier hypothesis loop
├── library/          # Phase 1.5 — immutable, versioned verified rules/capabilities
├── predictor/         # Phase 2.1 — grounded prediction + continual-learning metrics
├── containment/       # Phase 2.2 — promotion checks + fail-closed sandboxing
├── recognition/       # Phase 2.3 — proposed JEPA/wake-sleep ablations
├── evaluation/        # Phase 2.4-2.5 — persistent-world + fresh-world reporting
└── cli/               # `evolzen run / train / evaluate`
```

The nine subsystems jointly maintain a persistent, replayable world and measure learning from it.
Transition data is mechanistically verifiable; it is not called causal merely because it can be
replayed. Every subsystem has its own `README.md` — see
the table below.

```
[environment] -> [agents] -> [economy] -> [exploration] -> [library]
                                                                 |
                              verified transitions + rule library + manuals
                                                                 |
                                                                 v
     [predictor] -> [containment] -> [recognition] -> [evaluation]
```

## Subsystems

| Subsystem | Phase | What it does | Docs |
|---|---|---|---|
| [`environment/`](src/evolzen/environment/README.md) | 1.1 | Persistent, event-sourced social sandbox with replayable typed transitions. | [`docs/phases/1.1-environment.md`](docs/phases/1.1-environment.md) |
| [`agents/`](src/evolzen/agents/README.md) | 1.2 | Typed heterogeneous agents, drive vectors, QD selection, lineage/diversity metrics. | [`docs/phases/1.2-agents.md`](docs/phases/1.2-agents.md) |
| [`economy/`](src/evolzen/economy/README.md) | 1.3 | Resources, institutions, specialization, provenance-tracked manuals and floor. | [`docs/phases/1.3-economy.md`](docs/phases/1.3-economy.md) |
| [`exploration/`](src/evolzen/exploration/README.md) | 1.4 | Sandboxed actor/synthesizer/verifier with replay and interventions. | [`docs/phases/1.4-exploration.md`](docs/phases/1.4-exploration.md) |
| [`library/`](src/evolzen/library/README.md) | 1.5 | Immutable, context-aware, versioned verified rules/capabilities. | [`docs/phases/1.5-library.md`](docs/phases/1.5-library.md) |
| [`predictor/`](src/evolzen/predictor/README.md) | 2.1 | Prediction baseline, optional planning, rehearsal, transfer/forgetting metrics. | [`docs/phases/2.1-predictor.md`](docs/phases/2.1-predictor.md) |
| [`containment/`](src/evolzen/containment/README.md) | 2.2 | Replay/intervention promotion checks and fail-closed sandbox interface. | [`docs/phases/2.2-containment.md`](docs/phases/2.2-containment.md) |
| [`recognition/`](src/evolzen/recognition/README.md) | 2.3 | Proposed JEPA/wake-sleep variants with baseline-first ablations. | [`docs/phases/2.3-recognition.md`](docs/phases/2.3-recognition.md) |
| [`evaluation/`](src/evolzen/evaluation/README.md) | 2.4-2.5 | Persistent-world growth plus fresh-world EAE testing and reporting. | [`docs/phases/2.4-2.5-evaluation.md`](docs/phases/2.4-2.5-evaluation.md) |

Shared foundation (`config.py`, `logging.py`, `tracking.py`, `schemas/`, `storage/`) has its own
[`src/evolzen/README.md`](src/evolzen/README.md).

## Repository layout

```
evolzen/
├── README.md, AGENTS.md, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md
├── pyproject.toml              # one package, one dependency set, one lockfile
├── src/evolzen/                # the package — see table above
├── tests/                      # mirrors src/evolzen/ structure exactly
├── docs/                       # PRD, ARCHITECTURE, per-phase docs, ADRs, dependency stack, API reference
│   ├── PRD.md, ARCHITECTURE.md
│   └── phases/                 # one doc per phase, 1.1 through 2.5
├── configs/                    # YAML run configs, one file per subsystem
├── scripts/                    # dev/bootstrap scripts
├── .devcontainer/               # reproducible dev environment
└── .github/                    # CI (path-filtered), dependabot, PR/issue templates, CODEOWNERS
```

## Quickstart with Conda (CPU-first)

The supported local setup is Python 3.12 in a Conda environment named `evol`:

```powershell
conda create -n evol python=3.12 pip -y
conda run -n evol python -m pip install --upgrade pip
conda run -n evol python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5"
conda run -n evol python -m pip install -e ".[dev,docs,tracking]"
conda run -n evol python -m ruff check .
conda run -n evol python -m mypy .
conda run -n evol python -m pytest -q
```

Use `conda activate evol` for interactive work. This installs the CPU PyTorch wheel explicitly;
the future CUDA machine should use the separate `gpu` profile documented in
[`docs/dependency-stack.md`](docs/dependency-stack.md). Do not install both profiles in one
environment.

## Quickstart with uv

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management — **one package,
one lockfile**, no workspace complexity. Supported Python range (`>=3.11,<3.13`) is
intentionally conservative — see [ADR 0002](docs/adr/0002-dependency-stack-and-optional-extras.md).

```bash
# 1. Install uv (one-time) — or just use .devcontainer/ instead
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Resolve + lock + install (CPU-friendly base deps only)
uv sync --extra cpu

# 3. On the actual AGX Spark / DGX Spark / A6000 rig, also pull the GPU-only extras
uv sync --extra gpu

# 4. Verify
uv run pytest

# 5. Lint / type-check
uv run ruff check .
uv run mypy src

# 6. Docs site (PRD, architecture, per-phase docs, auto-generated API reference)
uv run --group docs mkdocs serve

# 7. Pipeline commands (world/training/evaluation implementations are still in development)
uv run evolzen run        # environment + agents loop
uv run evolzen train      # predictor / recognition-model training
uv run evolzen evaluate   # held-out generalization testing
```

`scripts/bootstrap.sh` wraps steps 1-4. `make setup`, `make lint`, `make test`, `make docs` wrap
the equivalent day-to-day commands — see the [`Makefile`](Makefile). CPU-first Conda setup and
future CUDA selection are documented in [`docs/dependency-stack.md`](docs/dependency-stack.md).

## Hardware topology this scaffold assumes

| Device | Role |
|---|---|
| AGX Spark | Active-agent inference and population orchestration after the capacity pilot. |
| DGX Spark | Persistent world state/logging, economy, exploration, library, routing, and sandbox coordination. |
| A6000 | Predictor/recognition training, replay maintenance, and capacity-pilot measurements. |

Nothing in the code hard-codes device placement — `evolzen.config` exposes a `device` setting.
The topology is a hypothesis until memory, throughput, world-tick, storage, and sandbox-density
measurements are recorded on the actual rig.

## Where to go next

| I want to... | Read |
|---|---|
| Understand what this project is trying to prove, and why | [`docs/PRD.md`](docs/PRD.md) |
| Understand the full system design | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Understand the research objectives and evaluation standard | [`docs/research/objectives-and-evaluation.md`](docs/research/objectives-and-evaluation.md) |
| Have an AI coding agent work in this repo correctly | [`AGENTS.md`](AGENTS.md) |
| Implement a specific subsystem | Its `README.md` (table above), then its `docs/phases/*.md` |
| Add or change a dependency | [`docs/dependency-stack.md`](docs/dependency-stack.md) |
| Understand CI/CD and parallel, multi-contributor work | [`docs/ci-cd.md`](docs/ci-cd.md) |
| Understand the containment/security model | [`SECURITY.md`](SECURITY.md) |
| See what changed release over release | [`CHANGELOG.md`](CHANGELOG.md) |

## Status

**Scaffold plus numerical agent baseline.** Implemented primitives are not evidence of conscious
thought, neural self-training or successful world evolution. Current versus planned behavior is
listed in [agent engineering](docs/subsystems/agents/engineering.md); no research gate is met
without a recorded measurement.
