from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.rule_library import RuleLibrary


def test_spawn_if_novel_adds_when_nothing_explains_it() -> None:
    lib = RuleLibrary()
    rule = CandidateRule(rule_id="r1", code="def f(): pass", explains=["t1"])
    spawned = lib.spawn_if_novel(rule, routing_confidence_fn=lambda new, existing: 0.0)
    assert spawned is True
    assert len(lib) == 1


def test_spawn_if_novel_skips_when_existing_rule_explains_it() -> None:
    lib = RuleLibrary()
    first = CandidateRule(rule_id="r1", code="def f(): pass", explains=["t1"])
    lib.spawn_if_novel(first, routing_confidence_fn=lambda new, existing: 0.0)

    second = CandidateRule(rule_id="r2", code="def f(): pass", explains=["t2"])
    spawned = lib.spawn_if_novel(second, routing_confidence_fn=lambda new, existing: 0.9)
    assert spawned is False
    assert len(lib) == 1  # unchanged — existing entry is never overwritten
