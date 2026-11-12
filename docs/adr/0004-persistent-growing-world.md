# ADR 0004: Persistent growing world with bounded extensibility

**Status:** Accepted

## Context

The original blueprint used a physically simulated voxel civilization to make the world feel
open-ended. The current Phase 0 scaffold correctly removed the infeasible voxel/DEM requirement,
but its three candidate domains (negotiation, historical market replay, and code-with-tests) do not
by themselves define an independently growing game world.

The revised research goal needs a world that persists across runs, changes because of agent action
and endogenous processes, and can accumulate durable artifacts, institutions, norms, and economic
relationships. At the same time, unrestricted self-modification of the world would make replay,
containment, and evaluation impossible.

## Decision

Phase 1.1 will target a **persistent, event-sourced, discrete social sandbox** with bounded
extensibility rather than a voxel physics engine or a stateless benchmark task.

The world has six versioned entity families:

1. agents and lineages;
2. locations and resources;
3. artifacts and capabilities;
4. contracts, markets, and institutions;
5. norms, beliefs, and manuals;
6. exogenous events and environmental processes.

World growth is defined as the creation and persistence of new state within those families. New
mechanics are not arbitrary executable code: they are proposed as typed capability or rule
packages, tested in a sandbox, and admitted only after replay and intervention checks. The world
may grow within its declared extension vocabulary, but it is not described as unbounded or
unrestricted open-ended intelligence.

The first implementation will use 10–30 active cognitive agents plus optional deterministic
background population processes. “All types of people” means coverage of a declared behavioral and
social ontology (needs, drives, skills, roles, affiliations, norms, memory, and communication),
not a claim to simulate real human demographics or psychology.

## Consequences

- The project now tests world growth directly instead of inferring it from a growing rule library.
- Persistent snapshots, event logs, branching, and deterministic replay become first-class
  requirements.
- The environment is less visually rich than the original voxel concept but is buildable on the
  stated hardware and exposes clearer causal and evaluation contracts.
- The extension boundary is explicit: new world capabilities must be typed, versioned, sandboxed,
  and measurable. Unbounded mechanic invention remains out of scope.

## Implementation status

The Phase 1.1 baseline implements the six entity families, growth ledger, invariants, and bounded
`CapabilityPackage` schemas in `evolzen.schemas.world`, the deterministic engine in
`evolzen.environment.engine.SocialSandboxEngine`, DuckDB event/snapshot persistence in
`evolzen.storage.transition_log.TransitionLogStore`, and replay/intervention helpers in
`evolzen.environment.replay` and `evolzen.environment.interventions`. Open Phase 1.1 hardening
items (living-agent `max_agents` enforcement, collection capacity bounds in `WorldState`, replay
and intervention fixes, and 17-action adapter coverage) are tracked separately. Empirical
long-horizon shock recovery, multi-generation population runs, dual-track OOD evaluation, and live
Phase 1.4/2.2 containment and capability-synthesis gates remain **untested/pending**.
