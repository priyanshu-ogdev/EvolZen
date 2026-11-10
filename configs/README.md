# configs/

YAML run configs, one file per subsystem that has a settings group in `evolzen.config`, layered
on top of (and overridden by) environment variables. Values here map 1:1 onto the matching
`BaseModel` in `evolzen/config.py`. The current files are Phase 0 defaults; they do not yet
represent the complete Phase 1.1 world-growth contract or Phase 2.4 evaluation schema.

Precedence (highest wins): CLI flag > environment variable (`EVOLZEN_<GROUP>__<FIELD>`) > YAML
file in this directory > class default.

Not every subsystem has a config file here — only those with a settings group defined in
`evolzen.config` (`environment`, `agents`, `economy`, `predictor`, `recognition`).
`containment`, `exploration`, `library`, and `evaluation` don't have tunable settings yet;
add a settings group and a matching YAML file here together, in the same PR, when they do.
When Phase 1.1 is implemented, add explicit settings for world seed/replay, growth bounds, and
exogenous-input recording. When Phase 2.4 is implemented, add separate persistent-world and
fresh-world evaluation settings; never use one flag to silently merge those tracks.

`economy.real_data_floor` is retained as a Phase 0 field name for compatibility. Its planned
semantics are the provenance floor described in `docs/phases/1.3-economy.md`, not a claim that
synthetic simulator output is real-world data.
