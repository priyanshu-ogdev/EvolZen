# Architecture Decision Records

Short, dated notes on *why* a specific, non-obvious design choice was made — so the reasoning
survives past whoever made it.

## When to write one

Write an ADR when a decision would be genuinely surprising to a newcomer, was a close call
between two reasonable options, or is expensive to reverse once other code depends on it.

## Format

**Status** (Accepted / Superseded by NNNN), **Context** (the problem, stated neutrally),
**Decision** (what was chosen), **Consequences** (what this makes easier, harder, or newly
possible).

## Index

- [0001 — Why one package, not a multi-package workspace](0001-single-package-not-workspace.md)
- [0002 — Dependency stack and optional extras](0002-dependency-stack-and-optional-extras.md)
- [0003 — Nine subsystems, not two packages](0003-nine-subsystems-not-two-packages.md)
- [0004 — Persistent growing world with bounded extensibility](0004-persistent-growing-world.md)
- [0005 — Transition semantics and dual-track evaluation](0005-transition-semantics-and-dual-track-evaluation.md)
- [0006 — Developmental eight-drive agents](0006-developmental-eight-drive-agents.md)
- [0007 — DuckDB append-only rule store and JSONL audit log for library](0007-library-persistence.md)
