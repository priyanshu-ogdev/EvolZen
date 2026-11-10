# CI/CD & Multi-Contributor Workflow

EvolZen is one package with nine subsystems, meant to be built by more than one person at once.
This document is the map of how CI, dependency updates, and the dev environment make that work.

## Why path-filtered CI

A change to `src/evolzen/agents/` shouldn't wait on `src/evolzen/recognition/`'s (heavier —
`faiss`, `sentence-transformers`) test run to get feedback. The workflow is maintained in the
repository's `.github/workflows/ci.yml`.
filters by subsystem, each also triggered by changes to the shared foundation
(`config.py`, `logging.py`, `tracking.py`, `schemas/`, `storage/`), since every subsystem
depends on it:

| Job trigger | Runs when these paths change |
|---|---|
| `foundation` (implicit in every subsystem below) | `config.py`, `logging.py`, `tracking.py`, `schemas/**`, `storage/**`, `pyproject.toml` |
| `environment` / `agents` / `economy` / `exploration` / `library` | foundation, or that subsystem's own folder |
| `predictor` / `containment` / `recognition` / `evaluation` | foundation, or that subsystem's own folder (`recognition` also watches `library/`, since it wraps it) |
| `docs` | `docs/**`, `mkdocs.yml`, any `README.md` |

A single `test` job runs whenever *any* subsystem's filter fires — since it's one package with
one test command (`uv sync && pytest`), there's no per-subsystem install cost to avoid, unlike
the old multi-package scaffold. The filtering's value here is skipping the whole test run
entirely on doc-only or foundation-untouched-but-irrelevant changes, and giving PR authors a
clear signal of *why* tests ran.

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

No packaged release yet — this is Phase 0. Tag milestones (`git tag phase-1.1-complete`) rather
than bumping the package version for research progress; the version in `pyproject.toml` tracks
this scaffold's own revisions (see `CHANGELOG.md`).
