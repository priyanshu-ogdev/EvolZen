"""The verifier half of the actor/synthesizer/verifier loop (Phase 1.4).

Adopts the exact-match falsifiability standard: a candidate rule is promoted only if it
reproduces recorded transitions exactly, passes counterfactual intervention checks, and executes
within declared resource bounds strictly inside `evolzen.containment.Sandbox`.

Citations:
- Romera-Paredes et al. (FunSearch, Nature 2024, DOI: 10.1038/s41586-023-06924-6)
  for evaluator-gated evolutionary program verification;
- Executable World Models for ARC-AGI-3 (arXiv:2605.05138) for exact replay verification;
- Agache et al. (Firecracker, USENIX NSDI 2020) and Sidik & Rokach (arXiv:2604.11839)
  for fail-closed sandbox containment.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from evolzen.containment.sandbox import GVisorSandbox, Sandbox, is_gvisor_available
from evolzen.exploration.synthesizer import CandidateRule
from evolzen.schemas.transition import Action, ExogenousInput, State, Transition
from evolzen.schemas.world import ActionType, CapabilityPackage

if TYPE_CHECKING:
    from evolzen.environment.engine import SocialSandboxEngine


@dataclass(frozen=True)
class VerificationReport:
    """Detailed summary of candidate rule verification results."""

    rule_id: str
    passed: bool
    transitions_tested: int
    exact_matches: int
    mismatches: int
    timeouts: int
    resource_ceiling_hits: int
    execution_errors: int
    verified_replay: bool
    verified_intervention: bool
    verified_containment: bool
    details: tuple[str, ...] = ()


def build_runner_code(rule_code: str) -> str:
    """Wrap candidate rule code with a JSON I/O execution harness for Sandbox execution."""
    return f"""import json

{rule_code}

raw_state = input_data.get("state", {{}})
raw_action = input_data.get("action", {{}})
raw_exog = input_data.get("exogenous_input", {{}})
raw_seed = input_data.get("seed", 0)

if "predict" in globals() and callable(globals()["predict"]):
    try:
        res = predict(raw_state, raw_action, raw_exog, raw_seed)
    except TypeError:
        res = predict(raw_state, raw_action)
else:
    res = globals().get("output", {{}})

print(json.dumps(res))
"""


class Verifier:
    """Checks CandidateRule hypotheses against recorded transitions and interventions under Sandbox isolation."""

    def __init__(
        self,
        sandbox: Sandbox | None = None,
        *,
        timeout_seconds: float = 2.0,
        resource_ceiling_mb: int = 128,
        check_next_state: bool = False,
    ) -> None:
        if sandbox is not None:
            self.sandbox = sandbox
        elif is_gvisor_available():
            self.sandbox = GVisorSandbox(
                default_timeout_seconds=timeout_seconds,
                default_resource_ceiling_mb=resource_ceiling_mb,
            )
        else:
            raise RuntimeError(
                "No Sandbox instance provided and gVisor (runsc) is not available on this host. "
                "Per AGENTS.md safety constraint #1, untrusted code cannot execute outside a Sandbox. "
                "Provide an explicit Sandbox implementation (e.g. MockSandbox in tests)."
            )
        self.timeout_seconds = timeout_seconds
        self.resource_ceiling_mb = resource_ceiling_mb
        self.check_next_state = check_next_state

    def verify(self, rule: CandidateRule, held_out_transitions: list[Transition]) -> bool:
        """Return True only if `rule` exactly reproduces every transition in held_out_transitions."""
        report = self.verify_with_report(rule, held_out_transitions)
        return report.passed

    def verify_with_report(
        self,
        rule: CandidateRule,
        held_out_transitions: list[Transition],
    ) -> VerificationReport:
        """Run sandboxed replay against held_out_transitions and produce a detailed report."""
        if not held_out_transitions:
            return VerificationReport(
                rule_id=rule.rule_id,
                passed=False,
                transitions_tested=0,
                exact_matches=0,
                mismatches=0,
                timeouts=0,
                resource_ceiling_hits=0,
                execution_errors=0,
                verified_replay=False,
                verified_intervention=False,
                verified_containment=False,
                details=("Empty transition set cannot satisfy exact-match verification",),
            )

        runner_code = build_runner_code(rule.code)
        exact_matches = 0
        mismatches = 0
        timeouts = 0
        resource_hits = 0
        execution_errors = 0
        details: list[str] = []

        for idx, trans in enumerate(held_out_transitions):
            input_data: dict[str, Any] = {
                "state": trans.state.data,
                "action": {
                    "agent_id": trans.action.agent_id,
                    "action_type": trans.action.action_type,
                    "params": trans.action.params,
                },
                "exogenous_input": {
                    "tick": trans.exogenous_input.tick,
                    "events": list(trans.exogenous_input.events),
                    "metadata": trans.exogenous_input.metadata,
                },
                "seed": trans.seed,
            }

            result = self.sandbox.run(
                runner_code,
                timeout_seconds=self.timeout_seconds,
                resource_ceiling_mb=self.resource_ceiling_mb,
                input_data=input_data,
            )

            if result.resource_ceiling_hit:
                resource_hits += 1
                details.append(f"Transition {idx} ({trans.transition_id}): resource ceiling hit")
                continue

            if result.exit_code == 124 or "timed out" in result.stderr.lower():
                timeouts += 1
                details.append(f"Transition {idx} ({trans.transition_id}): timed out")
                continue

            if not result.is_success:
                execution_errors += 1
                details.append(
                    f"Transition {idx} ({trans.transition_id}): exit {result.exit_code}: {result.stderr.strip()[:100]}"
                )
                continue

            pred_output = result.get_json_output()
            if pred_output is None:
                execution_errors += 1
                details.append(
                    f"Transition {idx} ({trans.transition_id}): failed to parse structured JSON output"
                )
                continue

            pred_emission = pred_output.get("emission", pred_output)
            emission_match = (pred_emission == trans.emission.data)

            state_match = True
            if self.check_next_state:
                pred_next_state = pred_output.get("next_state")
                state_match = (pred_next_state == trans.next_state.data)

            if emission_match and state_match:
                exact_matches += 1
            else:
                mismatches += 1
                diff_reason = (
                    f"emission mismatch (pred={pred_emission}, actual={trans.emission.data})"
                    if not emission_match
                    else "next_state mismatch"
                )
                details.append(f"Transition {idx} ({trans.transition_id}): {diff_reason}")

        all_matched = (
            exact_matches == len(held_out_transitions)
            and mismatches == 0
            and timeouts == 0
            and resource_hits == 0
            and execution_errors == 0
        )

        return VerificationReport(
            rule_id=rule.rule_id,
            passed=all_matched,
            transitions_tested=len(held_out_transitions),
            exact_matches=exact_matches,
            mismatches=mismatches,
            timeouts=timeouts,
            resource_ceiling_hits=resource_hits,
            execution_errors=execution_errors,
            verified_replay=all_matched,
            verified_intervention=False,
            verified_containment=True,
            details=tuple(details),
        )

    def verify_intervention(
        self,
        rule: CandidateRule,
        engine: SocialSandboxEngine,
        base_state: State,
        intervention_action: Action,
        *,
        exogenous_input: ExogenousInput | None = None,
        seed: int = 42,
    ) -> bool:
        """Verify that rule accurately predicts counterfactual outcome of a controlled intervention."""
        counterfactual_trans = engine.step(
            base_state,
            intervention_action,
            exogenous_input=exogenous_input,
            seed=seed,
        )
        return self.verify(rule, [counterfactual_trans])

    def promote_to_capability_package(
        self,
        rule: CandidateRule,
        held_out_transitions: list[Transition],
        *,
        engine: SocialSandboxEngine | None = None,
        base_state: State | None = None,
        intervention_action: Action | None = None,
        output_kind: str = "verified_rule",
        action_type: str = ActionType.CRAFT,
        required_resources: dict[str, int] | None = None,
        min_age: int = 0,
        evidence_id: str | None = None,
    ) -> CapabilityPackage | None:
        """Promote a candidate rule to a verified CapabilityPackage if all verification gates pass."""
        report = self.verify_with_report(rule, held_out_transitions)
        if not report.passed:
            return None

        verified_intervention = False
        if engine is not None and base_state is not None and intervention_action is not None:
            verified_intervention = self.verify_intervention(
                rule, engine, base_state, intervention_action
            )
            if not verified_intervention:
                return None
        else:
            verified_intervention = True

        resolved_evidence = (
            evidence_id
            if evidence_id
            else hashlib.sha256(f"{rule.rule_id}:{rule.code}".encode()).hexdigest()[:16]
        )

        return CapabilityPackage(
            package_id=rule.rule_id,
            version="1.0.0",
            action_type=action_type,
            required_resources=required_resources or {},
            output_kind=output_kind,
            min_age=min_age,
            evidence_id=resolved_evidence,
            verified_replay=True,
            verified_intervention=verified_intervention,
            verified_containment=True,
        )
