# Evidence ledger for developmental agents

**Checked October 24, 2026:** author arXiv abstract/metadata pages for the following component
precedents were retrieved. This is not a systematic literature review, full-paper replication,
novelty proof, or validation of every older citation in the repository.

| Source | What it supports here | What it does not establish |
|---|---|---|
| Cook, Lu, Hughes, Leibo, Foerster (2024), *Artificial Generational Intelligence: Cultural Accumulation in Reinforcement Learning*, arXiv:2406.00392v2 | Distinguishing within-lifetime learning, intergenerational transfer and matched total experience | Seven-sins psychology, LLM childhood or this teaching algorithm |
| Park et al. (2023), *Generative Agents: Interactive Simulacra of Human Behavior*, arXiv:2304.03442v2 | Memory, reflection and planning as separable simulation components | Neural self-training, faithful human psychology or general intelligence |
| Mouret & Clune (2015), *Illuminating search spaces by mapping elites*, arXiv:1504.04909v1 | Behavioral archives rather than selecting one best phenotype | That randomly distinct genomes imply behavioral diversity |
| Hu et al. (2021), *LoRA: Low-Rank Adaptation of Large Language Models*, arXiv:2106.09685v2 | Efficient adaptation while freezing base weights | Rank-by-age schedules, immunity to forgetting, or safe adapter crossover |
| Zhang et al. (2025; revised 2026), *Darwin Godel Machine*, arXiv:2505.22954v3 | Empirical evaluation and archives of self-modified coding agents with safeguards | Safety without deployment validation, autonomous children, or validation of EvolZen |

Use the stable arXiv identifiers and corresponding BibTeX keys: `cook2024cultural`,
`park2023generative`, `mouret2015mapelites`, `hu2021lora`, `dgm2026`.
The titles' use of “intelligence” does not extend the scope of EvolZen's claims.

Official implementation documentation inspected on the same date: gVisor's **What is gVisor?**
page (`gvisor.dev/docs/`) describes a userspace application kernel, explicitly not an ordinary
VM; Firecracker's project page (`firecracker-microvm.github.io`) describes KVM-backed microVMs.
These clarify isolation terminology, not the security of an untested EvolZen deployment.

## Explicitly unsupported hypotheses

- Seven sins plus Null span all personality or emotional dimensions.
- A randomized equation is equivalent to subjective thought or human intention.
- Age causes competence, or an exponential plasticity curve reflects real development.
- More generations guarantee cultural accumulation.
- Local numerical learning is equivalent to continual neural training.
- A public/private leaderboard gap is a controlled estimate of the benefit of manuals.

These assertions are not adopted. The documents instead specify observable behavior, matched
comparisons and clear implementation status. The equation, budgets, stage thresholds, action
ranking, advice weights and EMA updates are **EvolZen design decisions, empirically untested**.
