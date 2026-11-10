# AGENTS.md

Instructions for AI coding agents (Claude Code, Codex, Copilot, Cursor, or any other agent)
working in this repository, per the cross-tool `AGENTS.md` convention. Read
[`CONTRIBUTING.md`](CONTRIBUTING.md) too (the human-oriented equivalent) — when they seem to
conflict, this file's constraints win.

## Project snapshot

EvolZen is a concept-research testbed, not a product: **one package** (`evolzen`), nine
subsystems, ten phases (1.1-1.5, 2.1-2.5). This repository is **Phase 0** — engineering scaffold
only; every module under `src/evolzen/` is a typed, documented stub. Read
[`docs/PRD.md`](docs/PRD.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before any
change beyond a single function's internals.

**Naming note, because it's easy to get wrong from stale context:** there is no "Segment 1",
"Segment 2", "World package", or "Observer package" in this repository — those were rejected
naming schemes from earlier scaffolding iterations. The real structure is nine subsystem folders
under one package, named exactly what the PRD calls them: `environment`, `agents`, `economy`,
`exploration`, `library`, `predictor`, `containment`, `recognition`, `evaluation`. If you see
"segment" or "world/observer as packages" anywhere, that's stale content to fix, not a pattern
to follow.

## Setup & build commands

```bash
uv sync                       # CPU-friendly base deps — always safe to run
uv sync --extra gpu           # + vLLM/DeepSpeed/bitsandbytes/flash-attn/faiss-gpu — GPU hardware only
uv run pytest                 # full test suite
uv run pytest tests/agents -v # one subsystem's tests
uv run ruff check .           # lint
uv run ruff check . --fix     # lint with autofix
uv run mypy src               # strict type-check
uv run --group docs mkdocs serve
```

`make check` runs lint + typecheck + test together. There is no `requirements.txt` and none
should be added — this project uses `uv` exclusively, with one lockfile for the one package.

## Repository map

| Path | What's there |
|---|---|
| `docs/PRD.md`, `docs/ARCHITECTURE.md` | What/why, and how — read first. |
| `src/evolzen/{config,logging,tracking}.py`, `src/evolzen/{schemas,storage}/` | Shared foundation every subsystem depends on. Changing anything here affects the whole pipeline — see "Safety-critical constraints" below. |
| `src/evolzen/{environment,agents,economy,exploration,library}/` | Phases 1.1-1.5 — the data-generating half of the pipeline. |
| `src/evolzen/{predictor,containment,recognition,evaluation}/` | Phases 2.1-2.5 — the learning/evaluation half of the pipeline. |
| `src/evolzen/cli/` | The `evolzen` command. No research logic belongs here. |
| `docs/phases/` | Per-phase research design docs (goal, success metric, citations) — the spec each subsystem's implementation must satisfy. |
| `docs/adr/` | Why non-obvious decisions were made. |
| `docs/dependency-stack.md` | Why every dependency is here, base vs. `gpu`-extra. |
| `docs/ci-cd.md` | How CI, dependabot, and the devcontainer support parallel, multi-contributor work. |
| `configs/` | YAML run configs, one per subsystem, consumed by `evolzen.config`. |

## Coding conventions

- Python `>=3.11,<3.13` only (see [ADR 0002](docs/adr/0002-dependency-stack-and-optional-extras.md)).
- `mypy --strict` passes on every file you touch. Full type hints, explicit return types.
- Docstrings: Google style. Any module implementing a phase's design names the phase and cites
  the source (`arXiv:...`, author/year) backing it — match the existing pattern. A new module
  with no citation and no explicit "this is untested" note is incomplete.
- New heavy or platform-specific dependency? `[project.optional-dependencies] gpu`, never the
  base list — check `docs/dependency-stack.md` first.

## Testing requirements

- `tests/` mirrors `src/evolzen/` exactly — a change to `src/evolzen/agents/qd_archive.py` has
  its test at `tests/agents/test_qd_archive.py`.
- Every stub you move past `NotImplementedError` needs a real test alongside it.
- A test depending on a `gpu`-extra package must guard with `pytest.importorskip(...)`.

## Safety-critical constraints — never violate these

1. **Never execute agent-generated or self-modified code outside
   `evolzen.containment.Sandbox`** — not even a two-line toy example. Applies to anything from
   `evolzen.exploration.synthesizer`, `evolzen.library`, or `evolzen.agents.self_modification`.
   See [`SECURITY.md`](SECURITY.md).
2. **Never hand-edit `uv.lock`.** Regenerate with `uv lock` / `uv lock --upgrade`.
3. **Never change a schema in `evolzen.schemas` without checking every importer across all nine
   subsystems** — `mypy --strict` catches type errors; check test coverage too.
4. **Never write documentation, docstrings, or commit messages implying proximity to general
   intelligence, an unearned success metric, or a claim without a citation or an explicit
   "untested" flag.** See `docs/PRD.md` §4 (Non-Goals). This project's current, scoped form
   exists specifically because an earlier version overclaimed.
5. **Never mark a phase's success metric as met without it actually being measured.**

## Documentation requirements

- New module implementing a phase: docstring covers Goal, mechanism, citation.
- New non-obvious design decision: add an ADR (`docs/adr/000N-title.md`).
- Changed a phase's scope or approach: update `docs/phases/N.N-name.md` in the same PR.

## Git / PR conventions

- Conventional Commits (`feat(agents): ...`, `fix(schemas): ...`, `docs(predictor): ...`).
- Branch names: `phase/<phase-number>-<short-description>`.
- Fill out `.github/PULL_REQUEST_TEMPLATE.md` honestly.
- CI is path-filtered per subsystem (`docs/ci-cd.md`) — a change to `agents/` doesn't trigger
  `recognition/`'s (heavier) test job unless `schemas/`, `config.py`, etc. also changed.

## When you hit a `NotImplementedError` stub

Read its docstring and the linked `docs/phases/N.N-name.md` doc first — it names what's
blocking it. Don't implement around a documented blocker with a placeholder that silently
changes the module's contract.

## If you're uncertain

Prefer asking over guessing on anything touching: a shared schema, the exact-match verification
standard, containment/sandboxing, or any claim about what the system has demonstrated.
