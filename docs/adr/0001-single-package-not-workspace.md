# ADR 0001: One package (`evolzen`), not a multi-package `uv` workspace

**Status:** Accepted

## Context

An earlier scaffolding revision split the project into a `uv` workspace with three separately
installable packages (a shared "core" package plus two more for the rest of the pipeline), on
the theory that the two halves of the research design needed independent installability and
independent hardware deployment.

In practice this added real friction without a matching benefit: three `pyproject.toml` files
to keep in sync, `[tool.uv.sources]` cross-package references, a shared lockfile that still
had to account for all three packages' dependencies together, and — the more serious problem —
a package boundary that didn't map to how the actual research design is structured. The
research design describes **nine** subsystems (Environment Engine, Agents, Economy & Knowledge
Layer, Directed Exploration, Growing Library, Grounded Predictor, Verification Gate &
Containment, Recognition Model, Evaluation & Publication), not two, and none of the
project's actual deployment needs (see `docs/ARCHITECTURE.md` §5, Hardware & Deployment)
require *installable-package* separation — device placement is handled per-subsystem by a
config field, not by which package a module lives in.

## Decision

One package, `evolzen`, one `pyproject.toml`, one `uv.lock`. Nine subsystem folders as sibling
subpackages of `src/evolzen/`. `uv sync` installs everything; `uv sync --extra gpu` adds the
GPU-only pieces. No workspace, no cross-package source references.

## Consequences

- One dependency set, one lockfile, one install command — no more coordinating changes across
  multiple `pyproject.toml` files or resolving `uv.lock` conflicts across package boundaries.
- Any subsystem can still be deployed to a specific device (see hardware topology) — that's a
  runtime config decision (`evolzen.config`'s per-subsystem `device` field), not a packaging
  decision.
- If a genuine need for independent installability emerges later (e.g., publishing one
  subsystem as a standalone library for reuse outside this project), that's a new ADR with a
  concrete justification — not a default to reach for because "two things feels neater than
  nine."
