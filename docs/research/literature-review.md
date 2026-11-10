# Literature Review — Six Research Threads

Six research threads this design draws on. The project combines precedents from peer-reviewed
work, preprints, and vendor reports; the source status is recorded in `references.bib`. The
project's contribution is a measured combination, not an assumption that any one thread solves
the whole problem.

1. **World Models and Interactive System Identification** — executable state-transition models
   and active probing motivate `evolzen.environment` and `evolzen.exploration`; they do not by
   themselves establish causal identification or human-intent understanding.
2. **Continual Learning** — forgetting and spurious forgetting depend on the task sequence and
   update regime. Motivates replay, rollback, and explicit transfer metrics in `library` and
   `predictor`.
3. **Verified World-Model Synthesis** — actor/synthesizer/verifier loops (OPINE-World, Tycho,
   and related preprints) are relevant precedents for the bounded exploration mechanism in
   `evolzen.exploration`.
4. **Program-Synthesis Memory** — DreamCoder's wake/sleep bootstrapping is a component precedent
   for `evolzen.recognition.wake_sleep`, not evidence that a JEPA fusion will work here.
5. **Population Diversity** — quality-diversity and population-design studies motivate explicit
   descriptors, sparse communication, and collapse monitoring in `evolzen.agents.qd_archive`.
6. **Data Provenance** — recursive training on prior generations' own output can reduce diversity
   and rare-behavior coverage (Shumailov et al., Nature 2024). Motivates provenance labels and a
   configured floor in `evolzen.economy.manuals`.
