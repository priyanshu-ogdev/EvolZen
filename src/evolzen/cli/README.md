# src/evolzen/cli/ — the `evolzen` command

Thin Typer CLI. No research logic lives here — this module only wires
`evolzen.config` + `evolzen.logging` + the nine subsystems' public APIs together. If you're
implementing behavior, you want the subsystem folder, not this one.

## Commands

| Command | Wires to | Status |
|---|---|---|
| `evolzen run` | `evolzen.environment`, `evolzen.agents`, `evolzen.economy` | Implemented: runs multi-generation developmental agent loop with transition logging and generational reproduction. |
| `evolzen train` | `evolzen.predictor`, `evolzen.recognition` | Implemented: trains GRPO planner & JEPA representations on logged transitions. |
| `evolzen evaluate` | `evolzen.evaluation` | Implemented: runs dual-track persistent vs held-out generalization benchmark. |
| `evolzen ablate` | `evolzen.recognition` | Implemented: runs 4-cell pre-registered ablation matrix. |
| `evolzen replay` | `evolzen.storage` | Implemented: verifies cryptographic SHA-256 hash chains of logged transitions. |
| `evolzen inspect` | `evolzen.environment`, `evolzen.agents`, `evolzen.cli.dashboard` | Implemented: inspects world state and exports hermetic interactive HTML5 visualization dashboard. |
| `evolzen cluster` | `evolzen.cli.cluster`, `evolzen.containment` | Implemented: pre-flight hardware cluster activation and node diagnostics for DGX Spark, Jetson AGX Spark, RTX A6000, and standalone rigs. |

## Run it

```bash
uv run evolzen --help
uv run evolzen run --generations 5
uv run evolzen train --steps 1000
uv run evolzen evaluate --rounds 10
uv run evolzen ablate --steps 50
uv run evolzen inspect --export-html data/dashboard.html
uv run evolzen replay --db-path data/transitions.duckdb
uv run evolzen cluster --role standalone
```

`main.py` remains a thin entry point. Command logic belongs in its owning subsystem; the current
commands intentionally fail closed until their real phase contracts are implemented.

## How to build this

1. Don't add flags speculatively — add a CLI option only once the underlying subsystem call it
   wires to actually accepts that parameter.
2. Keep this file thin. More than a few lines of logic in a command function means that logic
   belongs in a subsystem, with a test, and this file should just call it.
3. `evaluate` must report persistent-world and fresh-world tracks separately, record exposure
   history, and never use a fixed reused held-out set as the final evaluation.
