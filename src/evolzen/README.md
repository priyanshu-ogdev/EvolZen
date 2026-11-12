# src/evolzen/ — shared foundation

The pieces every one of the nine subsystems below depends on. Nothing here is specific to any
one phase — changing anything in this folder is a change that affects the whole pipeline.

| File / folder | Purpose |
|---|---|
| [`config.py`](config.py) | `pydantic-settings`-based configuration: one `EvolZenSettings` root, loaded from env vars, an optional `.env`, and the YAML files under `configs/`. |
| [`logging.py`](logging.py) | One consistently-formatted logger (loguru) across every subsystem, taggable by phase. |
| [`tracking.py`](tracking.py) | Pluggable experiment tracking (`NoOpTracker` by default, `WandbTracker` behind the `tracking` extra) — no subsystem hard-codes a tracking vendor. |
| [`schemas/`](schemas/) | **The data contract.** Currently includes `transition.py`, `drive_vector.py`, `manual.py`, `development.py`, `world.py`, and `library.py`; `schemas/__init__.py` re-exports `transition`, `drive_vector`, `manual`, and `library` (top-level re-exports for `world` and `development` remain pending). `AgentProfile` and `ProvenanceRecord` schemas remain planned. |
| [`storage/`](storage/README.md) | DuckDB-backed append-only `TransitionLogStore` (`transition_log.py`, `SCHEMA_VERSION = 1`) for transitions, snapshots, growth events, and branches; an explicit `schema_version` mismatch/migration guard on open remains planned. |

`schemas/development.py` supplies frozen birth genomes, snapshots, outcomes, lessons, and archive
assessments for `agents/development/`, separate from Phase 1.1 `schemas/world.py` (`WorldState`,
`WorldSnapshot`, `CapabilityPackage`, `ActionType`) and Phase 1.5 `schemas/library.py` (`RuleEntry`,
`ValidityContext`, `VerificationEvidence`). `AgentProfile` and `ProvenanceRecord` remain planned. See
[developmental contracts](../../docs/subsystems/agents/engineering.md).

## Subsystems built on top of this

| Subsystem | Phase |
|---|---|
| [`environment/`](environment/README.md) | 1.1 |
| [`agents/`](agents/README.md) | 1.2 |
| [`economy/`](economy/README.md) | 1.3 |
| [`exploration/`](exploration/README.md) | 1.4 |
| [`library/`](library/README.md) | 1.5 |
| [`predictor/`](predictor/README.md) | 2.1 |
| [`containment/`](containment/README.md) | 2.2 |
| [`recognition/`](recognition/README.md) | 2.3 |
| [`evaluation/`](evaluation/README.md) | 2.4-2.5 |
| [`cli/`](cli/README.md) | — (thin entry point, no research logic) |

## Why this lives at the top level, not in a "core" sub-package

Earlier scaffolding revisions put this in a separate `evolzen-core` *package*, alongside two more
packages (`evolzen-world`, `evolzen-observer`) for the rest. That was a mistake — see
[`CHANGELOG.md`](../../CHANGELOG.md), "Phase 0 v5." There is one package now
(`evolzen`), so there's nothing to distinguish this foundation *from* — it's just the code that
happens to sit above the subsystem folders in the same package, the same way any project's
shared utilities do.
