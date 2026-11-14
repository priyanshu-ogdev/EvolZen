import pytest

from evolzen.agents.development import (
    advance,
    born,
    chebyshev_score,
    compute_ucb_values,
    decide,
    linear_score,
    mellowmax_probabilities,
    observe,
)
from evolzen.schemas.development import (
    ZERO,
    BrainSnapshot,
    Candidate,
    DevelopmentConfig,
    Outcome,
)


def test_action_feedback_changes_next_choice() -> None:
    a = Candidate(action_id="a", context_key="room", skill_key="a", predicted=(0.5,) * 8)
    b = Candidate(action_id="b", context_key="room", skill_key="b", predicted=(0.1,) * 8)
    initial = born("learner", 10)
    waiting = decide(initial, ZERO, (a, b), 0)
    assert waiting.pending is not None and waiting.pending.candidate == a
    outcome = Outcome(
        agent_id="learner", sequence=1, tick=1, action_id="a",
        evidence_id="transition-1", rewards=(-1.0,) * 8, verified=True,
    )
    learned = observe(waiting, outcome)
    next_step = decide(learned, ZERO, (a, b), 2)
    assert next_step.pending is not None and next_step.pending.candidate == b
    assert initial.knowledge == ()
    assert learned.knowledge[0].samples == 1
    with pytest.raises(ValueError):
        observe(learned, outcome)


def test_permission_and_age_masks_override_preference() -> None:
    forbidden = Candidate(action_id="forbidden", context_key="x", skill_key="x",
                          predicted=(1.0,) * 8, permitted=False)
    adult_only = Candidate(action_id="adult", context_key="x", skill_key="y",
                          predicted=(1.0,) * 8, minimum_age=300)
    rest = Candidate(action_id="rest", context_key="x", skill_key="rest")
    waiting = decide(born("c", 1), ZERO, (forbidden, adult_only, rest), 0)
    assert waiting.pending is not None and waiting.pending.candidate.action_id == "rest"
    with pytest.raises(ValueError):
        decide(born("c", 1), ZERO, (forbidden,), 0)


def test_pending_state_is_serializable_and_expiry_cancels_it() -> None:
    candidate = Candidate(action_id="rest", context_key="x", skill_key="rest")
    waiting = decide(born("c", 1), ZERO, (candidate,), 0)
    restored = BrainSnapshot.model_validate_json(waiting.model_dump_json())
    assert restored == waiting
    with pytest.raises(ValueError):
        decide(restored, ZERO, (candidate,), 1)
    dead = advance(restored, 1500)
    assert dead.pending is None
    with pytest.raises(ValueError):
        decide(dead, ZERO, (candidate,), 1500)


def test_candidate_ids_are_unique_and_ties_are_stable() -> None:
    a = Candidate(action_id="a", context_key="x", skill_key="a")
    b = Candidate(action_id="b", context_key="x", skill_key="b")
    state = born("c", 1)
    assert decide(state, ZERO, (a, b), 0) == decide(state, ZERO, (b, a), 0)
    with pytest.raises(ValueError):
        decide(state, ZERO, (a, a), 0)


def test_chebyshev_scalarization_resolves_nonconvex_front() -> None:
    """Verifies that Chebyshev scalarization selects balanced options on non-convex Pareto fronts.

    Citing Hayes et al. (AAMAS 2022) & Van Moffaert & Nowé (JMLR 2014): linear scalarization
    provably misses non-convex Pareto points, whereas Chebyshev distance to utopia z* finds them.
    """
    # Motive prioritizing coordinate 0 and coordinate 1 equally
    ratios = (0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # Candidate 1: extreme on coordinate 0
    val_extreme_a = (0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    # Candidate 2: balanced on both coordinates (non-convex interior point)
    val_balanced = (0.4, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    score_linear_extreme = linear_score(ratios, val_extreme_a, cost=0.0)
    score_linear_balanced = linear_score(ratios, val_balanced, cost=0.0)

    # Linear scalarization prefers extreme (0.45 > 0.40)
    assert score_linear_extreme > score_linear_balanced
    assert pytest.approx(score_linear_extreme) == 0.45
    assert pytest.approx(score_linear_balanced) == 0.40

    # Chebyshev scalarization prefers the balanced option (-0.296 > -0.4955)
    score_cheb_extreme = chebyshev_score(ratios, val_extreme_a, cost=0.0, rho=0.01)
    score_cheb_balanced = chebyshev_score(ratios, val_balanced, cost=0.0, rho=0.01)
    assert score_cheb_balanced > score_cheb_extreme
    assert score_cheb_balanced > -0.31
    assert score_cheb_extreme < -0.48


def test_chebyshev_preserves_strict_dominance() -> None:
    """If candidate A strictly dominates candidate B across coordinates, Chebyshev score is higher."""
    ratios = (0.125,) * 8
    dominated = (0.1,) * 8
    dominating = (0.8,) * 8

    score_dominated = chebyshev_score(ratios, dominated, cost=0.0)
    score_dominating = chebyshev_score(ratios, dominating, cost=0.0)
    assert score_dominating > score_dominated


def test_ucb_uncertainty_bonus_mechanics() -> None:
    """Verifies that UCB1 exploration bonus decays with sample count and scales with decisions."""
    base_values = (0.2,) * 8

    # Zero exploration c returns exact base values
    zero_c_values = compute_ucb_values(base_values, samples=0, total_decisions=10, exploration_c=0.0)
    assert zero_c_values == base_values

    # Positive exploration gives bonus that decays with more samples
    c = 0.5
    val_unsampled = compute_ucb_values(base_values, samples=0, total_decisions=20, exploration_c=c)
    val_few_samples = compute_ucb_values(base_values, samples=5, total_decisions=20, exploration_c=c)
    val_many_samples = compute_ucb_values(base_values, samples=50, total_decisions=20, exploration_c=c)

    assert val_unsampled[0] > val_few_samples[0] > val_many_samples[0] > base_values[0]

    # Clamping test: bonus cannot exceed 1.0
    high_base = (0.95,) * 8
    clamped = compute_ucb_values(high_base, samples=0, total_decisions=100, exploration_c=2.0)
    assert all(v == 1.0 for v in clamped)


def test_mellowmax_probabilities_properties() -> None:
    """Verifies that Mellowmax/softmax probabilities are valid, normalized, and monotonic."""
    scores = (1.0, 2.0, 3.0, 0.5)

    # Normalization: sums to 1.0
    probs = mellowmax_probabilities(scores, beta=2.0)
    assert len(probs) == len(scores)
    assert pytest.approx(sum(probs), rel=1e-5) == 1.0

    # Monotonicity: higher score has strictly higher probability
    assert probs[2] > probs[1] > probs[0] > probs[3]

    # Zero beta produces uniform distribution
    uniform_probs = mellowmax_probabilities(scores, beta=0.0)
    assert all(pytest.approx(p) == 0.25 for p in uniform_probs)

    # Empty input
    assert mellowmax_probabilities(()) == ()


def test_tier1_decision_chebyshev_selection() -> None:
    """An agent configured with use_tier1_decision=True uses Chebyshev multi-objective decision."""
    # Balanced motive weights on coord 0 and coord 1
    cand_extreme = Candidate(
        action_id="extreme_a",
        context_key="work",
        skill_key="specialist",
        predicted=(0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    cand_balanced = Candidate(
        action_id="balanced",
        context_key="work",
        skill_key="generalist",
        predicted=(0.4, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )

    tier0_config = DevelopmentConfig(use_tier1_decision=False)
    tier1_config = DevelopmentConfig(use_tier1_decision=True)

    agent_tier0 = born("agent_0", seed=42, config=tier0_config)
    agent_tier1 = born("agent_1", seed=42, config=tier1_config)

    # Provide context signal that creates demand for coords 0 and 1
    context = (1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    # Tier-0 selects candidate maximizing linear sum (or deterministic highest linear)
    dec_tier0 = decide(agent_tier0, context, (cand_extreme, cand_balanced), tick=10)
    assert dec_tier0.pending is not None

    # Tier-1 selects candidate via Chebyshev
    dec_tier1 = decide(agent_tier1, context, (cand_extreme, cand_balanced), tick=10)
    assert dec_tier1.pending is not None
    assert dec_tier1.pending.candidate.action_id == "balanced"


def test_tier1_decision_stochastic_sampling_with_seed() -> None:
    """Verifies that passing a seed to decide with Tier-1 samples according to softmax distribution."""
    c1 = Candidate(action_id="c1", context_key="ctx", skill_key="s1", predicted=(0.1,) * 8)
    c2 = Candidate(action_id="c2", context_key="ctx", skill_key="s2", predicted=(0.2,) * 8)
    c3 = Candidate(action_id="c3", context_key="ctx", skill_key="s3", predicted=(0.9,) * 8)

    cfg = DevelopmentConfig(use_tier1_decision=True, mellowmax_beta=5.0)
    agent = born("stochastic_agent", seed=10, config=cfg)

    # Running with different seeds explores multiple options
    chosen_actions: set[str] = set()
    for seed in range(50):
        pending_snap = decide(agent, ZERO, (c1, c2, c3), tick=5, seed=seed)
        assert pending_snap.pending is not None
        chosen_actions.add(pending_snap.pending.candidate.action_id)

    # c3 has highest utility, but exploration allows choosing others
    assert "c3" in chosen_actions
    assert len(chosen_actions) >= 2
