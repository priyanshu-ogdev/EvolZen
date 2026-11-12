# Motivation: a randomized, bounded birth equation

**Untested design hypothesis.** Coordinate semantics and equations below are invented for
EvolZen. They must be compared with simpler controls, not treated as laws of personality.

## Eight coordinates

All vectors use this order, recorded by `Motive` in `schemas/development.py`.

| Coordinate | Observable incentive | Distinction and test |
|---|---|---|
| Pride | Reputation, status, mastery recognition | Choose public credit versus identical private reward |
| Greed | Retained assets and future control of resources | Save versus consume under equal survival need |
| Lust | Nonsexual attraction, affiliation and preferred experiences | Social contact versus solitude; no sexualized child content |
| Envy | Relative disadvantage against a visible comparison group | Hold own assets fixed while changing observed peer assets |
| Gluttony | Immediate consumption/satiation beyond baseline need | Consume now versus retain resources; not identical to greed |
| Wrath | Response to perceived obstruction, threat or unfairness | Protest/defend/repair under permitted action constraints |
| Sloth | Avoidance of effort and resource expenditure | Lower-cost method of achieving the same end |
| Null | Disengagement/absence of goal pursuit | Wait/abstain even where another zero-effort action exists |

Low wrath does not mechanically imply kindness; high pride may encourage mastery or bluffing
depending on opportunities and learned beliefs. Cooperation and care can emerge from multiple
combinations but are not guaranteed or adequately modeled by these eight dimensions. Do not
equate demographic identity with coefficient values. Future extensions need their own ablations.

## Inputs and normalization

The environment adapter produces an eight-element feature vector `x_t` in [-1, 1] with versioned
feature definitions: status discrepancy, resource discrepancy, affiliation opportunity, relative
disadvantage, consumption pressure, obstruction, fatigue, and disengagement opportunity.
Each feature must come from the agent's permitted observations/internal needs, not evaluator
secrets. Values outside the range, NaN, infinity and wrong dimensions are rejected, not clipped
silently. Feature scaling is fixed on training data and logged with the scenario version.

For agent i, drive k at decision n:

    a_k(n) = tanh(b_k + (1/8) sum_j W_kj x_j(n)
                  + c_k age_fraction(n) + rho_k a_k(n-1))
    p_k(n) = exp((a_k(n) - max(a(n))) / T) / sum_l exp((a_l(n) - max(a(n))) / T)

`age_fraction = (world_tick - born_at) / lifespan` for living agents. All eight ratios are
nonnegative and sum to one; activations are bounded [-1, 1]. A ratio is relative priority, not
a probability that the agent will commit a particular act. Null is an explicit competing
coordinate; it is not `1 - sum(other unnormalized values)`.

Founder coefficients are sampled with a local seeded generator: b,c uniform [-0.5,0.5],
W uniform [-1,1], rho uniform [0,0.5], T=1. Coefficients are frozen birth data. Seeds and full
coefficients are persisted; seed alone is not a portable serialization format. Inheritance
averages aligned numerical coefficients plus bounded uniform mutation; rho stays [0,1].
T remains the parent mean. No equations are strings, and no `eval` or generated Python is used.

The equation advances once per decision, not every empty world tick. This is a simple recurrence,
not a continuous-time ODE. Compare decision-rate-matched agents to avoid confounding momentum
with action frequency. Periodicity, cross-drive recurrence, homeostatic feedback and learned
equations are future variants, not features of v1.

## From preferences to choices

Each domain candidate has an immutable action ID, context key, skill key, eight predicted
outcome values, cost, minimum age and domain permission flag. Context/skill keys must distinguish
materially different action parameters and world-rule versions.

    score(action) = sum_k p_k * expected_outcome_k(action) - cost(action)

Expected outcomes are the agent's own empirical estimate when available. Otherwise they are
the supplied candidate prediction, blended with at most 25% parental advice (10% default).
Own experience overrides parental advice. The highest score wins; action ID breaks ties, making
candidate ordering irrelevant. Candidate counts are bounded. If no candidate is legal the call
fails; the host must supply an explicit legal wait action when needed.

## Theoretical grounding & formal classification

While the seven-sins-plus-Null names and $8 \times 8$ tendency matrix $W_{kj}$ are untested
EvolZen design choices, their **mathematical form** maps directly onto three established
frameworks in IEEE and ML literature:

1. **Homeostatic Drive Modulation (Keramati & Gutkin, *eLife* 2014, `keramati2014homeostatic`):**
   The context vector $x_t \in [-1, 1]^8$ encodes discrepancies (resource deficit, status gap,
   consumption pressure, fatigue). Modulating drive activations $a_k(n)$ from internal and
   environmental deviations functions as a bounded homeostatic weighting mechanism rather than a
   claim about human emotion.
2. **Multi-Objective Linear Scalarization (Hayes et al., *AAMAS* 2022, `hayes2022morl`):**
   Evaluating `score(action) = sum_k p_k * expected_outcome_k(action) - cost(action)` is
   mathematically **MORL linear scalarization** using dynamic preference weights $p_k(n)$ over
   an 8-dimensional reward vector. By MORL theory, linear scalarization can only recover policies
   on the **convex hull** of the Pareto front; whenever trade-offs (e.g., safety vs. immediate
   consumption) are non-convex, future variants must ablate **non-linear (Chebyshev) utility**
   instead of assuming linear weights suffice.
3. **Priority Ratios vs. Stochastic Policy Operators (Asadi & Littman, *ICML* 2017, `asadi2017mellowmax`):**
   `drive_step` uses Boltzmann softmax solely to normalize $a_k(n)$ into positive priority weights
   $p_k(n)$, while `decide` uses **deterministic argmax** (`ranked[0]`). If future versions convert
   action scores into stochastic exploration policies, standard Boltzmann softmax can suffer from
   non-contraction/multiple fixed points under value iteration; the **Mellowmax** operator provides
   a provably non-expansive alternative to test against greedy selection and $\epsilon$-greedy.

This baseline is greedy and does not implement curiosity, planning or autonomous exploration
(compare Merrick, *IEEE TAMD* 2010, `merrick2010valuesystems`; Colas et al., *JAIR* 2022,
`colas2022autotelic`). A controlled exploration schedule, intrinsic competence-progress term, or
LLM proposal distribution must be added as a separately measured condition. Predicted utility is
not factual truth; observed outcome updates are how the baseline corrects a mistaken
preference-to-action expectation.

## Preferences are not permissions

Candidate masks are only an initial host-provided filter. The environment independently checks
action legality and lifecycle permissions on execution. A high wrath or greed ratio cannot
grant network access, change the reward evaluator, override containment, or alter another agent's
memory. Hard constraints sit outside utility maximization; violations cannot be traded for reward.

For future LLM reasoning, use ratios as structured goal-selection and memory-retrieval inputs,
then compare against ranking-only. Do not claim that a prompt changes internal neural reasoning
without controlled evidence. Log concise goal IDs, candidates, scores and evidence—not hidden
chain-of-thought.
