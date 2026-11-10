# Lifecycle, parenthood and inheritance

## Birth and overlapping generations

`born(id, seed, tick, config=..., parents=...)` returns an immutable `BrainSnapshot`.
A founder has no parents and generation zero. A descendant has one or two distinct living mature
parents and generation `1 + max(parent generation)`. The new agent starts at age zero with no
personal outcome estimates, memories or lessons. Its temperament is inherited numeric data;
its knowledge is not. Birth does not kill or replace either parent.

One parent is permitted for simplified inheritance controls; two-parent reproduction is a second
condition. Neither requires biological sex or sexual behavior. A population scheduler must enforce
unique IDs, sufficient resources, maturity, cooldown, maximum live population and balanced lineage
sampling before admitting a birth. The local `born` function validates lineage and maturity but
cannot enforce global resource/population limits without the world.

## Stages and age

Default simulation thresholds are illustrative, configurable and **not human years**:

| Age in world ticks | Stage | Intended curriculum (not auto-granted competence) |
|---|---|---|
| 0–99 | Child | Observe, rest, simple resource use, supervised trial, receive lessons |
| 100–299 | Adolescent | Wider tool practice, negotiation, independent experiments |
| 300–999 | Adult | Resource allocation, eligible reproduction, teaching |
| 1000–1499 | Elder | Continued learning, teaching, retrieval and skill consolidation |
| 1500+ | Dead | No actions, learning, teaching or reproduction |

Age is `tick - born_at`, never the number of LLM calls. All clocks are monotonic. Expiry is
terminal; restore a pre-expiry branch only as an explicitly different experiment, not a revived
agent in the same timeline. `advance` changes age without adding knowledge. It rejects a live
pending action; terminal expiry cancels it and the host must record the cancellation.
No hunger, illness, health-driven death or biological metabolism is implemented yet.

The domain supplies minimum action ages and rechecks legality during execution. Stage names are
labels, not privileges. Safe tool access also requires capability checks and competence criteria.
Learning rate is constant in the baseline so age and update budget can be separated experimentally.
An age-dependent plasticity schedule is optional research, not a mandated exponential decay.

## What grows

1. **Experience:** outcomes seen in this lifetime, with evidence IDs.
2. **Knowledge:** estimates, later manuals and evidence-linked episodic memories.
3. **Skills:** held-out task performance, not an age-derived rank or birthday bonus.
4. **Planning:** broader permitted action repertoire and, later, measured search competence.
5. **Culture:** lessons transmitted while generations overlap.
6. **Population diversity:** behavioral niches across descendants, measured separately from traits.

Base-model parameter count does not increase in v1. A future adapter expansion requires a
capacity/compute budget, measured saturation, held-out benefit, retention checks and rollback.
An old agent may keep learning; an inexperienced old agent must not be reported as an expert.

## Separate inheritance channels

| Channel | At birth | During overlapping lives | Status |
|---|---|---|---|
| Temperament | Numeric coefficient mixing plus bounded mutation | Fixed within lifetime | Implemented |
| Personal evidence | Empty | Own verified outcomes | Implemented numerical baseline |
| Parental lessons | Empty | Evidence-linked advice from living mature parents | Implemented |
| World assets | Host-defined transfer | Trades/inheritance laws | World integration pending |
| Weights | Shared base by default; no weight crossover | Optional validated private adapter updates | Planned |
| Cultural manuals | Explicit access policy; no omniscient global library | Teach, contradict, revise | Full manual integration pending |

Teaching is non-destructive: parents retain what they teach. A lesson is context/version scoped
and cannot certify a child's mastery. In v1 it influences only an unseen action's prior with a
capped weight; the child's own experience takes precedence. Archived lessons may remain readable
after a parent's death, but a new live teaching event cannot be emitted by a dead parent.

## Meaning of a “thinking child”

A shared pretrained LLM already contains adult language and world knowledge. The child construct
restricts *local* memory, permissions, curriculum and acquired game skills; it does not erase
pretraining. A genuinely blank neural learner is a separate, much more expensive experiment.
Report these two interpretations distinctly and include a pretrained-knowledge leakage probe.
