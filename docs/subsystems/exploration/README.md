# Exploration integration

Authority: [Phase 1.4](../../phases/1.4-exploration.md).
Source package: `src/evolzen/exploration/`.

Agents' preference equations rank opportunities; they are not autonomous hypothesis synthesis.
Keep empirical evidence separate from generated plans and reflection. Use declared observation
budgets and intervention permissions. All generated rule/policy code executes only in Sandbox.
The new greedy developmental core does not implement information-gain planning or curiosity;
compare an exploration controller separately at equal budgets.
