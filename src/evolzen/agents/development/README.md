# Developmental agent core

Detailed rationale and contracts: [agent design](../../../../docs/subsystems/agents/README.md).
Shared records: [`schemas/development.py`](../../schemas/development.py).

| Module | Public operations | What is actually implemented |
|---|---|---|
| `motivation.py` | `sample_genome`, `inherit_genome`, `drive_step` | Fixed safe equation family, numeric inheritance, eight ratios |
| `lifecycle.py` | `born`, `stage_at` | Seeded child birth, living/mature parents, simulation-age stages |
| `brain.py` | `decide`, `advance` | Deterministic candidate ranking, bounded pending state, terminal expiry |
| `learning.py` | `observe`, `teach` | Empirical outcome update and living-parent advice |
| `evolution.py` | `DevelopmentArchive` | Capacity-limited phenotype cells and external assessment gates |

API flow: `born -> decide -> host execution/verification -> observe`, repeated over a lifetime.
Then mature living agents can be passed as parents to `born`, and `teach` can transfer advice
while the child lives. The parent is unchanged. JSON snapshots include the entire equation and
bounded learning state. Persistent artifacts, world execution and population scheduling remain
unimplemented in this numerical core.

No legacy five-drive API is changed. No `eval`, generated-code execution, model training, resource
allocation or automatic births occur in these operations. The current learner updates numerical
outcome estimates; neural learning remains a separate milestone. `permitted`/`verified` values
must be supplied by a trusted host, not the LLM. Source tests live under
`tests/agents/development/`; a passing primitive test is not a population research result.
