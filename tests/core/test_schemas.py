"""Phase 0 sanity tests: shared schemas construct and validate correctly."""
from evolzen.schemas import Action, DriveVector, Emission, Manual, State, Transition
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


def test_drive_vector_as_vector_order_is_stable() -> None:
    dv = DriveVector(resource_seeking=0.5, status=0.1, aggression=-0.3)
    assert dv.as_vector() == [0.5, 0.1, 0.0, -0.3, 0.0]


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
