# CI/CD & Multi-Contributor Workflow

EvolZen is one package with nine subsystems, meant to be built by more than one person at once.
This document is the map of how CI, dependency updates, and the dev environment make that work.

## Why path-filtered CI

A change to `src/evolzen/agents/` shouldn't wait on `src/evolzen/recognition/`'s (heavier —
`faiss`, `sentence-transformers`) test run to get feedback. The workflow in
`.github/workflows/ci.yml` filters by subsystem, each also triggered by changes to the shared
foundation (`config.py`, `logging.py`, `tracking.py`, `schemas/`, `storage/`, `pyproject.toml`),
since every subsystem depends on it:

| Job trigger | Runs when these paths change |
|---|---|
| `foundation` (implicit in every subsystem below) | `src/evolzen/config.py`, `src/evolzen/logging.py`, `src/evolzen/tracking.py`, `src/evolzen/schemas/**`, `src/evolzen/storage/**`, `pyproject.toml` |
| `environment` / `agents` / `economy` / `exploration` / `library` | `foundation`, or `src/evolzen/<subsystem>/**`, or `tests/<subsystem>/**` |
| `predictor` / `containment` / `evaluation` | `foundation`, or `src/evolzen/<subsystem>/**`, or `tests/<subsystem>/**` |
| `recognition` | `foundation`, `src/evolzen/recognition/**`, `src/evolzen/library/**` (which it wraps), or `tests/recognition/**` |
| `docs` | `docs/**`, `mkdocs.yml`, `**/README.md` |

A single `test` job (`uv sync --extra cpu` and `uv run --extra cpu pytest --cov=src --cov-report=xml`
across Python 3.11 and 3.12) runs whenever *any* subsystem's filter or `foundation` fires — since
it's one package with one test command, there's no per-subsystem install cost to avoid, unlike the
old multi-package scaffold. The filtering's value here is skipping the whole test run on doc-only
changes, while `lint-and-typecheck` (`ruff check .` and `mypy .`) still runs unconditionally on
every push and pull request.

> **Known path-filter gap in `.github/workflows/ci.yml`:** `configs/**` and `src/evolzen/cli/**`
> are not currently included in `foundation` or any subsystem filter, so PRs modifying only YAML
> configs or CLI code run `lint-and-typecheck` but skip the `test` job until those paths are added
> to `ci.yml`.

## Branch protection (configure once, in repo settings)

Recommended: require `lint-and-typecheck` and `test` to pass before merge; require review;
require branches up to date with `main` before merge (matters given `uv.lock` is one shared
file).

## Dependabot

`.github/dependabot.yml` opens weekly PRs for dependency and
GitHub Actions updates.

## `uv.lock` conflicts

One file at the repo root. Two people adding different dependencies in parallel will conflict
there. Resolution: whoever merges second runs `uv lock` (not `--upgrade`) to regenerate cleanly
against both changes, then commits the regenerated file. Never hand-resolve conflict markers
inside it.

## Docs deployment

The `docs` job builds the mkdocs site on every docs-touching PR (catches broken nav/links
early) and deploys to GitHub Pages only on pushes to `main`. The workflow definition is in the
repository's `.github/workflows/ci.yml`.

## Dev environment parity

`.devcontainer/` gives every contributor and reviewer the same base image
without local setup beyond "reopen in container."

## Release process

No packaged release yet — Phase 0 scaffold + Phase 1.1/1.5 baselines implemented (plus the
Phase 1.2 numerical agent core); pre-release. Tag milestones (`git tag phase-1.1-complete`) rather
than bumping the package version for research progress; the version in `pyproject.toml` tracks
repository revisions (see `CHANGELOG.md`).
