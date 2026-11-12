"""Unit tests for the unified Agent class and developmental integration."""
from __future__ import annotations

from evolzen.agents.agent import Agent
from evolzen.environment.adapter import (
    execute_decision,
    legal_candidates,
    observe_features,
)
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import Candidate, DevelopmentConfig, Outcome
from evolzen.schemas.world import WorldState


def test_unified_agent_lifecycle_and_decision() -> None:
    profile = AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-0",
        roles=("gatherer",),
        adopted_norms=("conserve",),
    )
    agent = Agent.create(profile, seed=42, tick=0)
    assert agent.agent_id == "agent-0"
    assert agent.age == 0
    assert agent.tick == 0

    engine = SocialSandboxEngine(default_seed=42, num_agents=2)
    state = engine.reset(seed=42)

    features = observe_features(state, "agent-0")
    candidates = legal_candidates(state, "agent-0")

    decision = agent.decide(features, candidates, WorldState.from_state(state).tick)
    assert decision.agent_id == "agent-0"
    assert decision.candidate.permitted is True

    transition, outcome = execute_decision(engine, state, decision)
    assert outcome.verified is True

    agent.observe(outcome)
    assert len(agent.development.recent) == 1
    assert agent.tick == WorldState.from_state(transition.next_state).tick


def test_agent_parental_teaching() -> None:
    cfg = DevelopmentConfig(adolescence=10, adulthood=20, elderhood=50, lifespan=100)
    p_profile = AgentProfile(agent_id="parent-0", lineage_id="lineage-alpha")
    c_profile = AgentProfile(agent_id="child-0", lineage_id="lineage-alpha", parents=("parent-0",))

    parent = Agent.create(p_profile, seed=1, tick=0, config=cfg)
    parent.advance(20)
    assert parent.stage.value == "adult"

    # Parent performs an action and observes verified outcome to establish grounded knowledge
    candidate = Candidate(
        action_id="forage",
        context_key="context:world",
        skill_key="skill:forage",
        permitted=True,
    )
    parent.decide((0.1,) * 8, (candidate,), 20)
    outcome = Outcome(
        agent_id="parent-0",
        sequence=1,
        tick=20,
        action_id="forage",
        evidence_id="ev-grounded-1",
        rewards=(0.2,) * 8,
        verified=True,
    )
    parent.observe(outcome)
    assert len(parent.development.knowledge) == 1

    # Now advance to tick 25 and birth child
    parent.advance(25)
    child = Agent.create(c_profile, seed=2, tick=25, config=cfg, parents=(parent,))
    assert child.stage.value == "child"

    parent.teach(child, "context:world", "skill:forage", 25)
    assert len(child.development.lessons) == 1
    assert child.development.lessons[0].estimate.skill_key == "skill:forage"
