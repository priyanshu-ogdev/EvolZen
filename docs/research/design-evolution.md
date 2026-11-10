# Design Evolution — What Changed, Why, and How It Got Better

Every mechanism that changed across this project's revisions, in one place: what it was, what
it became, why it changed, what got better, and where that improvement is documented. This is
the record worth keeping for a paper or a grant application — it shows the reasoning survived,
not just the final design. Organized by the subsystem each change now lives in.

Three structural revisions preceded the current baseline:

- **v0 — the original blueprint** ("EvolZen" / "Building the Universe, Building the God"): an
  ambitious, physically-simulated voxel civilization observed by a central "AGI," targeting AGI
  directly on a 24-36 month timeline.
- **v1 — the PRD rescoping**: every mechanism below was traced to its root failure and replaced
  with a scoped, citable, buildable equivalent.
- **v2 — the SOTA integration pass**: every phase was checked against the cited 2026 literature
  and upgraded where relevant; actor/synthesizer/verifier systems became a design precedent, not
  a guarantee of transfer.

This baseline is the integrated result of all three passes, restructured around nine named
subsystems instead of the original two-segment framing (see [ADR 0003](../adr/0003-nine-subsystems-not-two-packages.md)).
The October 2026 audit adds a second correction: the target is now a persistent growing world,
not merely a growing rule library observed by a central “god” component.

## `evolzen.environment`

**Was:** a real-time, physically-simulated voxel civilization — a custom C++/CUDA engine, a
5-layer per-voxel state API, a Discrete Element Method structural solver, at a population/city
scale requiring datacenter-class compute.
**Became:** a persistent, event-sourced, discrete social sandbox with a seeded typed transition
contract, snapshots, a growth ledger, and bounded versioned capability packages.
**Why:** estimated compute for even the agent population alone exceeded the stated
three-workstation rig (AGX Spark, DGX Spark, A6000) by several orders of magnitude, and — more
importantly — physical realism was never actually the requirement. Verifiability was, and a
much smaller domain can be just as verifiable.
**How it got better:** buildable on the actual hardware, while the explicit persistence and growth
contract makes the revised research goal measurable. “Moore machine” is retained only as a legacy
module name; exact replay is not treated as causal identification.
**Citations:** OPINE-World, Tycho.

## `evolzen.agents`

**Neuroplasticity mechanism. Was:** a rank-expanding LoRA "aging ODE"
(`plasticity(t) = plasticity_0 · e^(-λt)`, rank 4→16→64 tied to age) with no mechanism for why
rank should track age rather than task complexity. **Became:** a fixed drive-vector evolved via
a Quality-Diversity archive, plus Darwin-Gödel-Machine-style validated self-modification of an
agent's own policy code. **Why:** the original was an invented metaphor with no established
continual-learning precedent — unfalsifiable, not buildable-and-testable. **How it got better:**
QD and DGM provide relevant empirical design precedents with validation gates; they do not establish
that EvolZen's specific population ontology or self-modification loop will work.

**Reproduction / inheritance mechanism. Was:** literal genetic crossover of parents' LoRA weight
matrices plus Gaussian mutation. **Became:** an evolved, low-dimensional drive-vector (never
literal weight crossover), with weight-inheritance and data-inheritance kept as separate,
explicit tracks. **Why:** independently trained neural networks don't share an aligned parameter
space — the "competing conventions" problem in neuroevolution means naive weight crossover
typically breaks both parents' behavior rather than blending it. **How it got better:** the new
mechanism avoids the failure mode entirely, and now has a real open-ended-evolution precedent
(DGM's growing archive of self-modified variants) instead of being a purely defensive fix.

**Diversity maintenance. Was:** implicit and unmonitored — diversity was assumed to emerge from
evolution with no tracking mechanism. **Became:** a tracked diversity metric as an explicit
collapse gate, upgraded to a QD/MAP-Elites archive plus three specific, evidence-based design
rules (avoid over-aligned clone populations, avoid dense communication topology, avoid
authority-driven hierarchy). **Why:** diversity collapse in multi-agent LLM populations is now a
documented, empirically characterized phenomenon with identified causal factors. **How it got
better:** the design rules are specific and falsifiable, not a vague aspiration.
**Citations:** Darwin Gödel Machine (arXiv:2505.22954), Quality-Diversity (arXiv:2406.03731),
Diversity Collapse study (ACL 2026 Findings).

## `evolzen.economy`

**Was:** agents write "books" (serialized policy-weight embeddings deposited to a vector
database); other agents read them to warm-start training; no floor on how much of any
generation's training data must be real, non-agent-generated material.
**Became:** a mandatory provenance floor plus a tracked diversity metric as an explicit collapse
warning and generation-halting circuit breaker; further upgraded to falsifiable, revisable
natural-language manuals. A vendor-reported cross-model transfer result is retained as a case
study, not as a guaranteed EvolZen effect.
**Why:** training purely on prior generations' own output is the literature's own reference
setup for demonstrating model collapse.
**How it got better:** adopts provenance tracking and a collapse circuit breaker, while treating
manual transfer as a faster, cheaper, more inspectable channel to measure. The mechanism is matched
to the project's compute asymmetry but remains untested here.
**Citations:** Shumailov et al. (Nature, 2024), Agno manual-transfer result (2026), Economy of
Minds (arXiv:2606.02859).

## `evolzen.exploration`

**Was:** agents independently discover the arch, the water wheel, and the SR latch through
unassisted trial-and-error RL within a fixed simulated timeframe — "give it a reward function"
standing in for open-ended discovery.
**Became:** an actor (probes) / synthesizer (writes executable hypothesis code) / verifier
(exact-match against replay) loop, exploration steered by ontology error; further upgraded to
wiring an off-the-shelf coding-agent harness directly to the environment as the synthesizer.
**Why:** no existing RL research demonstrates open-ended discovery of compositional engineering
artifacts even at toy scale — this was the single largest unsupported claim in the original
document.
**How it got better:** recent papers provide relevant actor/synthesizer/verifier precedents, so
an existing coding-agent harness can be evaluated as a candidate synthesizer rather than rebuilt
from scratch. Their benchmark scores are source- and task-specific; transfer to this persistent
social sandbox remains untested.
**Citations:** OPINE-World, Tycho, Executable World Models for ARC-AGI-3 (arXiv:2605.05138).

**Causal-understanding layer (verification standard, shared with `evolzen.containment`). Was:**
a differentiable Structural Causal Model "Causal Gate" with a stated but uncomputed gradient
 formula (`∇_actual = Gate(causal_score) × ∇_raw`). **Became:** exact-match
 transition reproduction plus held-out combinations and controlled intervention checks, applied
 wherever a candidate rule or capability package is promoted. **Why:** real counterfactual inference requires an identifiable causal
graph that cannot generically be discovered from raw multi-agent trajectories; the original
formula was notation, not a specified, computable procedure. **How it got better:** the
counterfactual-testing intuition survives in an implementable form, using the same falsifiability
 bar used by relevant programmatic-modeling systems, strengthened for EvolZen with interventions
 and validity context instead of treating replay as proof of a causal graph.

## `evolzen.library`

**Was:** a "Slow Weights" base model silently overwritten at the end of each simulated century,
plus real-time "Fast Weights" — no forgetting safeguard, no measurement of forgetting.
**Became:** a frozen, growing, verified-rule library, spawn-triggered like a Dirichlet process,
protected by a replay buffer and periodic held-out regression tests.
**Why:** silent overwriting is exactly the mechanism catastrophic-forgetting research warns
against, and the assumption that this wouldn't be a problem was never tested.
**How it got better:** forgetting is now a measured, tracked, actively-mitigated quantity,
calibrated against real 2026 frontier-scale evidence instead of an assumed non-issue.
**Citations:** Ferguson (1973) on Dirichlet process mixture models.

## `evolzen.predictor`

**Prediction-accuracy target. Was:** an inverse-RL reward function with an arbitrary,
pre-committed ">90% accuracy 10 time-steps into the future" target. **Became:** policy-gradient
(PPO/GRPO) training against a real, verifiable environment signal, with accuracy reported
plainly rather than targeted in advance, protected by deployment-experience rehearsal against
forgetting. **Why:** multi-agent systems with learning components are close to chaotic — small
model updates change everyone's policy simultaneously, which tends to hurt long-horizon
predictability rather than help it. **How it got better:** honest, un-gamed reporting, layered
with a specific, validated continual-learning mitigation (CLaaS-style rehearsal) instead of an
assumption that RL "converges toward" ever-more-general understanding.
**Citations:** CLaaS (arXiv:2606.05559), TFGN (arXiv:2605.15053).

## `evolzen.containment`

**Was:** "complete freedom, complete internet access, agents may bypass the sandbox" — presented
as a feature of the system.
**Became:** an explicit containment layer (network egress allow-list, hard resource ceilings,
full logging, kill switch); further upgraded to hardware-isolated microVM/gVisor sandboxing plus
dynamic capability governance.
**Why:** unrestricted access combined with a reward structure that incentivizes boundary-testing
is a real operational risk independent of the system's actual capability level — the same
structural situation the AI-boxing/containment literature describes, regardless of framing.
**How it got better:** specifies hardware isolation, default-deny policy, and target-host
acceptance instead of treating a backend name as proof of security. Behavior-sensitive governance
can tighten access but cannot bypass the static policy.
**Citations:** Bostrom (2014), Yudkowsky (2002), CORAL (arXiv:2604.01658), Sidik & Rokach
(arXiv:2604.11839), Safety Must Precede the Deployment of Open-Ended AI (arXiv:2502.04512).

**Ethical/alignment framing. Was:** a hard-coded "Constitutional Filter" of "mathematically
verifiable ethical constraints," with no account of how conflicts between them get resolved.
**Became:** explicit, testable behavioral rules checked against logged behavior, embedded in a
containment-first framing. **Why:** formally verifying open-ended, potentially-conflicting value
constraints is an active, unsolved research area — not buildable in a few months.

## `evolzen.recognition`

**Knowledge integration ("Oracle API"). Was:** query a real-world knowledge base and seed the
answer into the simulation when agents plateau technologically — the system doesn't discover,
it's told. **Became:** a growing verified-rule library, then a JEPA + wake-sleep recognition
model whose generalization is measured via explicit ablation, plus a natural-language manual
layer for fast transfer. **Why:** querying and injecting an answer isn't grounded generalization
— it never tests whether the system can generalize on its own. **How it got better:** the
recognition model's contribution is measured (with/without ablation), not assumed, and the
manual layer gives a real, measured transfer-efficiency number instead of a hoped-for one.

**The recognition architecture itself.** Proposed as an explicit JEPA + wake-sleep hybrid, not
declared a contribution in advance. A JEPA-style component learns candidate state
representations; a DreamCoder-style component learns typed operators. Both must be compared with
simpler baselines and evaluated with the ablation matrix: recognition on/off, manual on/off,
JEPA-only, wake-sleep-only, and combined. **Citations:** LeJEPA (arXiv:2511.08544) and
DreamCoder (PLDI 2021) are component precedents; the fusion and its transfer to this world are
untested.

## `evolzen.evaluation`

**Scale-to-generality claim. Was:** vectorize to 1,000 parallel city instances and use MAML to
extract "universal laws of civilizational development" — generality proven by raw scale of
exposure. **Became:** two separate tracks: persistent-world longitudinal growth and held-out
world-seed/mechanic adaptation scored with EvolZen Action Efficiency (EAE), inspired by but not
interchangeable with ARC-AGI-3 RHAE. **Why:** raw exposure does not establish transfer, and the
hardware plan does not justify 1,000 full worlds. **How it got better:** world growth and fresh
adaptation are now measured without conflating their claims.

**The benchmark question itself. Was:** no operational definition at all — success was
self-referential ("the system understands humanity," "the system passes real-world benchmarks
at human-expert level"). **Became:** explicit persistent-world and fresh-world metrics, with
ARC-AGI-3 used only as a dated methodological reference when the protocol is comparable. **Why:**
a custom social sandbox cannot inherit another benchmark's score semantics automatically. **How it
got better:** the project now reports what it actually measures and preserves exposure history as a
first-class variable. **Citations:** ARC Prize Foundation; third-party public-set reports are
case studies, not universal baselines.

## Project-level (no single subsystem)

**Real-world transfer / "graduation" claim. Was:** fine-tune the system's learned weights on
real bridges, real code, and real human social conflict, and claim the result demonstrates
cross-domain general intelligence and empathetic reasoning. **Became:** dropped entirely,
replaced by an explicit statement (see `docs/PRD.md` §4, Non-Goals) of what would and would not
count as evidence of progress, scoped to a specific, falsifiable claim about generalization
efficiency within a defined task family. **Why:** there is no demonstrated relationship between
"empathy" learned from watching synthetic agent simulations and understanding real human
suffering, culture, or context — the single largest unjustified leap in the original document,
and no development since has changed that. **How it got better:** the project can now produce a
genuine, publishable result — including a negative one — instead of a claim the evidence was
never going to support.

## Why the ceiling holds regardless of any upgrade above

None of the changes above, individually or stacked together, closes two structural gaps this
project's own PRD names honestly (`docs/PRD.md` §4):

- **Generality is bounded by task diversity, not by how well one task is learned.** A system
  that becomes excellent at this project's environment family has learned one narrow
  competency, however well — even the impressive 2026 manual-transfer result is a data point
  about transfer *within* a family of related games, not evidence against this ceiling.
- **A system cannot distill past its teacher without an external reward.** Every component in
  this design — JEPA, wake-sleep, the manuals, the DGM-style self-modification — is bounded by
  the base models it starts with, plus whatever real, verifiable signal the environment
  provides. This is exactly why `evolzen.environment`'s insistence on a genuinely checkable
  outcome, not a merely plausible one, remains the single most important design decision in the
  entire plan, upgrades or not.
