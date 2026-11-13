"""Phase 1.1 — Persistent, event-sourced social sandbox engine.

Implements `Environment` (Phase 0 protocol) and `PersistentEnvironment` with a concrete
`SocialSandboxEngine` satisfying the normative transition contract:

    (state_t, action_t, exogenous_input_t, seed) -> (emission_t, state_{t+1})

Design authority: docs/phases/1.1-environment.md, ADR 0004, ADR 0005.
Citations:
- Weyns et al. (JAAMAS 2007, doi:10.1007/s10458-006-0012-0) for the environment as a first-class programmatic abstraction;
- Zeigler et al. (Academic Press 2000) for discrete-event simulation specification (DEVS) transition/emission formalisms;
- Tycho (arXiv:2607.28287) for seeded, typed interactive transition systems;
- OPINE-World (arXiv:2607.01531) for ontology-error-guided exploration over typed entities;
- Executable World Models (arXiv:2605.05138) for verifiable executable world transitions;
- Sequential Social Dilemmas (AAMAS 2017, arXiv:1702.03037), Concordia (arXiv:2312.03664), and Melting Pot 2.0 (NeurIPS 2023, arXiv:2211.13746)
  for multi-agent social dilemma dynamics, resource renewal, and spatial/social mediation;
- The AI Economist (Science Advances 2022, doi:10.1126/sciadv.abk2607) for multi-agent dynamic economies and taxation;
- PettingZoo (NeurIPS 2021, arXiv:2009.14471) for multi-agent environment interface compatibility;
- Procgen (ICML 2020, arXiv:1912.01588) for seed-stratified procedural world generation;
- OMNI-EPIC (ICLR 2025, arXiv:2405.15568) as the contrastive boundary: EvolZen rejects arbitrary
  engine code mutation and admits only typed, replay-, intervention-, and
  containment-verified `CapabilityPackage` definitions.

The social-sandbox mechanics themselves are an EvolZen design choice and remain empirically
untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from evolzen.environment.growth import extract_growth_events
from evolzen.environment.invariants import check_invariants
from evolzen.environment.world_state import build_default_world
from evolzen.schemas.transition import Action, Emission, ExogenousInput, State, Transition
from evolzen.schemas.world import (
    ActionType,
    ArtifactRecord,
    CapabilityPackage,
    ContractRecord,
    InstitutionRecord,
    NormRecord,
    ResourceAccounting,
    WorldAgentState,
    WorldSnapshot,
    WorldState,
    canonical_json,
)


class Environment(Protocol):
    """Protocol every Phase 1.1 domain implementation must satisfy."""

    def reset(self) -> State:
        """Reset to an initial state and return it."""
        ...

    def step(self, state: State, action: Action) -> Transition:
        """Apply `action` to `state`, returning the full logged transition."""
        ...

    def is_terminal(self, state: State) -> bool:
        """Whether `state` ends an episode."""
        ...


class PersistentEnvironment(Environment, Protocol):
    """Extended Phase 1.1 protocol supporting snapshots, restore, and exogenous inputs."""

    def step(
        self,
        state: State,
        action: Action,
        exogenous_input: ExogenousInput | None = None,
        seed: int | None = None,
    ) -> Transition:
        """Apply `(action, exogenous_input, seed)` deterministically to `state`."""
        ...

    def snapshot(
        self,
        state: State,
        *,
        snapshot_id: str | None = None,
        parent_snapshot_id: str | None = None,
    ) -> WorldSnapshot:
        """Create a versioned immutable snapshot from `state`."""
        ...

    def restore(self, snapshot: WorldSnapshot) -> State:
        """Restore a validated `State` from `snapshot`."""
        ...


@dataclass(frozen=True)
class _StepOutcome:
    world: WorldState
    accepted: bool
    reason: str
    rewards: tuple[float, ...]


_HandlerFn = Callable[[WorldState, WorldAgentState, Action, int], _StepOutcome]

_LOCATION_IMPROVE_COST: dict[str, int] = {"wood": 2, "stone": 2}
_LOCATION_CAPACITY_INCREMENT = 10
_MAX_LOCATION_CAPACITY = 200


def _resolve_identifier(
    params: dict[str, Any],
    key: str,
    default: str | None = None,
) -> tuple[str | None, str | None]:
    """Extract and validate a non-empty bounded `Identifier` string from `params`."""
    if key not in params:
        if default is None:
            return None, f"{key} is required"
        return default, None
    raw = params[key]
    if not isinstance(raw, str):
        return None, f"{key} must be a non-empty string"
    cleaned = raw.strip()
    if not cleaned or len(cleaned) > 128:
        return None, f"{key} must be a non-empty string of at most 128 characters"
    return cleaned, None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_rewards(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(round(_clamp(v, -1.0, 1.0), 6) for v in values)


def _reject(world: WorldState, reason: str) -> _StepOutcome:
    return _StepOutcome(
        world=world,
        accepted=False,
        reason=reason,
        rewards=(-0.1, 0.0, 0.0, 0.0, 0.0, -0.2, 0.0, 0.0),
    )


def _replace_agent(world: WorldState, agent: WorldAgentState) -> WorldState:
    agents = dict(world.agents)
    agents[agent.agent_id] = agent
    return world.model_copy(update={"agents": agents})


def _handle_wait(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    updated = actor.model_copy(
        update={
            "fatigue": round(_clamp(actor.fatigue - 0.2, 0.0, 1.0), 6),
            "energy": round(_clamp(actor.energy + 0.02, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world, updated),
        accepted=True,
        reason="rested",
        rewards=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.3),
    )


def _handle_gather(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    if actor.fatigue >= 0.95:
        return _reject(world, "actor too fatigued to gather")
    raw_resource = action.params.get("resource", "food")
    if not isinstance(raw_resource, str) or not raw_resource.strip():
        return _reject(world, "resource must be a non-empty string")
    resource = raw_resource.strip()
    amount = action.params.get("amount", 1)
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
        return _reject(world, "gather amount must be a positive integer")
    loc = world.locations[actor.location_id]
    available = loc.resources.get(resource, 0)
    if available < amount:
        return _reject(world, f"insufficient {resource} at {loc.location_id}")

    loc_resources = dict(loc.resources)
    loc_resources[resource] = available - amount
    locations = dict(world.locations)
    locations[loc.location_id] = loc.model_copy(update={"resources": loc_resources})

    inv = dict(actor.inventory)
    inv[resource] = inv.get(resource, 0) + amount
    updated = actor.model_copy(
        update={
            "inventory": inv,
            "fatigue": round(_clamp(actor.fatigue + 0.05, 0.0, 1.0), 6),
            "energy": round(_clamp(actor.energy - 0.02, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    next_world = _replace_agent(world.model_copy(update={"locations": locations}), updated)
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"gathered {amount} {resource}",
        rewards=(0.05, 0.25, 0.0, 0.0, 0.05, 0.0, -0.05, -0.05),
    )


def _handle_move(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    if actor.fatigue >= 0.95:
        return _reject(world, "actor too fatigued to move")
    raw_target = action.params.get("target_location", "")
    if not isinstance(raw_target, str):
        return _reject(world, "target_location must be a string")
    target = raw_target.strip()
    loc = world.locations[actor.location_id]
    if target not in loc.neighbors or target not in world.locations:
        return _reject(world, f"location {target!r} is not adjacent to {actor.location_id}")
    updated = actor.model_copy(
        update={
            "location_id": target,
            "fatigue": round(_clamp(actor.fatigue + 0.04, 0.0, 1.0), 6),
            "energy": round(_clamp(actor.energy - 0.02, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    peers = sum(1 for a in world.agents.values() if a.alive and a.location_id == target)
    return _StepOutcome(
        world=_replace_agent(world, updated),
        accepted=True,
        reason=f"moved to {target}",
        rewards=(0.0, 0.0, 0.1 * min(peers, 3), 0.0, 0.0, 0.0, -0.04, -0.05),
    )


def _handle_consume(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_resource = action.params.get("resource", "food")
    if not isinstance(raw_resource, str) or not raw_resource.strip():
        return _reject(world, "resource must be a non-empty string")
    resource = raw_resource.strip()
    amount = action.params.get("amount", 1)
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
        return _reject(world, "consume amount must be a positive integer")
    held = actor.inventory.get(resource, 0)
    if held < amount:
        return _reject(world, f"insufficient {resource} in inventory")
    inv = dict(actor.inventory)
    inv[resource] = held - amount
    consumed = dict(world.accounting.consumed_or_decayed)
    consumed[resource] = consumed.get(resource, 0) + amount
    accounting = world.accounting.model_copy(update={"consumed_or_decayed": consumed})
    updated = actor.model_copy(
        update={
            "inventory": inv,
            "energy": round(_clamp(actor.energy + 0.15 * amount, 0.0, 1.0), 6),
            "fatigue": round(_clamp(actor.fatigue - 0.05, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    next_world = _replace_agent(world.model_copy(update={"accounting": accounting}), updated)
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"consumed {amount} {resource}",
        rewards=(0.0, -0.1, 0.0, 0.0, 0.35, 0.0, 0.05, 0.0),
    )


def _handle_craft(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    if "package_id" in action.params and action.params["package_id"] is not None:
        raw_pkg_id = action.params["package_id"]
        if not isinstance(raw_pkg_id, str) or not raw_pkg_id.strip():
            return _reject(world, "package_id must be a non-empty string")
        package_id = raw_pkg_id.strip()
        pkg = world.capabilities.get(package_id)
        if pkg is None:
            return _reject(world, f"unknown capability package {package_id}")
    else:
        kind, kind_err = _resolve_identifier(action.params, "kind", default="tool")
        if kind_err is not None or kind is None:
            return _reject(world, kind_err or "invalid craft kind")
        matches = sorted(
            (
                p
                for p in world.capabilities.values()
                if p.action_type == ActionType.CRAFT and p.output_kind == kind
            ),
            key=lambda p: p.package_id,
        )
        if not matches:
            return _reject(world, f"no verified capability package registered for craft kind {kind!r}")
        verified_matches = [
            p
            for p in matches
            if p.verified_replay and p.verified_intervention and p.verified_containment
        ]
        if not verified_matches:
            return _reject(world, f"capability package for craft kind {kind!r} is not verified")
        age = next_tick - actor.born_at
        eligible = [p for p in verified_matches if age >= p.min_age]
        pkg = eligible[0] if eligible else verified_matches[0]

    if pkg.action_type != ActionType.CRAFT:
        return _reject(world, f"capability package {pkg.package_id} is not a craft capability")
    if not (pkg.verified_replay and pkg.verified_intervention and pkg.verified_containment):
        return _reject(world, f"capability package {pkg.package_id} is not verified")
    if next_tick - actor.born_at < pkg.min_age:
        return _reject(world, f"actor below minimum age {pkg.min_age} for {pkg.package_id}")

    kind = pkg.output_kind
    recipe = dict(pkg.required_resources)

    inv = dict(actor.inventory)
    for res, req in recipe.items():
        if inv.get(res, 0) < req:
            return _reject(world, f"insufficient {res} to craft {kind}")
    for res, req in recipe.items():
        inv[res] = inv[res] - req

    artifact_id, art_err = _resolve_identifier(
        action.params,
        "artifact_id",
        default=f"artifact-{world.step_index + 1}-{actor.agent_id}",
    )
    if art_err is not None or artifact_id is None:
        return _reject(world, art_err or "invalid artifact_id")
    if artifact_id in world.artifacts:
        return _reject(world, f"duplicate artifact_id {artifact_id}")

    artifact = ArtifactRecord(
        artifact_id=artifact_id,
        kind=kind,
        creator_id=actor.agent_id,
        owner_id=actor.agent_id,
        location_id=actor.location_id,
        created_tick=next_tick,
        recipe_resources=recipe,
    )
    artifacts = dict(world.artifacts)
    artifacts[artifact_id] = artifact
    skill = f"craft:{kind}"
    skills = actor.skills if skill in actor.skills else (*actor.skills, skill)
    updated = actor.model_copy(
        update={
            "inventory": inv,
            "skills": skills,
            "status": round(actor.status + 0.15, 6),
            "fatigue": round(_clamp(actor.fatigue + 0.08, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    next_world = _replace_agent(world.model_copy(update={"artifacts": artifacts}), updated)
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"crafted {kind} ({artifact_id})",
        rewards=(0.3, 0.15, 0.0, 0.0, 0.0, 0.0, -0.08, -0.05),
    )


def _handle_trade(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_cp = action.params.get("counterparty_id", "")
    if not isinstance(raw_cp, str) or not raw_cp.strip():
        return _reject(world, f"invalid counterparty {raw_cp!r}")
    counterparty_id = raw_cp.strip()
    counterparty = world.agents.get(counterparty_id)
    if counterparty is None or not counterparty.alive or counterparty_id == actor.agent_id:
        return _reject(world, f"invalid counterparty {counterparty_id!r}")
    if counterparty.location_id != actor.location_id:
        return _reject(world, "trade requires co-located agents")
    resource, res_err = _resolve_identifier(action.params, "offer_resource", default="food")
    if res_err is not None or resource is None:
        return _reject(world, res_err or "invalid offer_resource")
    qty = action.params.get("offer_qty", 1)
    price = action.params.get("price", 2)
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
        return _reject(world, "offer_qty must be a positive integer")
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        return _reject(world, "price must be a non-negative integer")
    if actor.inventory.get(resource, 0) < qty:
        return _reject(world, f"insufficient {resource} for trade")
    if counterparty.currency < price:
        return _reject(world, f"counterparty {counterparty_id} lacks currency {price}")

    actor_inv = dict(actor.inventory)
    actor_inv[resource] = actor_inv[resource] - qty
    cp_inv = dict(counterparty.inventory)
    cp_inv[resource] = cp_inv.get(resource, 0) + qty

    updated_actor = actor.model_copy(
        update={
            "inventory": actor_inv,
            "currency": actor.currency + price,
            "status": round(actor.status + 0.05, 6),
            "last_action_tick": next_tick,
        }
    )
    updated_cp = counterparty.model_copy(
        update={
            "inventory": cp_inv,
            "currency": counterparty.currency - price,
        }
    )
    next_world = _replace_agent(_replace_agent(world, updated_actor), updated_cp)
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"traded {qty} {resource} to {counterparty_id} for {price}",
        rewards=(0.1, 0.25, 0.15, 0.0, 0.0, 0.0, -0.02, -0.02),
    )


def _handle_propose_contract(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_cp = action.params.get("counterparty_id", "")
    if not isinstance(raw_cp, str) or not raw_cp.strip():
        return _reject(world, f"invalid contract counterparty {raw_cp!r}")
    counterparty_id = raw_cp.strip()
    counterparty = world.agents.get(counterparty_id)
    if counterparty is None or not counterparty.alive or counterparty_id == actor.agent_id:
        return _reject(world, f"invalid contract counterparty {counterparty_id!r}")
    offer_res, offer_err = _resolve_identifier(action.params, "offer_resource", default="wood")
    if offer_err is not None or offer_res is None:
        return _reject(world, offer_err or "invalid offer_resource")
    offer_qty = action.params.get("offer_qty", 1)
    req_res, req_err = _resolve_identifier(action.params, "request_resource", default="food")
    if req_err is not None or req_res is None:
        return _reject(world, req_err or "invalid request_resource")
    req_qty = action.params.get("request_qty", 1)
    if (
        isinstance(offer_qty, bool)
        or not isinstance(offer_qty, int)
        or offer_qty < 1
        or isinstance(req_qty, bool)
        or not isinstance(req_qty, int)
        or req_qty < 1
    ):
        return _reject(world, "contract quantities must be positive integers")
    contract_id, cid_err = _resolve_identifier(
        action.params,
        "contract_id",
        default=f"contract-{world.step_index + 1}-{actor.agent_id}",
    )
    if cid_err is not None or contract_id is None:
        return _reject(world, cid_err or "invalid contract_id")
    if contract_id in world.contracts:
        return _reject(world, f"duplicate contract_id {contract_id}")
    contract = ContractRecord(
        contract_id=contract_id,
        proposer_id=actor.agent_id,
        counterparty_id=counterparty_id,
        offer_resource=offer_res,
        offer_qty=offer_qty,
        request_resource=req_res,
        request_qty=req_qty,
        status="open",
        created_tick=next_tick,
    )
    contracts = dict(world.contracts)
    contracts[contract_id] = contract
    updated = actor.model_copy(update={"last_action_tick": next_tick})
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"contracts": contracts}), updated),
        accepted=True,
        reason=f"proposed contract {contract_id}",
        rewards=(0.1, 0.1, 0.15, 0.0, 0.0, 0.0, -0.02, 0.0),
    )


def _handle_fulfill_contract(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_cid = action.params.get("contract_id", "")
    if not isinstance(raw_cid, str) or not raw_cid.strip():
        return _reject(world, f"contract {raw_cid!r} is not open")
    contract_id = raw_cid.strip()
    contract = world.contracts.get(contract_id)
    if contract is None or contract.status != "open":
        return _reject(world, f"contract {contract_id!r} is not open")
    if actor.agent_id != contract.counterparty_id:
        return _reject(world, "only counterparty may fulfill contract")
    proposer = world.agents.get(contract.proposer_id)
    if proposer is None or not proposer.alive:
        return _reject(world, "contract proposer unavailable")
    if proposer.inventory.get(contract.offer_resource, 0) < contract.offer_qty:
        return _reject(world, "proposer lacks offered resource")
    if actor.inventory.get(contract.request_resource, 0) < contract.request_qty:
        return _reject(world, "counterparty lacks requested resource")

    p_inv = dict(proposer.inventory)
    c_inv = dict(actor.inventory)
    p_inv[contract.offer_resource] -= contract.offer_qty
    p_inv[contract.request_resource] = p_inv.get(contract.request_resource, 0) + contract.request_qty
    c_inv[contract.request_resource] -= contract.request_qty
    c_inv[contract.offer_resource] = c_inv.get(contract.offer_resource, 0) + contract.offer_qty

    contracts = dict(world.contracts)
    contracts[contract_id] = contract.model_copy(update={"status": "fulfilled"})
    updated_actor = actor.model_copy(
        update={
            "inventory": c_inv,
            "status": round(actor.status + 0.1, 6),
            "last_action_tick": next_tick,
        }
    )
    updated_proposer = proposer.model_copy(
        update={"inventory": p_inv, "status": round(proposer.status + 0.1, 6)}
    )
    next_world = _replace_agent(
        _replace_agent(world.model_copy(update={"contracts": contracts}), updated_actor),
        updated_proposer,
    )
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"fulfilled contract {contract_id}",
        rewards=(0.2, 0.2, 0.25, 0.0, 0.0, 0.0, -0.02, 0.0),
    )


def _handle_found_institution(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    age = next_tick - actor.born_at
    raw_min_age = action.params.get("min_age", world.adulthood_age)
    if isinstance(raw_min_age, bool) or not isinstance(raw_min_age, int) or raw_min_age < 0:
        return _reject(world, "min_age must be a non-negative integer")
    required_age = max(world.adulthood_age, raw_min_age)
    if age < required_age:
        return _reject(world, "actor too young to found institution")
    seed_currency = action.params.get("seed_currency", 5)
    if isinstance(seed_currency, bool) or not isinstance(seed_currency, int) or seed_currency < 0:
        return _reject(world, "seed_currency must be a non-negative integer")
    if actor.currency < seed_currency:
        return _reject(world, "insufficient currency to found institution")
    inst_id, inst_err = _resolve_identifier(
        action.params,
        "institution_id",
        default=f"inst-{world.step_index + 1}-{actor.agent_id}",
    )
    if inst_err is not None or inst_id is None:
        return _reject(world, inst_err or "invalid institution_id")
    if inst_id in world.institutions:
        return _reject(world, f"duplicate institution_id {inst_id}")
    name, name_err = _resolve_identifier(action.params, "name", default=f"Guild-{inst_id}")
    if name_err is not None or name is None:
        return _reject(world, name_err or "invalid institution name")
    raw_rate = action.params.get("contribution_rate", 0.1)
    if isinstance(raw_rate, bool) or not isinstance(raw_rate, (int, float)):
        return _reject(world, "contribution_rate must be a finite number in [0, 1]")
    rate = float(raw_rate)
    if not math.isfinite(rate) or not (0.0 <= rate <= 1.0):
        return _reject(world, "contribution_rate must be in [0, 1]")

    inst = InstitutionRecord(
        institution_id=inst_id,
        name=name,
        founder_id=actor.agent_id,
        location_id=actor.location_id,
        member_ids=(actor.agent_id,),
        treasury={},
        currency_reserve=seed_currency,
        contribution_rate=rate,
        created_tick=next_tick,
    )
    institutions = dict(world.institutions)
    institutions[inst_id] = inst
    updated = actor.model_copy(
        update={
            "currency": actor.currency - seed_currency,
            "institution_ids": (*actor.institution_ids, inst_id),
            "status": round(actor.status + 0.25, 6),
            "last_action_tick": next_tick,
        }
    )
    next_world = _replace_agent(world.model_copy(update={"institutions": institutions}), updated)
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"founded institution {inst_id}",
        rewards=(0.35, 0.1, 0.25, 0.0, 0.0, 0.0, -0.05, -0.05),
    )


def _handle_join_institution(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_inst_id = action.params.get("institution_id", "")
    if not isinstance(raw_inst_id, str) or not raw_inst_id.strip():
        return _reject(world, f"unknown institution {raw_inst_id!r}")
    inst_id = raw_inst_id.strip()
    inst = world.institutions.get(inst_id)
    if inst is None:
        return _reject(world, f"unknown institution {inst_id!r}")
    if actor.agent_id in inst.member_ids:
        return _reject(world, f"already member of {inst_id}")
    institutions = dict(world.institutions)
    institutions[inst_id] = inst.model_copy(update={"member_ids": (*inst.member_ids, actor.agent_id)})
    updated = actor.model_copy(
        update={
            "institution_ids": (*actor.institution_ids, inst_id),
            "status": round(actor.status + 0.05, 6),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"institutions": institutions}), updated),
        accepted=True,
        reason=f"joined institution {inst_id}",
        rewards=(0.1, 0.0, 0.35, 0.0, 0.0, 0.0, 0.0, 0.0),
    )


def _handle_contribute_institution(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_inst_id = action.params.get("institution_id", "")
    if not isinstance(raw_inst_id, str) or not raw_inst_id.strip():
        return _reject(world, f"actor is not a member of {raw_inst_id!r}")
    inst_id = raw_inst_id.strip()
    inst = world.institutions.get(inst_id)
    if inst is None or actor.agent_id not in inst.member_ids:
        return _reject(world, f"actor is not a member of {inst_id!r}")
    resource, res_err = _resolve_identifier(action.params, "resource", default="food")
    if res_err is not None or resource is None:
        return _reject(world, res_err or "invalid resource")
    amount = action.params.get("amount", 1)
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
        return _reject(world, "contribution amount must be a positive integer")
    if actor.inventory.get(resource, 0) < amount:
        return _reject(world, f"insufficient {resource} to contribute")

    inv = dict(actor.inventory)
    inv[resource] -= amount
    treasury = dict(inst.treasury)
    treasury[resource] = treasury.get(resource, 0) + amount
    institutions = dict(world.institutions)
    institutions[inst_id] = inst.model_copy(update={"treasury": treasury})
    updated = actor.model_copy(
        update={
            "inventory": inv,
            "status": round(actor.status + 0.1, 6),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"institutions": institutions}), updated),
        accepted=True,
        reason=f"contributed {amount} {resource} to {inst_id}",
        rewards=(0.2, -0.05, 0.25, 0.0, 0.0, 0.0, -0.02, 0.0),
    )


def _handle_propose_norm(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    norm_id, norm_err = _resolve_identifier(
        action.params,
        "norm_id",
        default=f"norm-{world.step_index + 1}-{actor.agent_id}",
    )
    if norm_err is not None or norm_id is None:
        return _reject(world, norm_err or "invalid norm_id")
    if norm_id in world.norms:
        return _reject(world, f"duplicate norm_id {norm_id}")
    title, title_err = _resolve_identifier(action.params, "title", default="Share Surplus")
    if title_err is not None or title is None:
        return _reject(world, title_err or "invalid norm title")
    rule_kind, rule_err = _resolve_identifier(action.params, "rule_kind", default="conservation")
    if rule_err is not None or rule_kind is None:
        return _reject(world, rule_err or "invalid rule_kind")
    norm = NormRecord(
        norm_id=norm_id,
        title=title,
        proposer_id=actor.agent_id,
        rule_kind=rule_kind,
        adopters=(actor.agent_id,),
        created_tick=next_tick,
    )
    norms = dict(world.norms)
    norms[norm_id] = norm
    updated = actor.model_copy(
        update={
            "adopted_norms": (*actor.adopted_norms, norm_id),
            "status": round(actor.status + 0.1, 6),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"norms": norms}), updated),
        accepted=True,
        reason=f"proposed norm {norm_id}",
        rewards=(0.25, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0),
    )


def _handle_adopt_norm(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_norm_id = action.params.get("norm_id", "")
    if not isinstance(raw_norm_id, str) or not raw_norm_id.strip():
        return _reject(world, f"unknown norm {raw_norm_id!r}")
    norm_id = raw_norm_id.strip()
    norm = world.norms.get(norm_id)
    if norm is None:
        return _reject(world, f"unknown norm {norm_id!r}")
    if actor.agent_id in norm.adopters:
        return _reject(world, f"already adopted norm {norm_id}")
    norms = dict(world.norms)
    norms[norm_id] = norm.model_copy(update={"adopters": (*norm.adopters, actor.agent_id)})
    updated = actor.model_copy(
        update={
            "adopted_norms": (*actor.adopted_norms, norm_id),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"norms": norms}), updated),
        accepted=True,
        reason=f"adopted norm {norm_id}",
        rewards=(0.1, 0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0),
    )


def _handle_assign_role(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    role, role_err = _resolve_identifier(action.params, "role")
    if role_err is not None or role is None or role == actor.role:
        return _reject(world, role_err or "role must be a non-empty new role name")
    updated = actor.model_copy(
        update={
            "role": role,
            "status": round(actor.status + 0.1, 6),
            "last_action_tick": next_tick,
        }
    )
    return _StepOutcome(
        world=_replace_agent(world, updated),
        accepted=True,
        reason=f"assigned role {role}",
        rewards=(0.25, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0),
    )


def _handle_spawn_offspring(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    living_count = sum(1 for a in world.agents.values() if a.alive)
    if living_count >= world.max_agents:
        return _reject(world, "population ceiling reached")
    if next_tick - actor.born_at < world.adulthood_age:
        return _reject(world, "parent must reach adulthood_age before reproduction")
    endow_currency = action.params.get("endow_currency", 5)
    if (
        isinstance(endow_currency, bool)
        or not isinstance(endow_currency, int)
        or endow_currency < 0
    ):
        return _reject(world, "endow_currency must be a non-negative integer")
    if actor.currency < endow_currency:
        return _reject(world, "insufficient currency for offspring endowment")
    child_id, child_err = _resolve_identifier(
        action.params,
        "child_id",
        default=f"agent-{len(world.agents)}",
    )
    if child_err is not None or child_id is None:
        return _reject(world, child_err or "invalid child_id")
    if child_id in world.agents:
        return _reject(world, f"duplicate child_id {child_id}")

    parents: list[str] = [actor.agent_id]
    max_parent_gen = actor.generation
    co_parent_id = action.params.get("co_parent_id")
    if co_parent_id is not None:
        if not isinstance(co_parent_id, str) or not co_parent_id.strip():
            return _reject(world, f"invalid co_parent_id {co_parent_id!r}")
        cp = world.agents.get(co_parent_id.strip())
        if cp is None or not cp.alive or cp.agent_id == actor.agent_id:
            return _reject(world, f"invalid co_parent_id {co_parent_id}")
        if next_tick - cp.born_at < world.adulthood_age:
            return _reject(world, "co-parent must reach adulthood_age")
        parents.append(cp.agent_id)
        max_parent_gen = max(max_parent_gen, cp.generation)

    child = WorldAgentState(
        agent_id=child_id,
        location_id=actor.location_id,
        born_at=next_tick,
        alive=True,
        energy=0.8,
        fatigue=0.0,
        currency=endow_currency,
        inventory={},
        role="generalist",
        lineage_id=actor.lineage_id,
        parents=tuple(parents),
        generation=max_parent_gen + 1,
        status=0.0,
        skills=(),
        institution_ids=(),
        adopted_norms=(),
        last_action_tick=next_tick,
    )
    updated_actor = actor.model_copy(
        update={
            "currency": actor.currency - endow_currency,
            "status": round(actor.status + 0.15, 6),
            "last_action_tick": next_tick,
        }
    )
    agents = dict(world.agents)
    agents[actor.agent_id] = updated_actor
    agents[child_id] = child
    return _StepOutcome(
        world=world.model_copy(update={"agents": agents}),
        accepted=True,
        reason=f"spawned offspring {child_id}",
        rewards=(0.2, -0.05, 0.35, 0.0, 0.0, 0.0, -0.05, -0.05),
    )


def _handle_improve_location(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    if actor.fatigue >= 0.95:
        return _reject(world, "actor too fatigued to improve location")
    loc = world.locations[actor.location_id]
    raw_target = action.params.get("target_resource", action.params.get("resource", "food"))
    if not isinstance(raw_target, str) or not raw_target.strip():
        return _reject(world, "target_resource must be a non-empty string")
    target_resource = raw_target.strip()
    if target_resource not in loc.capacities:
        return _reject(world, f"unknown target_resource {target_resource!r} at {loc.location_id}")
    current_cap = loc.capacities[target_resource]
    if current_cap >= _MAX_LOCATION_CAPACITY:
        return _reject(
            world,
            f"{loc.location_id} {target_resource} capacity already at max ({_MAX_LOCATION_CAPACITY})",
        )
    inv = dict(actor.inventory)
    for res, req in _LOCATION_IMPROVE_COST.items():
        if inv.get(res, 0) < req:
            return _reject(world, f"insufficient {res} to improve {loc.location_id}")
    consumed = dict(world.accounting.consumed_or_decayed)
    for res, req in _LOCATION_IMPROVE_COST.items():
        inv[res] = inv[res] - req
        consumed[res] = consumed.get(res, 0) + req

    new_cap = min(current_cap + _LOCATION_CAPACITY_INCREMENT, _MAX_LOCATION_CAPACITY)
    capacities = dict(loc.capacities)
    capacities[target_resource] = new_cap
    locations = dict(world.locations)
    locations[loc.location_id] = loc.model_copy(update={"capacities": capacities})
    accounting = world.accounting.model_copy(update={"consumed_or_decayed": consumed})
    updated = actor.model_copy(
        update={
            "inventory": inv,
            "status": round(actor.status + 0.15, 6),
            "fatigue": round(_clamp(actor.fatigue + 0.08, 0.0, 1.0), 6),
            "energy": round(_clamp(actor.energy - 0.03, 0.0, 1.0), 6),
            "last_action_tick": next_tick,
        }
    )
    next_world = _replace_agent(
        world.model_copy(update={"locations": locations, "accounting": accounting}),
        updated,
    )
    return _StepOutcome(
        world=next_world,
        accepted=True,
        reason=f"improved {loc.location_id} {target_resource} capacity {current_cap} -> {new_cap}",
        rewards=(0.25, 0.1, 0.1, 0.0, 0.0, 0.0, -0.08, -0.05),
    )


def _handle_register_capability(
    world: WorldState, actor: WorldAgentState, action: Action, next_tick: int
) -> _StepOutcome:
    raw_pkg = action.params.get("package")
    if not isinstance(raw_pkg, dict):
        return _reject(world, "package parameter must be a mapping")
    try:
        pkg = CapabilityPackage.model_validate(raw_pkg)
    except Exception as exc:
        return _reject(world, f"invalid capability package: {exc}")
    if not pkg.package_id.strip():
        return _reject(world, "package_id must be a non-empty string")
    if pkg.action_type != ActionType.CRAFT:
        return _reject(world, f"unsupported capability action_type {pkg.action_type!r}")
    raw_param_evidence = action.params.get("evidence_id")
    if raw_param_evidence is not None and not isinstance(raw_param_evidence, str):
        return _reject(world, "evidence_id must be a string")
    param_evidence = raw_param_evidence.strip() if isinstance(raw_param_evidence, str) else ""
    pkg_evidence = pkg.evidence_id.strip()
    if pkg_evidence and param_evidence and pkg_evidence != param_evidence:
        return _reject(world, "mismatched evidence_id between package and action params")
    evidence_id = pkg_evidence or param_evidence
    if not evidence_id:
        return _reject(world, "capability registration requires non-empty evidence_id")
    if pkg.evidence_id != evidence_id:
        pkg = pkg.model_copy(update={"evidence_id": evidence_id})
    if not (pkg.verified_replay and pkg.verified_intervention and pkg.verified_containment):
        return _reject(world, "capability package failed verification/containment gate")
    if pkg.package_id in world.capabilities:
        return _reject(world, f"capability {pkg.package_id} already exists")
    caps = dict(world.capabilities)
    caps[pkg.package_id] = pkg
    updated = actor.model_copy(
        update={"status": round(actor.status + 0.15, 6), "last_action_tick": next_tick}
    )
    return _StepOutcome(
        world=_replace_agent(world.model_copy(update={"capabilities": caps}), updated),
        accepted=True,
        reason=f"registered verified capability {pkg.package_id}",
        rewards=(0.3, 0.1, 0.0, 0.0, 0.0, 0.0, -0.05, 0.0),
    )


_ACTION_HANDLERS: dict[ActionType, _HandlerFn] = {
    ActionType.WAIT: _handle_wait,
    ActionType.GATHER: _handle_gather,
    ActionType.MOVE: _handle_move,
    ActionType.CONSUME: _handle_consume,
    ActionType.CRAFT: _handle_craft,
    ActionType.TRADE: _handle_trade,
    ActionType.PROPOSE_CONTRACT: _handle_propose_contract,
    ActionType.FULFILL_CONTRACT: _handle_fulfill_contract,
    ActionType.FOUND_INSTITUTION: _handle_found_institution,
    ActionType.JOIN_INSTITUTION: _handle_join_institution,
    ActionType.CONTRIBUTE_INSTITUTION: _handle_contribute_institution,
    ActionType.PROPOSE_NORM: _handle_propose_norm,
    ActionType.ADOPT_NORM: _handle_adopt_norm,
    ActionType.ASSIGN_ROLE: _handle_assign_role,
    ActionType.SPAWN_OFFSPRING: _handle_spawn_offspring,
    ActionType.IMPROVE_LOCATION: _handle_improve_location,
    ActionType.REGISTER_CAPABILITY: _handle_register_capability,
}


def _apply_exogenous(
    world: WorldState,
    exogenous_input: ExogenousInput,
) -> tuple[WorldState, tuple[str, ...]]:
    """Apply explicit deterministic exogenous events to `world`."""
    if not exogenous_input.events:
        return world, ()
    locations = dict(world.locations)
    inflows = dict(world.accounting.exogenous_inflows)
    consumed = dict(world.accounting.consumed_or_decayed)
    applied: list[str] = []

    for event in exogenous_input.events:
        kind = str(event.get("type", ""))
        if kind == "regen":
            for loc_id in sorted(locations):
                loc = locations[loc_id]
                new_res = dict(loc.resources)
                for res, rate in sorted(loc.regen_rates.items()):
                    cap = loc.capacities.get(res, new_res.get(res, 0))
                    effective_rate = int(round(rate * loc.shock_factor))
                    added = max(0, min(effective_rate, cap - new_res.get(res, 0)))
                    if added > 0:
                        new_res[res] = new_res.get(res, 0) + added
                        inflows[res] = inflows.get(res, 0) + added
                next_factor = round(_clamp(loc.shock_factor + 0.25, 0.0, 1.0), 6)
                locations[loc_id] = loc.model_copy(
                    update={"resources": new_res, "shock_factor": next_factor}
                )
            applied.append("regen")
        elif kind == "shock":
            targets = event.get("location_ids", sorted(locations))
            deplete_fraction = _clamp(float(event.get("deplete_fraction", 0.5)), 0.0, 1.0)
            shock_factor = _clamp(float(event.get("shock_factor", 0.25)), 0.0, 1.0)
            for loc_id in targets:
                if loc_id not in locations:
                    continue
                loc = locations[loc_id]
                new_res = dict(loc.resources)
                for res, qty in sorted(new_res.items()):
                    removed = int(qty * deplete_fraction)
                    if removed > 0:
                        new_res[res] = qty - removed
                        consumed[res] = consumed.get(res, 0) + removed
                locations[loc_id] = loc.model_copy(
                    update={"resources": new_res, "shock_factor": shock_factor}
                )
            applied.append("shock")

    accounting = ResourceAccounting(
        initial_resources=world.accounting.initial_resources,
        exogenous_inflows=inflows,
        consumed_or_decayed=consumed,
        initial_currency=world.accounting.initial_currency,
    )
    return (
        world.model_copy(update={"locations": locations, "accounting": accounting}),
        tuple(applied),
    )


def _resolve_next_tick(world: WorldState, exogenous_input: ExogenousInput) -> int:
    delta = 0 if exogenous_input.metadata.get("same_tick") is True else 1
    for event in exogenous_input.events:
        if event.get("type") == "advance_tick":
            raw_delta = event.get("delta", 1)
            if not isinstance(raw_delta, bool) and isinstance(raw_delta, int) and raw_delta >= 0:
                delta = max(delta, raw_delta)
    return max(world.tick + delta, exogenous_input.tick)


def _expire_agents(world: WorldState, next_tick: int) -> WorldState:
    agents: dict[str, WorldAgentState] = {}
    for agent_id, agent in world.agents.items():
        if agent.alive and next_tick - agent.born_at >= world.lifespan:
            agents[agent_id] = agent.model_copy(update={"alive": False})
        else:
            agents[agent_id] = agent
    return world.model_copy(update={"agents": agents})


class SocialSandboxEngine:
    """Stateless deterministic Phase 1.1 social-sandbox transition engine.

    Stores only initial configuration (`default_seed`, `max_ticks`, `max_agents`,
    `num_locations`, `num_agents`). No mutable world state resides on `self`.
    """

    def __init__(
        self,
        *,
        default_seed: int = 42,
        max_ticks: int = 2000,
        max_agents: int = 64,
        num_locations: int = 4,
        num_agents: int = 4,
    ) -> None:
        self._default_seed = default_seed
        self._max_ticks = max_ticks
        self._max_agents = max_agents
        self._num_locations = num_locations
        self._num_agents = num_agents

    def reset(
        self,
        seed: int | None = None,
        *,
        run_id: str = "default-run",
        branch_id: str = "main",
        initial_agent_age: int = 0,
    ) -> State:
        """Return a deterministic initial `State`."""
        world = build_default_world(
            seed=self._default_seed if seed is None else seed,
            run_id=run_id,
            branch_id=branch_id,
            num_locations=self._num_locations,
            num_agents=self._num_agents,
            max_ticks=self._max_ticks,
            max_agents=self._max_agents,
            initial_agent_age=initial_agent_age,
        )
        report = check_invariants(None, world)
        if not report.passed:
            raise RuntimeError(f"Initial world failed invariants: {report}")
        return world.to_state()

    def is_terminal(self, state: State) -> bool:
        """Return True when `max_ticks` is reached or no living agents remain."""
        world = WorldState.from_state(state)
        return world.tick >= world.max_ticks or not any(a.alive for a in world.agents.values())

    def snapshot(
        self,
        state: State,
        *,
        snapshot_id: str | None = None,
        parent_snapshot_id: str | None = None,
    ) -> WorldSnapshot:
        """Build an immutable `WorldSnapshot` from `state`."""
        world = WorldState.from_state(state)
        digest = world.state_hash()
        resolved_id = snapshot_id or f"snap-{world.run_id}-{world.branch_id}-{world.tick}-{digest[:12]}"
        return WorldSnapshot(
            snapshot_id=resolved_id,
            world_version=world.world_version,
            run_id=world.run_id,
            branch_id=world.branch_id,
            tick=world.tick,
            parent_snapshot_id=parent_snapshot_id,
            state_hash=digest,
            state=world,
        )

    def restore(self, snapshot: WorldSnapshot) -> State:
        """Verify integrity of `snapshot` and return its canonical `State`."""
        if snapshot.state.state_hash() != snapshot.state_hash:
            raise ValueError(f"Snapshot {snapshot.snapshot_id} hash mismatch")
        return snapshot.state.to_state()

    def step(
        self,
        state: State,
        action: Action,
        exogenous_input: ExogenousInput | None = None,
        seed: int | None = None,
    ) -> Transition:
        """Execute `(state, action, exogenous_input, seed) -> (emission, next_state)`."""
        world = WorldState.from_state(state)
        resolved_exog = exogenous_input if exogenous_input is not None else ExogenousInput(tick=world.tick)
        resolved_seed = world.seed if seed is None else seed

        if world.tick >= world.max_ticks:
            outcome = _reject(world, f"world has reached max_ticks ({world.max_ticks})")
            applied_exog: tuple[str, ...] = ()
            final_world = outcome.world.model_copy(
                update={
                    "step_index": world.step_index + 1,
                    "seed": resolved_seed,
                }
            )
        else:
            next_tick = _resolve_next_tick(world, resolved_exog)
            actor = world.agents.get(action.agent_id)
            if actor is None:
                outcome = _reject(world, f"unknown agent {action.agent_id}")
            elif not actor.alive:
                outcome = _reject(world, f"agent {action.agent_id} is dead")
            else:
                try:
                    action_type = ActionType(action.action_type)
                except ValueError:
                    outcome = _reject(world, f"unsupported action_type {action.action_type!r}")
                else:
                    handler = _ACTION_HANDLERS[action_type]
                    outcome = handler(world, actor, action, next_tick)

            post_exog_world, applied_exog = _apply_exogenous(outcome.world, resolved_exog)
            final_world = _expire_agents(
                post_exog_world.model_copy(
                    update={
                        "tick": next_tick,
                        "step_index": world.step_index + 1,
                        "seed": resolved_seed,
                    }
                ),
                next_tick,
            )

        report = check_invariants(world, final_world)
        if not report.passed:
            raise RuntimeError(f"World invariant violation: {report}")

        next_state = final_world.to_state()
        tid = uuid5(
            NAMESPACE_URL,
            f"evolzen:transition:{state.state_id}:{canonical_json(action.model_dump(mode='json'))}:"
            f"{canonical_json(resolved_exog.model_dump(mode='json'))}:{resolved_seed}",
        )
        growth_events = extract_growth_events(world, final_world, action, resolved_exog, str(tid))
        rewards = _clamp_rewards(outcome.rewards)
        emission_data: dict[str, Any] = {
            "accepted": outcome.accepted,
            "reason": outcome.reason,
            "tick": final_world.tick,
            "step_index": final_world.step_index,
            "actor_id": action.agent_id,
            "action_type": action.action_type,
            "rewards": list(rewards),
            "growth_events": [e.model_dump(mode="json") for e in growth_events],
            "invariant_passed": report.passed,
            "exogenous_applied": list(applied_exog),
            "evidence_id": str(tid),
        }
        ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=final_world.step_index)
        return Transition(
            transition_id=tid,
            timestamp=ts,
            state=state,
            action=action,
            exogenous_input=resolved_exog,
            seed=resolved_seed,
            emission=Emission(data=emission_data),
            next_state=next_state,
        )
