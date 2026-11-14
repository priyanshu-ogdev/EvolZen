"""Unit tests for Verifier, sandboxed replay, and capability promotion (Phase 1.4)."""
from __future__ import annotations

from evolzen.containment.governance import CapabilityGovernor
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.exploration.synthesizer import CandidateRule
from evolzen.exploration.verifier import Verifier, build_runner_code
from evolzen.schemas.transition import Action, Emission, State, Transition
from evolzen.schemas.world import ActionType, WorldState
from tests.containment.conftest import MockSandbox


def test_build_runner_code() -> None:
    code = "def predict(state, action, ex=None, seed=None):\n    return {'emission': {'accepted': True}}"
    runner = build_runner_code(code)
    assert "def predict" in runner
    assert "input_data" in runner
    assert "print(json.dumps" in runner


def test_verifier_exact_match_success() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited 1 tick"}),
        next_state=State(data={"tick": 1}),
    )
    t2 = Transition(
        state=State(data={"tick": 1}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited 1 tick"}),
        next_state=State(data={"tick": 2}),
    )

    code = (
        "def predict(state, action, ex=None, seed=None):\n"
        "    return {'emission': {'accepted': True, 'reason': 'waited 1 tick'}}\n"
    )
    rule = CandidateRule(rule_id="rule-wait", code=code, explains=[str(t1.transition_id)])

    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    report = verifier.verify_with_report(rule, [t1, t2])
    assert report.passed is True
    assert report.exact_matches == 2
    assert report.mismatches == 0
    assert report.verified_replay is True
    assert report.verified_containment is True
    assert len(sandbox.call_history) == 2


def test_verifier_detects_mismatch() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited 1 tick"}),
        next_state=State(data={"tick": 1}),
    )

    # Rule predicts wrong reason
    code = (
        "def predict(state, action, ex=None, seed=None):\n"
        "    return {'emission': {'accepted': True, 'reason': 'wrong reason'}}\n"
    )
    rule = CandidateRule(rule_id="rule-wrong", code=code, explains=[str(t1.transition_id)])

    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    report = verifier.verify_with_report(rule, [t1])
    assert report.passed is False
    assert report.mismatches == 1
    assert report.exact_matches == 0
    assert "emission mismatch" in report.details[0]


def test_verifier_detects_timeout() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True}),
        next_state=State(data={"tick": 1}),
    )
    rule = CandidateRule(rule_id="rule-timeout", code="pass", explains=[str(t1.transition_id)])

    sandbox = MockSandbox(simulate_timeout=True)
    verifier = Verifier(sandbox=sandbox)

    report = verifier.verify_with_report(rule, [t1])
    assert report.passed is False
    assert report.timeouts == 1


def test_verifier_detects_resource_ceiling_hit() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True}),
        next_state=State(data={"tick": 1}),
    )
    rule = CandidateRule(rule_id="rule-oom", code="pass", explains=[str(t1.transition_id)])

    sandbox = MockSandbox(simulate_oom=True)
    verifier = Verifier(sandbox=sandbox)

    report = verifier.verify_with_report(rule, [t1])
    assert report.passed is False
    assert report.resource_ceiling_hits == 1


def test_verifier_empty_transitions() -> None:
    rule = CandidateRule(rule_id="rule-empty", code="pass", explains=[])
    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    report = verifier.verify_with_report(rule, [])
    assert report.passed is False
    assert report.transitions_tested == 0


def test_verifier_counterfactual_intervention() -> None:
    engine = SocialSandboxEngine(default_seed=42, num_agents=2)
    s0 = engine.reset(seed=42, run_id="intervention-test")

    action = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    # The actual emission of WAIT in SocialSandboxEngine:
    actual_trans = engine.step(s0, action, seed=42)

    code = (
        "def predict(state, action, ex=None, seed=None):\n"
        f"    return {{'emission': {actual_trans.emission.data!r}}}\n"
    )
    rule = CandidateRule(rule_id="rule-wait-intervention", code=code, explains=[])

    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    ok = verifier.verify_intervention(rule, engine, s0, action, seed=42)
    assert ok is True


def test_verifier_promote_to_capability_package() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="craft"),
        emission=Emission(data={"accepted": True, "reason": "crafted item"}),
        next_state=State(data={"tick": 1}),
    )

    code = (
        "def predict(state, action, ex=None, seed=None):\n"
        "    return {'emission': {'accepted': True, 'reason': 'crafted item'}}\n"
    )
    rule = CandidateRule(rule_id="cap-craft-tool", code=code, explains=[str(t1.transition_id)])

    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    pkg = verifier.promote_to_capability_package(
        rule,
        [t1],
        output_kind="iron_tool",
        action_type=ActionType.CRAFT,
        required_resources={"wood": 2, "iron": 1},
    )

    assert pkg is not None
    assert pkg.package_id == "cap-craft-tool"
    assert pkg.output_kind == "iron_tool"
    assert pkg.verified_replay is True
    assert pkg.verified_intervention is True
    assert pkg.verified_containment is True
    assert len(pkg.evidence_id) > 0

    # CapabilityGovernor accepts the promoted package
    governor = CapabilityGovernor()
    assert governor.verify_capability_package(pkg) is True


def test_verifier_promoted_package_registered_in_engine() -> None:
    engine = SocialSandboxEngine(default_seed=50, num_agents=2)
    s0 = engine.reset(seed=50, run_id="reg-cap-test")

    t1 = Transition(
        state=s0,
        action=Action(agent_id="agent-0", action_type=ActionType.WAIT),
        emission=Emission(data={"accepted": True, "reason": "waited 1 tick", "rewards": [0.0] * 8}),
        next_state=s0,
    )

    code = (
        "def predict(state, action, ex=None, seed=None):\n"
        "    return {'emission': {'accepted': True, 'reason': 'waited 1 tick', 'rewards': [0.0] * 8}}\n"
    )
    rule = CandidateRule(rule_id="cap-gather-efficiency", code=code, explains=[str(t1.transition_id)])

    sandbox = MockSandbox()
    verifier = Verifier(sandbox=sandbox)

    pkg = verifier.promote_to_capability_package(rule, [t1], output_kind="efficiency_boost")
    assert pkg is not None

    # Register in engine via ActionType.REGISTER_CAPABILITY
    reg_action = Action(
        agent_id="agent-0",
        action_type=ActionType.REGISTER_CAPABILITY,
        params={"package": pkg.model_dump(), "evidence_id": pkg.evidence_id},
    )
    trans = engine.step(s0, reg_action, seed=50)
    assert trans.emission.data.get("accepted") is True
    assert "registered verified capability" in trans.emission.data.get("reason", "")

    w_next = WorldState.from_state(trans.next_state)
    assert pkg.package_id in w_next.capabilities
