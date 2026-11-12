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
| Oudeyer, Kaplan & Hafner (2007), *Intrinsic Motivation Systems for Autonomous Mental Development*, *IEEE TEVC*, DOI:10.1109/TEVC.2006.890271 | Developmental competence-progress exploration over life stages | EvolZen's seven-sins-plus-Null basis or greedy candidate scoring |
| Santucci, Baldassarre & Mirolli (2016), *GRAIL*, *IEEE TCDS*, DOI:10.1109/TCDS.2016.2538961 | Autonomous goal discovery and competence-driven skill acquisition in developmental agents | That fixed host-supplied candidate pools achieve open-ended goal discovery |
| Vassiliades, Chatzilygeroudis & Mouret (2018), *CVT-MAP-Elites*, *IEEE TEVC*, DOI:10.1109/TEVC.2017.2735550 | Centroidal Voronoi partitioning to scale QD archives to higher-dimensional descriptor spaces | That EvolZen's 2D `DevelopmentArchive` grid captures all social/behavioral niches |
| Pugh, Soros & Stanley (2016), *Quality Diversity: A New Frontier for Evolutionary Computation*, *Frontiers in Robotics and AI*, DOI:10.3389/frobt.2016.00040 | Conceptual separation of behavioral descriptors from objective fitness | Any specific social ontology or multi-agent communication graph |
| *Hyperagents* (2026), arXiv:2603.19461 | Metacognitive self-modification (`DGM-H`) extending beyond coding tasks via persistent insight/memory structures | Safe execution or bounded growth in `evolzen.agents` without Firecracker/gVisor containment |

Use the stable arXiv identifiers and DOIs with corresponding BibTeX keys: `cook2024cultural`,
`park2023generative`, `mouret2015mapelites`, `hu2021lora`, `dgm2026`, `oudeyer2007intrinsic`,
`santucci2016grail`, `vassiliades2018cvtmape`, `pugh2016qd`, `hyperagents2026`.
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
