# src/evolzen/ — shared foundation

The pieces every one of the nine subsystems below depends on. Nothing here is specific to any
one phase — changing anything in this folder is a change that affects the whole pipeline.

| File / folder | Purpose |
|---|---|
| [`config.py`](config.py) | `pydantic-settings`-based configuration: one `EvolZenSettings` root, loaded from env vars, an optional `.env`, and the YAML files under `configs/`. |
| [`logging.py`](logging.py) | One consistently-formatted logger (loguru) across every subsystem, taggable by phase. |
| [`tracking.py`](tracking.py) | Pluggable experiment tracking (`NoOpTracker` by default, `WandbTracker` behind the `tracking` extra) — no subsystem hard-codes a tracking vendor. |
| [`schemas/`](schemas/) | **The data contract.** Current Phase 0 types include `Transition`, `DriveVector`, and `Manual`; Phase 1.1 will add the versioned world snapshot, growth-event, agent-profile, provenance, and capability-package contracts before implementation proceeds. |
| [`storage/`](storage/README.md) | Versioned transition-log interface; production persistence remains pending. |

New `schemas/development.py` supplies frozen birth genomes, snapshots, outcomes, lessons and
archive assessments for `agents/development/`. It does not add the proposed world snapshot,
capability package or rich social-profile classes. See
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
