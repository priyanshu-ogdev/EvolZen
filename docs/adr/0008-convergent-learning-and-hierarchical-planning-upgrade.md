# ADR 0008: Convergent learning, non-convex MORL, and hierarchical world-model planning upgrade

**Status:** Proposed (target architecture beyond the Phase 1.2 numerical baseline; empirically **untested** in EvolZen)

## Context

The implemented `agents/development/` baseline (`motivation.py`, `brain.py`, `learning.py`)
provides a deterministic, host-locked numerical loop using:
- point-estimate Exponential Moving Average (EMA) updates (`observe`),
- one-step myopic candidate ranking (`decide`) via deterministic argmax, and
- linear MORL scalarization (`sum_k p_k * expected_outcome_k - cost`).

Literature analysis identifies five structural bottlenecks limiting sample efficiency,
non-stationary convergence, and representational scaling:

1. **Zero exploration regret guarantee:** Pure greedy argmax over point-estimate EMA values can
   lock permanently onto suboptimal actions when initial candidate priors or parental lessons are
   inaccurate.
2. **Convexity trap in linear MORL:** Linear weighted sums cannot discover Pareto-optimal choices
   on non-convex preference frontiers (`hayes2022morl`, `vanmoffaert2014morl`).
3. **Myopic one-step horizon:** Single-step candidate scoring lacks temporal credit assignment
   and multi-step counterfactual rollout planning (`hafner2025dreamerv3`, `hansen2024tdmpc2`).
4. **Primitive-tick bottleneck:** Selecting one atomic action per tick fails to compose durable
   multi-step skills stored in `evolzen.library.RuleLibrary` (`sutton1999options`).
5. **Multi-agent non-stationarity:** Independent learners in a 10–30-agent population violate
   stationary MDP assumptions unless peer dynamics are explicitly conditioned (`busoniu2008marl`).

Per `docs/PRD.md` §4 (`NG1`, `NG3`), this upgrade targets measurable improvements in regret,
Pareto coverage, EAE, and multi-generation stability—**not** an artificial general intelligence claim.

## Decision

Upgrade the agentic growth architecture in three staged, backward-compatible tiers evaluated
under paired ablation controls:

### Tier 1 — Uncertainty-Aware & Pareto-Complete Decision Core (CPU-friendly)
- **Epistemic uncertainty + provable exploration:** Extend `SkillEstimate` (in a future schema
  revision) with outcome variance / posterior precision so `decide` supports **UCB**
  (`auer2002ucb1`) and **Thompson Sampling** (`russo2018thompson`) for sublinear regret on
  stationary contexts, alongside **Mellowmax** (`asadi2017mellowmax`) stochastic policies.
- **Chebyshev (Tchebycheff) scalarization:** Supplement linear scalarization with augmented
  Chebyshev scalarization (`vanmoffaert2014morl`) relative to a host-normalized utopia vector
  $z^*$, enabling recovery of non-convex Pareto trade-offs.

### Tier 2 — Expected Free Energy & Latent World-Model Rollouts (`predictor` + `recognition`)
- **Unified epistemic + pragmatic objective:** Test Active Inference / Expected Free Energy
  scoring (`friston2015epistemic`, `parr2022activeinference`) combining homeostatic/goal utility
  with expected transition-information gain inside `evolzen.predictor.planner`.
- **Multi-step latent MPC:** Integrate `DreamerV3`/`TD-MPC2`-style imagined rollouts
  (`hafner2025dreamerv3`, `hansen2024tdmpc2`) over `evolzen.predictor` and `JEPAEncoder` latents,
  ablated strictly against one-step and model-free baselines.

### Tier 3 — Hierarchical Options & Non-Stationary Multi-Agent Stabilization
- **Temporal abstraction (Options / SMDP):** Represent verified `evolzen.library.RuleEntry`
  artifacts as **options** `(I, pi, beta)` (`sutton1999options`) with explicit preconditions and
  termination predicates so agents compose reusable multi-step macro-skills without sacrificing
  host-level per-tick permission checks.
- **Multi-agent equilibrium monitoring:** Track joint-action non-stationarity and equilibrium
  convergence (`busoniu2008marl`) alongside CVT-MAP-Elites behavioral coverage (`vassiliades2018cvtmape`)
  and semantic-collapse coupling (`diversitycollapse2026`).

## Consequences

- Every tier preserves existing `PRD.md` §4 non-goals, `SECURITY.md` Firecracker/gVisor `Sandbox`
  execution boundaries, and dual-track (`persistent-world` vs. `fresh-world` EAE) evaluation.
- Existing `agents/development/` tests remain untouched and act as the Tier-0 deterministic baseline
  in all matched ablations.
- Higher-tier world-model and hierarchical mechanisms introduce compute and stability risks that
  must be measured via transfer/forgetting curves and hardware acceptance gates before scaling.

