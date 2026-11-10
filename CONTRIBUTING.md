# Contributing to EvolZen

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/PRD.md`](docs/PRD.md) (especially
§12, "Parallel Workstreams"), and [`AGENTS.md`](AGENTS.md) before your first PR touches anything
outside a single subsystem's internals. `AGENTS.md` applies to human contributors too where
relevant — it's just written with an AI agent's failure modes specifically in mind.

## Before you start

1. Read the phase doc for whatever you're implementing (`docs/phases/`), and its citation(s).
2. Check [`docs/dependency-stack.md`](docs/dependency-stack.md) before adding a dependency — GPU-
   only or platform-specific packages go in `[project.optional-dependencies] gpu`, never base.
3. Keep existing public type signatures stable — other subsystems likely import them.
4. Check [`.github/CODEOWNERS`](.github/CODEOWNERS) for who else needs to weigh in.

## Local setup

```bash
./scripts/bootstrap.sh
make check
make docs
```

Or use [`.devcontainer/`](.devcontainer/) for a zero-local-setup environment identical to CI.

## Working in parallel with other contributors

See [`docs/PRD.md`](docs/PRD.md) §12 for which subsystems can be built concurrently, and
[`docs/ci-cd.md`](docs/ci-cd.md) for the mechanics:

- CI is **path-filtered per subsystem** — a PR touching only `agents/` triggers `agents`'s test
  job, not `recognition`'s (heavier) one, unless shared foundation code (`schemas/`,
  `config.py`) also changed.
- `uv.lock` is one shared file. If your PR conflicts with a merged one there, regenerate with
  `uv lock` against both changes — never hand-resolve conflict markers inside it.
- Changing `evolzen.schemas` requires checking every importer across all nine subsystems, not
  just the one you're working in.

## Branching & commits

- Branch names: `phase/<phase-number>-<short-description>`.
- [Conventional Commits](https://www.conventionalcommits.org/): `feat(agents): ...`,
  `fix(schemas): ...`, `docs(predictor): ...`.

## Pull requests

- One subsystem's worth of change per PR where reasonably possible.
- A PR changing `evolzen.schemas` must note, in the description, which downstream subsystems
  were checked against the change.
- New research-backed design decisions get an ADR, not just a code comment.
- A stub replaced with a real implementation needs a real test alongside it.
- Fill out [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) honestly.

## Code style

Enforced by `ruff` and `mypy --strict` via pre-commit and CI. Run `make format` before pushing.

## Honesty requirement

This project exists in its current, scoped form because an earlier version overclaimed. If you
notice a docstring, comment, README, or log message implying proximity to general intelligence,
an unearned success metric, or a claim not backed by a citation or an explicit "untested" flag —
treat it as a bug and file it as one.
