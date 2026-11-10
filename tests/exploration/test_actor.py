from evolzen.exploration.actor import Actor
from evolzen.schemas.transition import State


def test_choose_probe_picks_highest_ontology_error() -> None:
    states = [State(data={"id": i}) for i in range(3)]
    scores = {states[0].state_id: 0.1, states[1].state_id: 0.9, states[2].state_id: 0.4}
    actor = Actor(ontology_error_fn=lambda s: scores[s.state_id])
    chosen = actor.choose_probe(states)
    assert chosen is states[1]
