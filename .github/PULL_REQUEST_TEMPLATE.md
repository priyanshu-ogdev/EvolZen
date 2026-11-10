## What does this PR implement?

<!-- Phase number + subsystem, e.g. "Phase 1.4: coding-agent-harness Synthesizer wrapper" -->

## Checklist

- [ ] I read the relevant phase doc under `docs/phases/` and its citation(s).
- [ ] If I added a dependency, it's in the correct place (base vs. `gpu` extra) per
      `docs/dependency-stack.md`.
- [ ] If I changed a shared schema in `evolzen.schemas`, I checked every importer across all
      nine subsystems and noted which ones below.
- [ ] I kept existing public type signatures stable, or explicitly called out the breaking
      change.
- [ ] Every replaced stub has a real test alongside it.
- [ ] `make check` passes locally.
- [ ] I did not add a docstring, comment, or log message implying proximity to general
      intelligence, an unearned success metric, or a claim without a citation or an explicit
      "untested" flag (see `CONTRIBUTING.md`, "Honesty requirement").

## Downstream subsystems checked (if a shared schema changed)

<!-- list them, or delete this section -->

## New ADR?

<!-- If this PR makes a research-backed design decision, link the new docs/adr/NNNN-*.md file -->
