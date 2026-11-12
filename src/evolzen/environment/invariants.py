"""Phase 1.1 world invariant checks for the persistent social sandbox.

Verifies exact resource/currency conservation, capacity and scalar boundedness, valid
ownership/membership integrity, and monotonic clock progression per docs/phases/1.1-environment.md,
ADR 0004, and Tycho (arXiv:2607.28287). These invariant definitions are an EvolZen design
choice and remain empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

import math

from evolzen.schemas.world import InvariantReport, WorldInvariant, WorldState


def total_world_resources(world: WorldState) -> dict[str, int]:
    """Sum all non-consumed resource quantities across locations, agents, institutions, and artifacts."""
    totals: dict[str, int] = {}
    for loc in world.locations.values():
        for res, qty in loc.resources.items():
            totals[res] = totals.get(res, 0) + qty
    for agent in world.agents.values():
        for res, qty in agent.inventory.items():
            totals[res] = totals.get(res, 0) + qty
    for inst in world.institutions.values():
        for res, qty in inst.treasury.items():
            totals[res] = totals.get(res, 0) + qty
    for artifact in world.artifacts.values():
        for res, qty in artifact.recipe_resources.items():
            totals[res] = totals.get(res, 0) + qty
    return totals


def _check_resource_conservation(world: WorldState) -> WorldInvariant:
    totals = total_world_resources(world)

    all_keys = (
        set(totals)
        | set(world.accounting.initial_resources)
        | set(world.accounting.exogenous_inflows)
        | set(world.accounting.consumed_or_decayed)
    )
    mismatches: list[str] = []
    for key in sorted(all_keys):
        observed = totals.get(key, 0)
        expected = (
            world.accounting.initial_resources.get(key, 0)
            + world.accounting.exogenous_inflows.get(key, 0)
            - world.accounting.consumed_or_decayed.get(key, 0)
        )
        if observed != expected:
            mismatches.append(f"{key}: observed={observed} expected={expected}")

    observed_currency = sum(a.currency for a in world.agents.values()) + sum(
        i.currency_reserve for i in world.institutions.values()
    )
    if observed_currency != world.accounting.initial_currency:
        mismatches.append(
            f"currency: observed={observed_currency} expected={world.accounting.initial_currency}"
        )

    return WorldInvariant(
        name="resource_conservation",
        description="Resources and currency reconcile exactly with initial stock, inflows, and sinks.",
        passed=not mismatches,
        details="; ".join(mismatches),
    )


def _check_bounded_state(world: WorldState) -> WorldInvariant:
    issues: list[str] = []
    if len(world.agents) > world.max_agents:
        issues.append(f"agents={len(world.agents)} > max_agents={world.max_agents}")
    for loc_id, loc in world.locations.items():
        for res, qty in loc.resources.items():
            cap = loc.capacities.get(res)
            if qty < 0:
                issues.append(f"{loc_id}.{res} negative ({qty})")
            if cap is not None and qty > cap:
                issues.append(f"{loc_id}.{res}={qty} exceeds capacity={cap}")
    for agent_id, agent in world.agents.items():
        for field_name, val in (
            ("energy", agent.energy),
            ("fatigue", agent.fatigue),
            ("status", agent.status),
        ):
            if not math.isfinite(val):
                issues.append(f"{agent_id}.{field_name} non-finite")
        if not (0.0 <= agent.energy <= 1.0):
            issues.append(f"{agent_id}.energy={agent.energy} out of [0, 1]")
        if not (0.0 <= agent.fatigue <= 1.0):
            issues.append(f"{agent_id}.fatigue={agent.fatigue} out of [0, 1]")
    return WorldInvariant(
        name="bounded_state",
        description="Resource stocks remain within location capacities and scalar states remain finite/bounded.",
        passed=not issues,
        details="; ".join(issues),
    )


def _check_valid_ownership(world: WorldState) -> WorldInvariant:
    issues: list[str] = []
    valid_owners = set(world.agents) | set(world.institutions)
    for agent_id, agent in world.agents.items():
        if agent.location_id not in world.locations:
            issues.append(f"{agent_id} at unknown location {agent.location_id}")
        for inst_id in agent.institution_ids:
            inst = world.institutions.get(inst_id)
            if inst is None or agent_id not in inst.member_ids:
                issues.append(f"{agent_id} mismatched membership in {inst_id}")
    for inst_id, inst in world.institutions.items():
        if inst.location_id not in world.locations:
            issues.append(f"institution {inst_id} at unknown location {inst.location_id}")
        for member_id in inst.member_ids:
            member = world.agents.get(member_id)
            if member is None or inst_id not in member.institution_ids:
                issues.append(f"institution {inst_id} lists invalid/unsynced member {member_id}")
    for artifact_id, artifact in world.artifacts.items():
        if artifact.location_id not in world.locations:
            issues.append(f"artifact {artifact_id} at unknown location {artifact.location_id}")
        if artifact.owner_id not in valid_owners:
            issues.append(f"artifact {artifact_id} owned by unknown {artifact.owner_id}")
    for contract_id, contract in world.contracts.items():
        if contract.proposer_id not in world.agents or contract.counterparty_id not in world.agents:
            issues.append(f"contract {contract_id} references unknown agent")
    return WorldInvariant(
        name="valid_ownership",
        description="All agents, artifacts, contracts, and institutions reference valid entities.",
        passed=not issues,
        details="; ".join(issues),
    )


def _check_monotonic_clock(prev_world: WorldState | None, next_world: WorldState) -> WorldInvariant:
    issues: list[str] = []
    for agent_id, agent in next_world.agents.items():
        if agent.born_at > next_world.tick:
            issues.append(f"{agent_id} born_at={agent.born_at} > tick={next_world.tick}")
    if prev_world is not None:
        if next_world.tick < prev_world.tick:
            issues.append(f"tick regressed: {prev_world.tick} -> {next_world.tick}")
        if next_world.step_index < prev_world.step_index:
            issues.append(f"step_index regressed: {prev_world.step_index} -> {next_world.step_index}")
        for agent_id, prev_agent in prev_world.agents.items():
            next_agent = next_world.agents.get(agent_id)
            if next_agent is None:
                issues.append(f"agent {agent_id} vanished from world record")
            elif not prev_agent.alive and next_agent.alive:
                issues.append(f"dead agent {agent_id} resurrected")
    return WorldInvariant(
        name="monotonic_clock",
        description="World clock and step counter never regress and dead agents are never resurrected.",
        passed=not issues,
        details="; ".join(issues),
    )


def check_invariants(prev_world: WorldState | None, next_world: WorldState) -> InvariantReport:
    """Evaluate all Phase 1.1 world invariants on `next_world`."""
    checks = (
        _check_resource_conservation(next_world),
        _check_bounded_state(next_world),
        _check_valid_ownership(next_world),
        _check_monotonic_clock(prev_world, next_world),
    )
    return InvariantReport(
        tick=next_world.tick,
        passed=all(check.passed for check in checks),
        checks=checks,
    )
