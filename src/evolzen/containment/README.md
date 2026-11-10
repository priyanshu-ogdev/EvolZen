# evolzen.containment — Phase 2.2

**Goal:** install replay/intervention promotion checks and fail-closed containment in a form that's actually implementable
and actually protective, matching the isolation stack to the real risk profile of a
self-modifying, code-writing agent population.

Full research design: [`docs/phases/2.2-containment.md`](../../../docs/phases/2.2-containment.md).

## What's here

| File | Purpose |
|---|---|
| [`sandbox.py`](sandbox.py) | `Sandbox` protocol — **interface only**; assumes a Firecracker-microVM- or gVisor-backed executor. |
| [`governance.py`](governance.py) | `CapabilityGovernor` — fail-closed, per-capability policy that may tighten access based on behavior but cannot bypass static default-deny controls. |

## How to build this

1. **Stand this up early, before any synthesized or self-modified code executes.** Every
   piece of code originating from `evolzen.exploration.synthesizer`,
   `evolzen.agents.self_modification`, or `evolzen.library` must run inside a `Sandbox`
   implementation — not a plain subprocess call, not a bare shared-kernel container. See
   `SECURITY.md`.
2. Provision the actual Firecracker/gVisor infrastructure on the DGX Spark — this is
   infrastructure work, not a Python dependency, and remains outside this repository's Phase 0
   implementation scope.
3. Reuse the exploration promotion standard, strengthened with replay, held-out combinations,
   intervention, resource-bound, and validity-context checks.
4. Follow the safeguard checklist: isolated workspaces, evaluator separation, resource ceilings,
   session/health management, egress control, kill-switch latency, recovery, and tamper-evident
   logging.

**Success metric:** interface, backend, and target-host tests each demonstrate no unlogged action,
no unbounded resource use, fail-closed denial, bounded kill-switch latency, clean recovery, and
preserved audit logs. The report must state which layer was actually tested.

**Depends on:** nothing from the other subsystems — this can be built immediately, in parallel
with anything else (see `docs/PRD.md` §12).
**Depended on by:** every subsystem that executes agent-originated code
(`evolzen.exploration`, `evolzen.agents`, `evolzen.library`).
