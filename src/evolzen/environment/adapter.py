"""Phase 1.1 — Host integration adapter connecting `SocialSandboxEngine` to `evolzen.agents.development`.

Implements the environment boundary specified in `docs/subsystems/environment/README.md`,
`docs/subsystems/agents/motivation.md`, and ADR 0006:
- produces 8 normalized `[-1.0, 1.0]` observable features (`Signal`) from permitted views only;
- dynamically surfaces legal age- and permission-annotated `Candidate` actions from
  `world.capabilities` and local world state (always including `wait`);
- independently re-validates `Decision` proposals on the host side before execution and emits
  host-verified `Outcome` receipts.

Citations: Cook et al. (arXiv:2406.00392) for cultural-transfer motivation context; Tycho
(arXiv:2607.28287) and OPINE-World (arXiv:2607.01531) for interactive transition semantics.
This host-adapter feature and candidate mapping is an EvolZen design choice and remains
empirically untested until Phase 1.1/1.2 integration experiments are run.
"""
from __future__ import annotations

import math

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.development import (
    Candidate,
    Decision,
    DevelopmentConfig,
    Outcome,
    Signal,
)
from evolzen.schemas.transition import Action, ExogenousInput, State, Transition
from evolzen.schemas.world import ActionType, WorldAgentState, WorldState


def _clamp_unit(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"Non-finite observation feature: {value}")
    return round(max(-1.0, min(1.0, value)), 6)


def observe_features(state: State, agent_id: str) -> Signal:
    """Compute eight normalized `[-1.0, 1.0]` features from permitted observations of `agent_id`.

    Coordinate order matches `evolzen.schemas.development.Motive`:
    (pride, greed, lust, envy, gluttony, wrath, sloth, null).
    """
    world = WorldState.from_state(state)
    agent = world.agents.get(agent_id)
    if agent is None:
        raise KeyError(f"Unknown agent_id: {agent_id}")
    loc = world.locations[agent.location_id]
    peers = [
        other
        for other in world.agents.values()
        if other.alive and other.agent_id != agent_id and other.location_id == agent.location_id
    ]
    mean_peer_status = (
        sum(p.status for p in peers) / len(peers) if peers else agent.status
    )
    own_wealth = agent.currency + sum(agent.inventory.values())
    max_peer_wealth = max(
        (p.currency + sum(p.inventory.values()) for p in peers),
        default=own_wealth,
    )
    local_institutions = sum(
        1 for inst in world.institutions.values() if inst.location_id == agent.location_id
    )

    pride = _clamp_unit(mean_peer_status - agent.status)
    greed = _clamp_unit((10 - sum(agent.inventory.values())) / 10.0)
    lust = _clamp_unit(((len(peers) + local_institutions) / 4.0) * 2.0 - 1.0)
    envy = _clamp_unit((max_peer_wealth - own_wealth) / 30.0)
    gluttony = _clamp_unit((0.8 - agent.energy) * 2.0 - 0.3)
    wrath = _clamp_unit((1.0 - loc.shock_factor) * 1.5 - 0.5)
    sloth = _clamp_unit(agent.fatigue * 2.0 - 0.5)
    null = _clamp_unit((agent.energy - 0.6) - agent.fatigue)
    return (pride, greed, lust, envy, gluttony, wrath, sloth, null)


def _build_legal_candidates(world: WorldState, agent: WorldAgentState) -> list[Candidate]:
    """Construct all deterministic host-side `Candidate` records for a living agent."""
    loc = world.locations[agent.location_id]
    context_key = f"{world.world_version}:{loc.location_id}"
    candidates: list[Candidate] = [
        Candidate(
            action_id="wait",
            context_key=context_key,
            skill_key="wait:v1",
            predicted=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.3),
            cost=0.0,
            minimum_age=0,
            permitted=True,
        )
    ]

    for res in sorted(loc.resources):
        available = loc.resources.get(res, 0) > 0 and agent.fatigue < 0.95
        candidates.append(
            Candidate(
                action_id=f"gather:{res}:1",
                context_key=context_key,
                skill_key=f"gather:{res}:v1",
                predicted=(0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05),
                cost=0.02,
                minimum_age=0,
                permitted=available,
            )
        )

    if agent.inventory.get("food", 0) >= 1:
        candidates.append(
            Candidate(
                action_id="consume:food:1",
                context_key=context_key,
                skill_key="consume:food:v1",
                predicted=(0.0, -0.1, 0.0, 0.0, 0.35, 0.0, 0.05, 0.0),
                cost=0.0,
                minimum_age=0,
                permitted=True,
            )
        )

    for neighbor in sorted(loc.neighbors):
        candidates.append(
            Candidate(
                action_id=f"move:{neighbor}",
                context_key=context_key,
                skill_key=f"move:{neighbor}:v1",
                predicted=(0.0, 0.0, 0.15, 0.0, 0.0, 0.0, -0.04, -0.05),
                cost=0.02,
                minimum_age=0,
                permitted=agent.fatigue < 0.95,
            )
        )

    for pkg_id in sorted(world.capabilities):
        pkg = world.capabilities[pkg_id]
        if not (
            pkg.action_type == ActionType.CRAFT
            and pkg.verified_replay
            and pkg.verified_intervention
            and pkg.verified_containment
        ):
            continue
        can_craft = all(
            agent.inventory.get(res, 0) >= req for res, req in pkg.required_resources.items()
        )
        action_id = (
            pkg.package_id if pkg.package_id.startswith("craft:") else f"craft:{pkg.package_id}"
        )
        candidates.append(
            Candidate(
                action_id=action_id,
                context_key=context_key,
                skill_key=pkg.package_id,
                predicted=(0.3, 0.15, 0.0, 0.0, 0.0, 0.0, -0.08, -0.05),
                cost=0.05,
                minimum_age=pkg.min_age,
                permitted=can_craft,
            )
        )

    for res in sorted(loc.capacities):
        can_improve = (
            agent.fatigue < 0.95
            and loc.capacities.get(res, 0) < 200
            and agent.inventory.get("wood", 0) >= 2
            and agent.inventory.get("stone", 0) >= 2
        )
        candidates.append(
            Candidate(
                action_id=f"improve_location:{res}",
                context_key=context_key,
                skill_key=f"improve_location:{res}:v1",
                predicted=(0.25, 0.1, 0.1, 0.0, 0.0, 0.0, -0.08, -0.05),
                cost=0.05,
                minimum_age=0,
                permitted=can_improve,
            )
        )

    candidates.append(
        Candidate(
            action_id="found_institution:guild",
            context_key=context_key,
            skill_key="found_institution:v1",
            predicted=(0.35, 0.1, 0.25, 0.0, 0.0, 0.0, -0.05, -0.05),
            cost=0.05,
            minimum_age=world.adulthood_age,
            permitted=agent.currency >= 5,
        )
    )
    return candidates


def legal_candidates(
    state: State,
    agent_id: str,
    *,
    config: DevelopmentConfig | None = None,
) -> tuple[Candidate, ...]:
    """Generate deterministic `Candidate` proposals for `agent_id` at the current world state."""
    world = WorldState.from_state(state)
    agent = world.agents.get(agent_id)
    if agent is None or not agent.alive:
        raise ValueError(f"Agent {agent_id!r} is missing or dead")
    candidates = _build_legal_candidates(world, agent)
    limit = config.max_candidates if config is not None else 32
    return tuple(candidates[:limit])


def _resolve_craft_params(action_id: str, world: WorldState | None) -> dict[str, str]:
    suffix = action_id.removeprefix("craft:")
    if not suffix:
        raise ValueError(f"Unsupported candidate action_id: {action_id!r}")
    if world is not None:
        if action_id in world.capabilities:
            pkg = world.capabilities[action_id]
            return {"package_id": pkg.package_id, "kind": pkg.output_kind}
        if suffix in world.capabilities:
            pkg = world.capabilities[suffix]
            return {"package_id": pkg.package_id, "kind": pkg.output_kind}
        for pkg_id in sorted(world.capabilities):
            pkg = world.capabilities[pkg_id]
            if (
                pkg.action_type == ActionType.CRAFT
                and pkg.output_kind == suffix
                and pkg.verified_replay
                and pkg.verified_intervention
                and pkg.verified_containment
            ):
                return {"package_id": pkg.package_id, "kind": pkg.output_kind}
        return {"kind": suffix}

    if ":" in suffix:
        kind = suffix.split(":", 1)[0]
        return {"package_id": action_id, "kind": kind}
    return {"kind": suffix}


def action_from_candidate(
    action_id: str,
    agent_id: str,
    *,
    state: State | None = None,
) -> Action:
    """Translate a host-issued `Candidate.action_id` into an environment `Action`."""
    if action_id == "wait":
        return Action(agent_id=agent_id, action_type=ActionType.WAIT)
    parts = action_id.split(":")
    verb = parts[0]
    if verb == "gather" and len(parts) == 3:
        return Action(
            agent_id=agent_id,
            action_type=ActionType.GATHER,
            params={"resource": parts[1], "amount": int(parts[2])},
        )
    if verb == "consume" and len(parts) == 3:
        return Action(
            agent_id=agent_id,
            action_type=ActionType.CONSUME,
            params={"resource": parts[1], "amount": int(parts[2])},
        )
    if verb == "move" and len(parts) == 2:
        return Action(
            agent_id=agent_id,
            action_type=ActionType.MOVE,
            params={"target_location": parts[1]},
        )
    if verb == "craft" and len(parts) >= 2:
        world = WorldState.from_state(state) if state is not None else None
        return Action(
            agent_id=agent_id,
            action_type=ActionType.CRAFT,
            params=_resolve_craft_params(action_id, world),
        )
    if verb == "found_institution" and len(parts) == 2:
        return Action(
            agent_id=agent_id,
            action_type=ActionType.FOUND_INSTITUTION,
            params={"name": parts[1], "seed_currency": 5},
        )
    if verb == "improve_location" and len(parts) in (1, 2):
        resource = parts[1] if len(parts) == 2 and parts[1] else "food"
        return Action(
            agent_id=agent_id,
            action_type=ActionType.IMPROVE_LOCATION,
            params={"target_resource": resource},
        )
    raise ValueError(f"Unsupported candidate action_id: {action_id!r}")


def execute_decision(
    engine: SocialSandboxEngine,
    state: State,
    decision: Decision,
    *,
    exogenous_input: ExogenousInput | None = None,
    seed: int | None = None,
) -> tuple[Transition, Outcome]:
    """Host-validate and execute a developmental `Decision`, returning `(Transition, Outcome)`."""
    world = WorldState.from_state(state)
    agent = world.agents.get(decision.agent_id)
    if agent is None or not agent.alive:
        raise ValueError(f"Agent {decision.agent_id!r} is missing or dead")
    if decision.tick != world.tick:
        raise ValueError(
            f"Stale decision tick {decision.tick} does not match world tick {world.tick}"
        )

    host_candidates = {c.action_id: c for c in _build_legal_candidates(world, agent)}
    host_candidate = host_candidates.get(decision.candidate.action_id)
    if host_candidate is None:
        raise ValueError(
            f"Candidate action {decision.candidate.action_id!r} is not legal in current state"
        )
    if not host_candidate.permitted or not decision.candidate.permitted:
        raise ValueError(
            f"Candidate action {decision.candidate.action_id!r} is not permitted"
        )
    age = world.tick - agent.born_at
    if age < host_candidate.minimum_age:
        raise ValueError(
            f"Agent {decision.agent_id!r} age {age} is below minimum_age "
            f"{host_candidate.minimum_age} for {decision.candidate.action_id!r}"
        )

    action = action_from_candidate(decision.candidate.action_id, decision.agent_id, state=state)
    transition = engine.step(state, action, exogenous_input=exogenous_input, seed=seed)
    raw_rewards = transition.emission.data.get("rewards", [0.0] * 8)
    rewards = tuple(float(v) for v in raw_rewards)
    if len(rewards) != 8:
        raise RuntimeError(f"Expected 8 reward coordinates, got {len(rewards)}")
    next_tick = int(transition.emission.data["tick"])
    outcome = Outcome(
        agent_id=decision.agent_id,
        sequence=decision.sequence,
        tick=next_tick,
        action_id=decision.candidate.action_id,
        evidence_id=str(transition.transition_id),
        rewards=rewards,
        verified=bool(transition.emission.data.get("invariant_passed", False)),
    )
    return transition, outcome
