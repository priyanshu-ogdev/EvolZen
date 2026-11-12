"""Phase 1.1 — Minimal controlled-intervention interface.

Supports counterfactual single-variable (`set_variable`) and action-withholding
(`withhold_action`) interventions over the normative transition contract.

Design authority: docs/phases/1.1-environment.md, ADR 0005
(docs/adr/0005-transition-semantics-and-dual-track-evaluation.md).
Citations: Tycho (arXiv:2607.28287) for active intervention probes over interactive
rendered environments. Downstream causal-identification efficacy remains empirically
untested until Phase 1.1 and Phase 2.1 experiments are run.
"""
from __future__ import annotations

import copy
from typing import Any

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants, total_world_resources
from evolzen.schemas.transition import Action, ExogenousInput, State, Transition
from evolzen.schemas.world import ActionType, InterventionSpec, ResourceAccounting, WorldState


def _reconcile_accounting(base: WorldState, modified: WorldState) -> WorldState:
    before = total_world_resources(base)
    after = total_world_resources(modified)
    inflows = dict(modified.accounting.exogenous_inflows)
    consumed = dict(modified.accounting.consumed_or_decayed)
    for res in set(before) | set(after):
        delta = after.get(res, 0) - before.get(res, 0)
        if delta > 0:
            inflows[res] = inflows.get(res, 0) + delta
        elif delta < 0:
            consumed[res] = consumed.get(res, 0) + (-delta)
    accounting = ResourceAccounting(
        initial_resources=modified.accounting.initial_resources,
        exogenous_inflows=inflows,
        consumed_or_decayed=consumed,
        initial_currency=modified.accounting.initial_currency,
    )
    return modified.model_copy(update={"accounting": accounting})


def _set_nested_path(payload: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Return a deep copy of `payload` with dotted `path` updated to `value`."""
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ValueError("target_path must not be empty for set_variable intervention")
    copied = copy.deepcopy(payload)
    cursor: Any = copied
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise KeyError(f"Invalid intervention path segment {part!r} in {path!r}")
        cursor = cursor[part]
    if not isinstance(cursor, dict) or parts[-1] not in cursor:
        raise KeyError(f"Invalid final intervention key {parts[-1]!r} in {path!r}")
    cursor[parts[-1]] = value
    return copied


def apply_intervention(
    engine: SocialSandboxEngine,
    state: State,
    action: Action,
    intervention: InterventionSpec,
    *,
    exogenous_input: ExogenousInput | None = None,
    seed: int | None = None,
) -> tuple[Transition, Transition]:
    """Run baseline `(state, action)` and a counterfactual branch under `intervention`.

    Supports:
    - `set_variable`: modifies one declared variable in a branched copy of `WorldState`
      (updating accounting if a location resource stock is intervened on, and verifying
      invariants before stepping).
    - `withhold_action`: replaces `action` with a canonical `wait` action when matching
      `withheld_agent_id` (or unconditionally if `withheld_agent_id` is None).
    """
    baseline = engine.step(state, action, exogenous_input=exogenous_input, seed=seed)

    if intervention.kind == "withhold_action":
        if intervention.withheld_agent_id is None or action.agent_id == intervention.withheld_agent_id:
            counterfactual_action = Action(agent_id=action.agent_id, action_type=ActionType.WAIT)
        else:
            counterfactual_action = action
        counterfactual = engine.step(
            state,
            counterfactual_action,
            exogenous_input=exogenous_input,
            seed=seed,
        )
        return baseline, counterfactual

    base_world = WorldState.from_state(state)
    modified_dict = _set_nested_path(
        base_world.canonical_dict(), intervention.target_path, intervention.value
    )
    modified_world = _reconcile_accounting(base_world, WorldState.model_validate(modified_dict))
    report = check_invariants(None, modified_world)
    if not report.passed:
        raise ValueError(f"Intervened state violates world invariants: {report}")
    counterfactual = engine.step(
        modified_world.to_state(),
        action,
        exogenous_input=exogenous_input,
        seed=seed,
    )
    return baseline, counterfactual
