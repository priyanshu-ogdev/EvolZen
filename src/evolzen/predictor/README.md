# evolzen.predictor — Phase 2.1

**Goal:** build a grounded predictor of world transitions, agent actions, and declared latent
profile variables. Start with supervised/action-prediction baselines; add policy-gradient planning
only after its incremental value is measurable.

Full research design: [`docs/phases/2.1-predictor.md`](../../../docs/phases/2.1-predictor.md).

## What's here

| File | Purpose |
|---|---|
| [`planner.py`](planner.py) | `Planner` — baseline prediction first, with optional PPO/GRPO-style planning against replayable world outcomes. |
| [`rehearsal_buffer.py`](rehearsal_buffer.py) | `RehearsalBuffer` — configurable old/new replay for measuring forgetting and transfer. |

## How to build this

1. Implement `Planner.predict` and `.train_step` against real `evolzen.environment` /
   `evolzen.agents` transition data. Labels must come from replayable world outcomes, not another
   model's approval.
2. Wire the rehearsal buffer from the first training run and declare its replay/data budget.
3. Report prediction, intervention response, forward transfer, backward transfer, forgetting,
   adaptation latency, and update cost. Compare replay against task-free/replay-free training as
   an ablation; do not import an external percentage as a universal baseline.

**Success metric:** held-out transition and intervention performance plus longitudinal transfer and
forgetting curves, with no fixed accuracy target accepted in advance.

**Depends on:** `evolzen.schemas.transition`, `evolzen.tracking`.
**Depended on by:** `evolzen.recognition` (the planner searches the library, guided by the
recognition model, to act and predict).
