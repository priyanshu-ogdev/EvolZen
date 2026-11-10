# Changelog

## Phase 0 — Baseline finalized

**Added:**
- [`docs/research/design-evolution.md`](docs/research/design-evolution.md) — the complete
  "was -> became -> why -> how it got better" log for every mechanism that changed across this
  project's three research-design revisions (original blueprint -> PRD rescoping -> SOTA
  integration pass), reorganized by subsystem instead of the original two-segment framing, with
  every claim still tied to its citation.
- [`docs/research/landscape.md`](docs/research/landscape.md) — the full comparative landscape
  with the specific figures behind every major design decision (30.16% frontier baseline on the
  blind ARC-AGI-3 evaluation, the 30.2%->96%+ public/private-set gap, 15-32% continual-learning
  degradation without mitigation, etc.) — previously only present in condensed form in the
  literature review.
- [`docs/PAPER.md`](docs/PAPER.md) — a research-paper outline mapping this repository's content
  onto actual paper sections (Introduction, Related Work, Method, Evaluation, Limitations),
  with each section pointing at exactly what existing doc it draws from and what it's still
  waiting on measured results for.
- `docs/README.md` and `mkdocs.yml` updated to surface all three new documents.

**Status:** this is the finalized Phase 0 baseline. The engineering scaffold (one package, nine
named subsystems, shared foundation, path-filtered CI, devcontainer) is complete; the research
documentation (PRD, architecture, per-phase specs, full design-evolution history, comparative
landscape, and a paper outline) is complete and cross-linked. Implementation begins at Phase
1.1, starting with the environment-domain decision documented as the first open item in
`docs/PRD.md` §4 (NG4) and `docs/ARCHITECTURE.md`'s subsystem section for `evolzen.environment`.

## Earlier history

- **Unified single-package restructure:** collapsed an earlier three-package split
  (`evolzen-core` / `evolzen-world` / `evolzen-observer`, and before that `evolzen-segment1` /
  `evolzen-segment2`) into one package, `evolzen`, with nine subsystem folders named for what
  they do. See [ADR 0001](docs/adr/0001-single-package-not-workspace.md) and
  [ADR 0003](docs/adr/0003-nine-subsystems-not-two-packages.md).
- **Dependency-stack review:** added `evolzen.tracking`, YAML-loading `evolzen.config`,
  structured-decoding agent inference (`outlines`), FAISS-backed recognition routing,
  Ray/PettingZoo in the agent population; split heavy GPU-only packages into an optional
  extra. See [ADR 0002](docs/adr/0002-dependency-stack-and-optional-extras.md).
- **Requirements, architecture, and CI/CD documentation pass:** added the PRD, the full
  architecture document, `AGENTS.md`, path-filtered CI, dependabot, the devcontainer, and a
  `README.md` in every major folder.
- **Initial scaffold:** typed module stubs, shared schemas, CI, docs skeleton.
