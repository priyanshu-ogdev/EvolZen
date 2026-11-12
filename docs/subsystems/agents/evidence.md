# Evidence ledger for developmental agents

**Checked October 24, 2026 (expanded November 12, 2026):** author arXiv abstract/metadata pages
and peer-reviewed journal records for the following component precedents were retrieved. This is
not a systematic literature review, full-paper replication, novelty proof, or validation of every
older citation in the repository.

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
| Merrick (2010), *A Comparative Study of Value Systems for Self-Motivated Exploration and Learning by Robots*, *IEEE TAMD* (now *TCDS*), DOI:10.1109/TAMD.2010.2051435 | Controlled head-to-head benchmarking of competing intrinsic value systems on exploration/competence | That an eight-drive tendency matrix outperforms curiosity or competence-progress baselines |
| Hayes et al. (2022), *A practical guide to multi-objective reinforcement learning and planning*, *AAMAS*, DOI:10.1007/s10458-022-09552-y | Formalizes EvolZen's weighted outcome sum as MORL linear scalarization and defines when non-linear utility is required | That linear scalarization discovers non-convex Pareto-optimal trade-offs |
| Keramati & Gutkin (2014), *Homeostatic reinforcement learning for integrating reward collection and physiological stability*, *eLife*, DOI:10.7554/eLife.04811 | Grounds internal discrepancy features (`x_t`) as homeostatic drive-reduction weights modulating action utility | Moral or psychological validity of the seven-sins coordinate names |
| Colas, Karch, Sigaud & Oudeyer (2022), *Autotelic Agents with Intrinsically Motivated Goal-Conditioned RL*, *JAIR*, arXiv:2012.09830 | Integrating intrinsic goal sampling, autotelic curricula, and cultural/social skill repertoires | That greedy candidate ranking alone produces autotelic open-ended growth |
| Asadi & Littman (2017), *An Alternative Softmax Operator for Reinforcement Learning*, *ICML*, arXiv:1612.05628 | Non-expansion properties of Mellowmax vs. Boltzmann softmax fixed-point instabilities in sequential choice | Any unmeasured stochastic policy improvement in EvolZen's social sandbox |
| Klyubin, Polani & Nehaniv (2005), *Empowerment: A universal agent-centric measure of control*, *IEEE CEC*, DOI:10.1109/CEC.2005.1554676 | Information-theoretic channel capacity between actions and future sensory states as a task-independent measure of control | That fixed 8-drive ratios preserve or maximize empowerment |
| Schmidhuber (2010), *Formal Theory of Creativity, Fun, and Intrinsic Motivation (1990–2010)*, *IEEE TAMD*, DOI:10.1109/TAMD.2010.2056368 | Predictive compression-progress derivative as a formal intrinsic reward for active exploration | That `Null` (abstention) or non-predictive drives yield curiosity |
| Leibo et al. (2017), *Multi-agent Reinforcement Learning in Sequential Social Dilemmas*, *AAMAS*, arXiv:1702.03037 | Temporally extended Markov-game framing for cooperation/defection under resource scarcity | Any cooperative outcome from single-step utility weights alone |
| Foerster et al. (2018), *Learning with Opponent-Learning Awareness*, *ICLR*, arXiv:1709.04326 | Differentiating through peer learning updates to mitigate non-stationarity and emerge cooperation | Convergence of independent EMA learners without opponent awareness |

Use the stable arXiv identifiers and DOIs with corresponding BibTeX keys: `cook2024cultural`,
`park2023generative`, `mouret2015mapelites`, `hu2021lora`, `dgm2026`, `oudeyer2007intrinsic`,
`santucci2016grail`, `vassiliades2018cvtmape`, `pugh2016qd`, `hyperagents2026`,
`merrick2010valuesystems`, `hayes2022morl`, `keramati2014homeostatic`, `colas2022autotelic`,
`asadi2017mellowmax`, `klyubin2005empowerment`, `schmidhuber2010creativity`, `leibo2017ssd`,
`foerster2018lola`.
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
