# src/evolzen/cli/ — the `evolzen` command

Thin Typer CLI. No research logic lives here — this module only wires
`evolzen.config` + `evolzen.logging` + the nine subsystems' public APIs together. If you're
implementing behavior, you want the subsystem folder, not this one.

## Commands

| Command | Wires to | Status |
|---|---|---|
| `evolzen run` | `evolzen.environment`, `evolzen.agents`, `evolzen.economy` | `NotImplementedError`, pending Phase 1.1's persistent-world contract and hardware pilot. |
| `evolzen train` | `evolzen.predictor`, `evolzen.recognition` | `NotImplementedError`, pending Phase 2.1's planner. |
| `evolzen evaluate` | `evolzen.evaluation` | `NotImplementedError`, pending the persistent-world and fresh-world evaluation generators. |

## Run it

```bash
uv run evolzen --help
uv run evolzen run --generations 5
uv run evolzen train --steps 1000
uv run evolzen evaluate --rounds 10
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
