# Literature Review — Six Research Threads

Six research threads this design draws on. The project combines precedents from peer-reviewed
work, preprints, and vendor reports; the source status is recorded in `references.bib`. The
project's contribution is a measured combination, not an assumption that any one thread solves
the whole problem.

1. **World Models, Standardized Environments & Evaluation Splits** — executable state-transition
   models (`opineworld2026`, `tycho2026`), standardized multi-agent transition APIs (PettingZoo,
   Terry et al., *NeurIPS* 2021, `terry2021pettingzoo`), and procedural OOD evaluation splits
   (Procgen, Cobbe et al., *ICML* 2020, `cobbe2020procgen`; ARC-AGI-2, Chollet et al.,
   `chollet2025arcagi2`) motivate `evolzen.environment` and `evolzen.evaluation`; they do not by
   themselves establish causal identification or AGI claims.
2. **Continual Learning** — forgetting and spurious forgetting depend on the task sequence and
   update regime (Wang et al., *IEEE TPAMI* 2024, `wang2024continualsurvey`). Motivates replay,
   dynamic-capacity isolation, rollback, and explicit transfer metrics in `library` and
   `predictor`.
3. **Verified World-Model Synthesis & Skill Libraries** — actor/synthesizer/verifier loops
   (OPINE-World, Tycho, and executable skill-library agents such as Voyager, *TMLR* 2023,
   `wang2023voyager`) are relevant precedents for bounded exploration (`evolzen.exploration`) and
   append-only rule retention (`evolzen.library`).
4. **Program-Synthesis Memory** — DreamCoder's wake/sleep bootstrapping is a component precedent
   for `evolzen.recognition.wake_sleep`, not evidence that a JEPA fusion will work here.
5. **Population Diversity & Intrinsic Motivation** — quality-diversity (Pugh et al. 2016;
   CVT-MAP-Elites, *IEEE TEVC* 2018, `vassiliades2018cvtmape`; ICML 2024 `qdlimited2024`) and
   intrinsically motivated developmental learning (*IEEE TEVC* 2007 `oudeyer2007intrinsic`; *IEEE
   TCDS* 2016 `santucci2016grail`) motivate explicit behavioral descriptors, sparse communication,
   and collapse monitoring in `evolzen.agents`. Open-ended environment/agent proposals (OMNI-EPIC
   `faldor2024omniepic`; Hyperagents `hyperagents2026`; Hughes et al. ICML 2024
   `hughes2024openended`) motivate bounded diversity metrics without relaxing `PRD.md` §4 non-goals.
6. **Data Provenance, Economic Mechanisms & Hardware Containment** — recursive training on prior
   generations' own output reduces diversity and rare-behavior coverage (Shumailov et al., *Nature*
   2024, `shumailov2024collapse`), while two-level economic RL (Zheng et al., *Science Advances*
   2022, `zheng2022aieconomist`) informs multi-agent incentive/taxation dynamics in
   `evolzen.economy`. On the systems boundary, KVM microVM virtualization (Firecracker, Agache et
   al., *USENIX NSDI* 2020, `agache2020firecracker`) and default-deny capability governance
   (`sidikrokach2026`) ground `evolzen.containment.Sandbox`.
