# EvolZen Docs

- [`PRD.md`](PRD.md) — what and why: requirements, goals, non-goals, risks, team structure.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — how: the complete system design, all nine subsystems.
- [`subsystems/README.md`](subsystems/README.md) — folders mirroring all nine subsystem owners.
  Start with [developmental agents](subsystems/agents/README.md) for birth equations, seven sins
  plus Null, lifecycle, learning, teaching, evolution, evaluation and delivery status.
- [`PAPER.md`](PAPER.md) — the research-paper outline: how the material in this repo maps onto
  an actual paper's sections, and what's still waiting on measured results.
- [`phase-0-foreground.md`](phase-0-foreground.md) — what Phase 0 (this repository) is and
  what "done" looks like for it.
- [`dependency-stack.md`](dependency-stack.md) — every dependency, why it's here, base vs.
  `gpu`-extra.
- [`ci-cd.md`](ci-cd.md) — path-filtered CI, dependabot, the devcontainer, multi-contributor
  workflow.
- [`phases/`](phases/1.1-environment.md) — one doc per phase (1.1 through 2.4-2.5): goal, what you build, success
  metric, citations, and explicit untested assumptions.
- [`research/`](research/README.md) — the research backing this design:
  - [`literature-review.md`](research/literature-review.md) — the six threads, condensed,
    mapped to subsystems.
  - [`landscape.md`](research/landscape.md) — the comparative landscape, dated benchmark notes,
    and source-status cautions behind the major design decisions.
  - [`design-evolution.md`](research/design-evolution.md) — the complete "was -> became -> why
    -> how it got better" log for every mechanism that changed across this project's revisions,
    organized by subsystem.
  - [`design-audit.md`](research/design-audit.md) — the audit and verdict for the supplied
    blueprints against the repository and the persistent-world goal.
  - [`docs-and-codebase-audit.md`](research/docs-and-codebase-audit.md) — full `docs/` link/nav
    validation, IEEE/ML citation coverage, and doc-to-codebase progress match.
  - [`objectives-and-evaluation.md`](research/objectives-and-evaluation.md) — the research
    objectives, hypotheses, baselines, evaluation standards, and decision gates.
  - [`references.bib`](research/references.bib) — full BibTeX citation list.
- [`adr/`](adr/README.md) — Architecture Decision Records: why specific, non-obvious choices were made.
- [`api/`](api/README.md) — auto-generated API reference (`mkdocstrings`), pulled directly from
  docstrings in `src/evolzen/`.

Note: `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `CHANGELOG.md` live at the repository
root by convention (`AGENTS.md` in particular is only recognized by AI coding tools at that
exact path) and are read directly on GitHub, not through this docs site.

Every phase doc follows the same shape: **Goal -> What you build -> Success metric -> Citations ->
See also.** If a design choice doesn't trace to either a citation or an explicit
"this is untested, flag it" note, that's a bug in the documentation.

Build/browse this site locally with `uv run --group docs mkdocs serve` from the repo root.
