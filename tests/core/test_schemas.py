"""Phase 0 / Phase 1.2 sanity tests: shared schemas construct and validate correctly."""
from evolzen.schemas import Action, AgentProfile, Emission, Manual, State, Transition
from evolzen.schemas.manual import ManualEntry, ManualEntryStatus


def test_transition_roundtrip() -> None:
    t = Transition(
        state=State(data={"round": 1}),
        action=Action(agent_id="agent-0", action_type="propose", params={"offer": 5}),
        emission=Emission(data={"accepted": False}),
        next_state=State(data={"round": 2}),
    )
    dumped = t.model_dump_json()
    restored = Transition.model_validate_json(dumped)
    assert restored.action.agent_id == "agent-0"
    assert restored.next_state.data["round"] == 2


def test_agent_profile_roundtrip_and_descriptor_stability() -> None:
    profile = AgentProfile(
        agent_id="agent-0",
        lineage_id="lineage-alpha",
        generation=1,
        parents=("agent-root",),
        roles=("gatherer", "builder"),
        institutional_affiliations=("guild-craft",),
        adopted_norms=("norm-conserve",),
        memory_horizon=64,
        behavioral_descriptor=(0.8, 0.4, -0.2, 0.1, 0.9),
    )
    assert profile.agent_id == "agent-0"
    assert profile.generation == 1
    assert profile.descriptor_vector() == [0.8, 0.4, -0.2, 0.1, 0.9]
    dumped = profile.model_dump_json()
    restored = AgentProfile.model_validate_json(dumped)
    assert restored == profile


def test_manual_active_beliefs_excludes_falsified() -> None:
    manual = Manual(situation_key="negotiation:round-1")
    manual.add_entry(ManualEntry(text="Offers below 3 are always rejected.", written_by="agent-0"))
    manual.add_entry(
        ManualEntry(
            text="Offers below 3 are sometimes accepted under time pressure.",
            status=ManualEntryStatus.FALSIFIED,
            written_by="agent-1",
        )
    )
    active = manual.active_beliefs()
    assert len(active) == 1
    assert active[0].status == ManualEntryStatus.HYPOTHESIS
