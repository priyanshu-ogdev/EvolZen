# Engineering boundaries and delivery plan

## Layout and status

**Initial numerical-core receipt, October 24, 2026:**
`PYTHONPATH=src python -m pytest tests/agents/development tests/schemas/test_development.py -q`
completed successfully: **32 cases passed**. This was a targeted source-path run, not a full
uv-environment or hardware certification. The three project-wide checks were also attempted once
with five-minute limits: `ruff check .` reported 14 pre-existing findings and one new import-layout
finding in `tests/schemas/test_development.py`; the new finding was corrected without changing
test behavior. `mypy .` could not start because mypy is unavailable. `python -m pytest -q`
stopped with 19 import-collection errors because system Python cannot locate `evolzen` without
the source path/project installation. No full-suite, type-check or docs-build success is claimed.
No model training or simulation was run. No failed project check was retried; the import-only
test formatting correction was reviewed statically after the passing targeted run.

No source folders are renamed and no existing public interfaces are broken. The developmental
implementation is a cohesive subpackage under the existing `agents` subsystem.

| Source | Implemented responsibility | Companion tests |
|---|---|---|
| `schemas/development.py` | Closed frozen records, eight coordinates, limits, lineage/snapshot validation | `tests/schemas/test_development.py` |
| `agents/development/motivation.py` | Seeded coefficient generation, bounded equations, inheritance | `tests/agents/development/test_motivation.py` |
| `agents/development/lifecycle.py` | Birth, age stages and parental maturity | `test_lifecycle.py` in the same test folder |
| `agents/development/brain.py` | Candidate ranking, pending decision, clock advancement | `test_brain.py` |
| `agents/development/learning.py` | Trusted receipt update and living-parent advice | `test_learning.py` |
| `agents/development/evolution.py` | Bounded behavior-cell elite archive | `test_evolution.py` |
Tests mirror each corresponding source owner.

The legacy `Agent`, five-coordinate `DriveVector`, `InferenceBackend.generate_action`,
`QualityDiversityArchive` and `AgentLineage` signatures remain unchanged. The new API is imported
from `evolzen.agents.development`; new records from `evolzen.schemas.development`.
There is deliberately no lossy automatic eight-to-five drive projection. Old inference/QD helpers
do not silently understand the new schema. The new `DevelopmentArchive` holds developmental
snapshots instead of coercing them into legacy entries.

Existing shared-schema importers were inspected across the project. This change adds a parallel
schema module and leaves `schemas/__init__.py` and existing model fields unchanged. World snapshot,
rule/capability packages and richer profile schemas described elsewhere are still proposals, not
newly implemented by this change.

The root `AGENTS.md` still describes every module as a stub. Replacing that owner-protected
snapshot text was refused by the editing tool pending explicit approval, so it was left unchanged.
Its containment and schema-review rules remain authoritative; use this status map and the root
README for the actual scope of the new numerical implementation.

## Host call sequence

    snapshot = born(...)
    snapshot = decide(snapshot, permitted_context, candidate_actions, world_tick)
    host executes snapshot.pending.candidate using environment and containment
    snapshot = observe(snapshot, trusted_outcome_receipt)
    host persists the decision/outcome and snapshot
    child = born(..., parents=(snapshot,), tick=current_world_tick)
    child = teach(snapshot, child, context_key, skill_key, current_world_tick)

The birth call in the last two lines requires a mature living parent. These are API descriptions,
not an executable demo or a way around `Sandbox`. `BrainSnapshot.model_dump_json()` and
`BrainSnapshot.model_validate_json()` provide serialization; persistent filesystem/database
storage and the population scheduler remain pending.

Only the host creates candidate permissions, time, observations, receipts and assessments. The
agent may propose content but cannot mark its own outcome verified. Snapshot immutability is not
authentication. Persistent receipts need versioned run IDs, signed or protected provenance,
exactly-once transition IDs, and crash-safe atomic append before production use.

## Critical subsystem interfaces

- **environment:** map legal observations to normalized eight features; execute legal actions;
  produce independently checked outcome vectors and evidence IDs. Track actual time and needs.
- **economy:** enforce resource/birth costs and parent teaching budgets; convert manual evidence
  into bounded advice records only through host checks.
- **exploration/library:** store generated hypotheses and verified skills separately; hypothesis
  success is not automatically policy competence. Execute generated code only inside Sandbox.
- **predictor:** predict future observations/actions, not hidden birth equations unless in a
  privileged evaluation condition. Scripted drive labels do not establish true mental intent.
- **containment:** authority independent of drive scores; no direct filesystem/network capability
  in the numerical core. Firecracker is a KVM microVM; gVisor is a different isolation design,
  not a hardware microVM by definition. Backend deployment remains a separate gate.
- **recognition:** optional learned proposal prior; cannot promote rules, manipulate evidence
  or replace the authoritative action validator.
- **evaluation:** owns frozen budgets, splits, paired controls and validation receipts. Final test
  scores never become live evolutionary fitness.

## Development milestones (not calendar promises)

| Milestone | Exit evidence | Status |
|---|---|---|
| A0: numerical contracts | Source tests for equations, birth, feedback, teaching and archive | Implemented; check results reported in delivery, not assumed |
| A1: trusted world integration | Child acts in a real typed adapter and receives host-verified feedback; all receipts replayable | Pending world adapter |
| A2: living families | Budgeted births, overlapping lives, teaching, death and crash-safe history | Local primitives only; scheduler pending |
| A3: learned proposals | Shared local LLM proposes bounded candidates with no privileged-state leak | Pending |
| A4: neural updates | Offline private adapters with replay, fixed validation and rollback | Pending |
| A5: population evolution | Host-selected parents from validated phenotype archive; five-generation study | Archive only; scheduler/study pending |
| A6: publication | Registered splits, all control conditions, costs and negative results | Pending |

Start with child-scale tasks such as choosing between immediate consumption, saving, rest, social
contact and skill practice. Labels alone must not determine rewards. Add conflicting incentives
and scarce information only after the simple choice/feedback/teaching loop is measurable.

## Hardware and reproducibility

No new dependencies or global settings. Numerical core is CPU-only and allocates no model.
Shared quantized base inference, batched agent requests, bounded contexts and private memory are
planned. The exact device called “AGX Spark” needs model/SKU confirmation before deployment sizing;
do not assume its CUDA, ARM, virtualization or serving support from a nickname.
Measure tokens/decision, latency, KV memory, training cadence and storage before choosing population
size. One LLM call per simulated physics tick is not the scheduling model.

Persist: full genome, versioned configuration, world and lineage IDs, context schema, action keys,
policy/checkpoint hashes, snapshot, pending sequence, teacher evidence and assessment suite. Store
secrets outside the repo. A population-wide snapshot must restore all agent clocks and event order,
not just individual object state.
