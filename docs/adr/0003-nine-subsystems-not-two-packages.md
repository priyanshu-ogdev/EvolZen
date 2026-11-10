# ADR 0003: Nine subsystems, named for what they do — not two artificial "halves"

**Status:** Accepted

## Context

This project's naming went through two rejected iterations before landing on its current
shape, and it's worth recording both, since the failure mode is easy to accidentally
reintroduce.

**Iteration 1 — "Segment 1" / "Segment 2".** Early scaffolding split the pipeline into
"Segment 1" (environment through library) and "Segment 2" (predictor through evaluation),
mirroring the original research blueprint's own two-part structure ("Building the Universe" /
"Building the God"). The naming read as if it described two sequential *development phases*
rather than two permanent *architectural components* — a reasonable misreading, since "Segment
1" and "Segment 2" carry no information about what either segment actually does.

**Iteration 2 — "World" / "Observer" as separate installable packages.** The fix for the naming
went too far in a different direction: it replaced the numbered segments with two descriptive
names ("World," "Observer") *and* turned them into two separate installable packages
(`evolzen-world`, `evolzen-observer`), alongside a third shared "core" package. This solved the
"what does this name mean" problem but reintroduced a different one: it still implied the
system has exactly two components, when the actual research design specifies nine (Environment
Engine, Agents, Economy & Knowledge Layer, Directed Exploration, Growing Library, Grounded
Predictor, Verification Gate & Containment, Recognition Model, Evaluation & Publication). It
also added real packaging friction (see [ADR 0001](0001-single-package-not-workspace.md))
without a deployment requirement that actually needed it.

## Decision

Nine subsystem folders, one package, each named exactly what the PRD calls it:
`environment`, `agents`, `economy`, `exploration`, `library`, `predictor`, `containment`,
`recognition`, `evaluation`. No grouping label for "the first five" versus "the last four" —
where that grouping is useful to describe (data flows from the first group into the second,
via what the research documents call "the Bridge"), it's described in prose
(`docs/ARCHITECTURE.md` §1) as a data-flow fact, not encoded as a folder, a package, or a name
anything is required to use.

## Consequences

- The subsystem names carry real information — reading `src/evolzen/` top-level listing tells
  you what the system does, not just that it has two halves.
- There's nothing to "keep in sync" between a folder-level grouping and the actual nine-item
  list in the PRD, because no such grouping exists as a structural artifact.
- Future contributors proposing a return to a two-part package split should read this ADR
  first — it has been tried twice, for different reasons, and reverted twice.
