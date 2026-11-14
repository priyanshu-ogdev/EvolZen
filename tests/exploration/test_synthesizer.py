"""Unit tests for CandidateRule and Synthesizer implementations (Phase 1.4)."""
from __future__ import annotations

import pytest

from evolzen.exploration.synthesizer import CandidateRule, TemplateRuleSynthesizer
from evolzen.schemas.transition import Action, Emission, State, Transition


def test_candidate_rule_dataclass() -> None:
    rule = CandidateRule(rule_id="r1", code="print(1)", explains=["t1", "t2"])
    assert rule.rule_id == "r1"
    assert rule.code == "print(1)"
    assert rule.explains == ["t1", "t2"]


def test_template_rule_synthesizer_single_pattern() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited"}),
        next_state=State(data={"tick": 1}),
    )
    t2 = Transition(
        state=State(data={"tick": 1}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited"}),
        next_state=State(data={"tick": 2}),
    )

    synth = TemplateRuleSynthesizer(rule_prefix="test_rule")
    rule = synth.propose([t1, t2])
    assert rule.rule_id == "test_rule-1"
    assert str(t1.transition_id) in rule.explains
    assert str(t2.transition_id) in rule.explains
    assert "def predict" in rule.code


def test_template_rule_synthesizer_multi_action_mapping() -> None:
    t1 = Transition(
        state=State(data={"tick": 0}),
        action=Action(agent_id="a1", action_type="wait"),
        emission=Emission(data={"accepted": True, "reason": "waited"}),
        next_state=State(data={"tick": 1}),
    )
    t2 = Transition(
        state=State(data={"tick": 1}),
        action=Action(agent_id="a1", action_type="gather"),
        emission=Emission(data={"accepted": True, "reason": "gathered"}),
        next_state=State(data={"tick": 2}),
    )

    synth = TemplateRuleSynthesizer(rule_prefix="multi_rule")
    rule = synth.propose([t1, t2])
    assert rule.rule_id == "multi_rule-1"
    assert "mapping" in rule.code


def test_template_rule_synthesizer_empty_raises() -> None:
    synth = TemplateRuleSynthesizer()
    with pytest.raises(ValueError, match="Cannot synthesize rule from empty transitions"):
        synth.propose([])
