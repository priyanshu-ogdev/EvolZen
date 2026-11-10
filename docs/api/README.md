# docs/api/

Thin `mkdocstrings` index pages — each file is a handful of `::: module.path` directives that
pull the real documentation (docstrings, type signatures) directly from the source in
`src/evolzen/`. Don't duplicate documentation here; if something's missing from the rendered
API reference, the fix is a better docstring in the source module.

Build/browse locally with `uv run --group docs mkdocs serve`.
