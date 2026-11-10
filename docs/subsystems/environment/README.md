# Environment integration

Authority: [Phase 1.1](../../phases/1.1-environment.md).
Source package: `src/evolzen/environment/`.

Own the world clock, agent observations, legal candidate generation, execution and outcome
verification. Developmental agents consume eight normalized observable features and return a
pending action ID; they do not mutate world state themselves. The environment must recheck age,
resources, permissions and action parameters, then issue a matching trusted outcome receipt.
Version context/skill keys with mechanics and meaningful action parameters.

The environment remains a contract and implementation boundary. Population health, birth
ceilings, institutions, shocks and production event persistence remain unimplemented.
See [agent engineering](../agents/engineering.md) for the broader boundaries.
