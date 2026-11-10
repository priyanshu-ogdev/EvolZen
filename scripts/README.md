# scripts/

Small, direct dev scripts — no framework, no magic.

| Script | Purpose |
|---|---|
| [`bootstrap.sh`](bootstrap.sh) | One-time setup: installs `uv`, syncs base deps, installs pre-commit hooks, runs tests. Set `EVOLZEN_INSTALL_GPU_EXTRAS=1` to also pull GPU extras — actual rig only. |
| [`check.sh`](check.sh) | Everything CI runs — run locally before pushing. |

Prefer `make setup` / `make check` for day-to-day use; these are what those targets call.
