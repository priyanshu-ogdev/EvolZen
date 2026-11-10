# Phase 0 — The Foreground

**Historical scaffold description.** The current repository additionally contains the
[developmental numerical agent core](subsystems/agents/engineering.md). That increment is not
a trained neural model or completed population experiment. The checklist below records earlier
scaffold goals; it is not fresh evidence that installation, CI or the full suite passes here.

## What Phase 0 is

Every research phase (1.1 through 2.4-2.5) assumes a working, documented, dependency-locked
codebase to build inside. Phase 0 produces that codebase. It sits in front of the numbered
research phases — hence "foreground" — and is intentionally free of research content: no
trained models, no environment logic, no agent behavior.

## What "done" means for Phase 0

- [x] One `pyproject.toml`, one package (`evolzen`), one lockfile — no workspace, no artificial
      multi-package split (see [ADR 0001](adr/0001-single-package-not-workspace.md)).
- [x] Nine subsystem folders under `src/evolzen/`, named exactly what the PRD calls them, each
      with its own `README.md` explaining what belongs there, its success metric, and how to
      build it.
- [x] Shared schemas (`Transition`, `DriveVector`, `Manual`) live in `evolzen.schemas` so no
      two subsystems can silently drift onto incompatible representations of the same data.
- [x] Base dependencies install and pass tests on a CPU-only machine; GPU-only packages are an
      opt-in extra (see [ADR 0002](adr/0002-dependency-stack-and-optional-extras.md)).
- [x] `tests/` mirrors `src/evolzen/` exactly.
- [x] CI runs lint, type-check, and test on every push, path-filtered per subsystem.
- [x] `docs/` contains a complete PRD, a complete ARCHITECTURE.md, one doc per phase, ADRs, and
      a dependency-stack rationale — a 1:1 mapping between "a phase in the plan" and "a place to
      read about it and a place to implement it."

## What Phase 0 explicitly does not do

- It does not implement the persistent world engine — Phase 1.1 still owns the concrete world
  state, growth categories, replay semantics, and domain-specific action vocabulary.
- It does not pin exact dependency versions — `pyproject.toml` specifies ranges;
  `uv lock --upgrade` resolves current-stable versions periodically.
- It does not stand up the hardware-isolated sandboxing (Firecracker/gVisor) — that's
  infrastructure, not a Python dependency.
- It does not include any actual research logic. Every function either has a minimal,
  honestly-trivial implementation or raises `NotImplementedError` pointing at the phase doc
  that specifies what should replace it.

## Owning a subsystem

If you're the first to implement a stub past `NotImplementedError`:
1. Read the subsystem's `README.md` and the linked doc in `docs/phases/`.
2. Check `docs/research/literature-review.md` for the citation backing its design.
3. Replace the stub, keep the type signature stable if at all possible — other subsystems may
   already import it.
4. Add or extend the test in the matching `tests/<subsystem>/` file.
