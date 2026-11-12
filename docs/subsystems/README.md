# Subsystem design navigation

One package, nine subsystems. This documentation hierarchy does not create new packages.
Requirements live in [PRD](../PRD.md); cross-system boundaries in
[Architecture](../ARCHITECTURE.md); experiments in [research](../research/README.md).
Subsystem folders hold detailed contracts, rationale and implementation status.

| Folder | Responsibility | Phase authority |
|---|---|---|
| [environment](environment/README.md) | World state, clocks, observations, authoritative outcomes | [1.1](../phases/1.1-environment.md) |
| [agents](agents/README.md) | Birth, eight drives, development, personal learning and teaching | [1.2](../phases/1.2-agents.md) |
| [economy](economy/README.md) | Resource transfers, manuals and provenance | [1.3](../phases/1.3-economy.md) |
| [exploration](exploration/README.md) | Proposals, experiments and replay verification | [1.4](../phases/1.4-exploration.md) |
| [library](library/README.md) | Versioned reusable artifacts | [1.5](../phases/1.5-library.md) |
| [predictor](predictor/README.md) | Outcome and intent prediction | [2.1](../phases/2.1-predictor.md) |
| [containment](containment/README.md) | Execution permissions and isolation | [2.2](../phases/2.2-containment.md) |
| [recognition](recognition/README.md) | Transferable proposal priors | [2.3](../phases/2.3-recognition.md) |
| [evaluation](evaluation/README.md) | Independent measurements and frozen final evaluation | [2.4–2.5](../phases/2.4-2.5-evaluation.md) |

Detailed agent documents supersede earlier five-coordinate Phase 0 interface stubs **for the active
developmental path**. Phase 1.1 world and action schemas are now implemented in
`src/evolzen/schemas/world.py` (`WorldState`, `ActionType`, `CapabilityPackage`) and
`src/evolzen/environment/adapter.py`; reconciling or retiring those legacy five-coordinate Phase 0
stubs against the active eight-coordinate developmental core remains an explicit Phase 1.2 action
item.
