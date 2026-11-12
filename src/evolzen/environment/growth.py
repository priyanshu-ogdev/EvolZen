"""Phase 1.1 growth ledger extraction and attribution (docs/PRD.md G1a, ADR 0004).

Compares consecutive `WorldState` transitions to emit durable, causally attributable
`GrowthEvent` records across the five Phase 1.1 growth categories, supporting
ontology-aligned world tracking (OPINE-World, arXiv:2607.01531; Executable World
Models, arXiv:2605.05138). The growth taxonomy and attribution rules are an EvolZen
design choice and remain empirically untested until Phase 1.1 experiments are run.
"""
from __future__ import annotations

from collections.abc import Iterable

from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import (
    ActionType,
    GrowthAttribution,
    GrowthCategory,
    GrowthEvent,
    WorldState,
)


def extract_growth_events(
    prev_world: WorldState,
    next_world: WorldState,
    action: Action,
    exogenous_input: ExogenousInput,
    transition_id: str,
) -> tuple[GrowthEvent, ...]:
    """Compare `prev_world` and `next_world` to emit attributable `GrowthEvent` records."""
    events: list[GrowthEvent] = []
    idx = 0

    def add_event(
        category: GrowthCategory,
        attribution: GrowthAttribution,
        actor_id: str,
        entity_id: str,
        summary: str,
    ) -> None:
        nonlocal idx
        idx += 1
        events.append(
            GrowthEvent(
                event_id=f"{transition_id}:g{idx}",
                tick=next_world.tick,
                category=category,
                attribution=attribution,
                actor_id=actor_id,
                entity_id=entity_id,
                summary=summary,
                transition_id=transition_id,
            )
        )

    for artifact_id in sorted(set(next_world.artifacts) - set(prev_world.artifacts)):
        art = next_world.artifacts[artifact_id]
        add_event(
            GrowthCategory.ARTIFACT_CAPABILITY,
            GrowthAttribution.AGENT_ACTION,
            art.creator_id,
            artifact_id,
            f"Crafted durable artifact {art.kind}",
        )

    for pkg_id in sorted(set(next_world.capabilities) - set(prev_world.capabilities)):
        add_event(
            GrowthCategory.ARTIFACT_CAPABILITY,
            GrowthAttribution.AGENT_ACTION,
            action.agent_id,
            pkg_id,
            f"Registered verified capability {pkg_id}",
        )

    for contract_id in sorted(set(next_world.contracts) - set(prev_world.contracts)):
        c = next_world.contracts[contract_id]
        add_event(
            GrowthCategory.CONTRACT_MARKET_INSTITUTION,
            GrowthAttribution.AGENT_ACTION,
            c.proposer_id,
            contract_id,
            f"Created bilateral contract {contract_id}",
        )

    for contract_id, next_c in sorted(next_world.contracts.items()):
        prev_c = prev_world.contracts.get(contract_id)
        if prev_c is not None and prev_c.status == "open" and next_c.status == "fulfilled":
            add_event(
                GrowthCategory.CONTRACT_MARKET_INSTITUTION,
                GrowthAttribution.AGENT_ACTION,
                action.agent_id,
                contract_id,
                f"Fulfilled contract {contract_id}",
            )

    for inst_id in sorted(set(next_world.institutions) - set(prev_world.institutions)):
        inst = next_world.institutions[inst_id]
        add_event(
            GrowthCategory.CONTRACT_MARKET_INSTITUTION,
            GrowthAttribution.AGENT_ACTION,
            inst.founder_id,
            inst_id,
            f"Founded institution {inst.name}",
        )

    for norm_id in sorted(set(next_world.norms) - set(prev_world.norms)):
        norm = next_world.norms[norm_id]
        add_event(
            GrowthCategory.NORM_BELIEF_MANUAL,
            GrowthAttribution.AGENT_ACTION,
            norm.proposer_id,
            norm_id,
            f"Proposed norm {norm.title}",
        )

    for norm_id, next_norm in sorted(next_world.norms.items()):
        prev_norm = prev_world.norms.get(norm_id)
        if prev_norm is not None and len(next_norm.adopters) > len(prev_norm.adopters):
            new_adopters = sorted(set(next_norm.adopters) - set(prev_norm.adopters))
            for adopter in new_adopters:
                add_event(
                    GrowthCategory.NORM_BELIEF_MANUAL,
                    GrowthAttribution.AGENT_ACTION,
                    adopter,
                    f"{norm_id}:{adopter}",
                    f"Agent {adopter} adopted norm {next_norm.title}",
                )

    for agent_id in sorted(set(next_world.agents) - set(prev_world.agents)):
        agent = next_world.agents[agent_id]
        add_event(
            GrowthCategory.AGENT_ROLE_LINEAGE,
            GrowthAttribution.AGENT_ACTION,
            action.agent_id,
            agent_id,
            f"Born descendant {agent_id} (generation {agent.generation})",
        )

    for agent_id, next_agent in sorted(next_world.agents.items()):
        prev_agent = prev_world.agents.get(agent_id)
        if prev_agent is not None and prev_agent.role != next_agent.role:
            add_event(
                GrowthCategory.AGENT_ROLE_LINEAGE,
                GrowthAttribution.AGENT_ACTION,
                agent_id,
                f"{agent_id}:role:{next_agent.role}",
                f"Agent {agent_id} specialized role {prev_agent.role} -> {next_agent.role}",
            )

    for loc_id, next_loc in sorted(next_world.locations.items()):
        prev_loc = prev_world.locations.get(loc_id)
        if prev_loc is None:
            continue
        for res, next_cap in sorted(next_loc.capacities.items()):
            prev_cap = prev_loc.capacities.get(res, 0)
            if next_cap > prev_cap:
                actor_before = prev_world.agents.get(action.agent_id)
                if (
                    action.action_type == ActionType.IMPROVE_LOCATION
                    and actor_before is not None
                    and actor_before.location_id == loc_id
                ):
                    attribution = GrowthAttribution.AGENT_ACTION
                    actor_id = action.agent_id
                elif exogenous_input.events:
                    attribution = GrowthAttribution.EXOGENOUS_INPUT
                    actor_id = "world"
                else:
                    attribution = GrowthAttribution.ENDOGENOUS_PROCESS
                    actor_id = "world"
                add_event(
                    GrowthCategory.LOCATION_RESOURCE,
                    attribution,
                    actor_id,
                    f"{loc_id}:{res}",
                    f"Expanded {loc_id} {res} capacity {prev_cap} -> {next_cap}",
                )

    return tuple(events)


def summarize_growth(events: Iterable[GrowthEvent]) -> dict[GrowthCategory, int]:
    """Count growth events per `GrowthCategory`."""
    counts: dict[GrowthCategory, int] = {cat: 0 for cat in GrowthCategory}
    for event in events:
        counts[event.category] = counts.get(event.category, 0) + 1
    return counts

