# Comparative Landscape (reviewed 2026-10-21)

`docs/research/literature-review.md` gives the six-thread summary mapped to subsystems. This
document is the fuller picture behind it — the source-status notes, dated benchmark context, and
reasoning that shaped the major design decisions in `docs/ARCHITECTURE.md`, kept in one place so
claims do not have to be re-derived per subsystem.

## The field's own yardstick

ARC-AGI-3 is relevant because it operationalizes one important question: how efficiently can a
system learn an unfamiliar interactive task under a fixed action/observation protocol. It is not a
universal definition of general intelligence and its leaderboard is date-sensitive. The official
ARC material distinguishes public progress from blind evaluation; third-party leaderboard
summaries should not be used as permanent baselines. EvolZen records the benchmark date and source
when it cites ARC-AGI-3, and uses its own EAE metric for a custom world unless the official
protocol is followed exactly [arcprize2026].

## The public-set/private-set gap — the single most load-bearing fact in this design

A different, important pattern remains: specialized agent harnesses and persistent manuals can
substantially improve performance on a reused public set. That is an exposure-regime result, not
automatically evidence of cold-start generalization. Vendor or third-party reports are retained as
case studies, labeled as such, and are not treated as independent replication [agno2026manual].

Read this as a methodological warning: reused-set performance and fresh-set performance answer
different questions. The exact gap is not a permanent constant and must be re-measured for each
system, exposure protocol, model, and benchmark release.

This is why `evolzen.evaluation.procedural_env_gen` exists at all, and why it's a hard
requirement rather than a nice-to-have: `evolzen.evaluation`'s held-out testing must be designed
so it can't quietly collapse into measuring the first thing while believing it measures the
second. See `docs/phases/2.4-2.5-evaluation.md` and `evolzen.evaluation.report.EvaluationReport`,
which makes the reused-vs-fresh gap a required field, not optional.

## Programmatic world-model synthesis

Several recent approaches use actor/synthesizer/verifier systems that build an executable world
model from interaction and check it against replay:

- **OPINE-World** (Courtis, Li & Sanner, `opineworld2026`, `arXiv:2607.01531`): pairs a
  qualitative object-oriented natural-language proto-ontology with an executable Python world model
  and Bayesian uncertainty exploration.
- **Tycho** (Lehmann, Aioanei & Vahdati, `tycho2026`, `arXiv:2607.28287`): formalizes tasks as
  parameterized deterministic transition systems and uses *active abstraction* to decide when to
  construct, test, repair, or bypass executable hypotheses.
- **Executable World Models** (Rodionov, `executableworldmodels2026`, `arXiv:2605.05138`):
  maintains replay-verified Python world models refactored under a Minimum Description Length
  simplicity bias before action planning.

These are relevant design precedents, not proof that the method transfers automatically to a
persistent social sandbox. EvolZen may use an existing coding-agent harness as a candidate
synthesizer, but all generated code remains behind containment and transfer is tested explicitly.

## Representation learning and library learning

- **LeJEPA** (Balestriero & LeCun, `lejepa2025`, `arXiv:2511.08544`) and *When Does LeJEPA
  Learn a World Model?* (`lejepaworldmodel2026`, `arXiv:2605.26379`) replace ad-hoc stop-gradient
  or teacher-student heuristics with Sketched Isotropic Gaussian Regularization (SIGReg),
  building on **I-JEPA** (`assran2023ijepa`, *CVPR* 2023).
- **DreamCoder** (`dreamcoder2021`, *PLDI* 2021) and *Wake-Sleep Event Semantics* (Balogh,
  `wakesleepschank2026`, `arXiv:2603.25975`) demonstrate wake-sleep operator compression over state
  transformations, while **FAISS** (`johnson2019faiss`, *IEEE TBDATA* 2019) supports sparse
  vector retrieval over `evolzen.library`.

The proposed EvolZen combination is not assumed to be necessary, novel, or effective: it must be
compared against simpler state encoders, symbolic baselines, and manual-only conditions.

## Continual learning remains an open engineering risk

Continual learning remains an empirical risk rather than a solved property (*IEEE TPAMI* survey,
`wang2024continualsurvey`). **CLEAR** (`rolnick2019clear`, *NeurIPS* 2019) motivates mixing
off-policy replay with on-policy updates; **TFGN** (Ganguli, `tfgn2026`, `arXiv:2605.15053`)
explores task-free replay-free continual pretraining; and **CLaaS** (Fallah et al., `claas2026`,
`arXiv:2606.05559`) investigates online continual adaptation services. Reported numbers are not
imported as universal baselines for EvolZen; the predictor phase must measure forgetting,
spurious forgetting, forward/backward transfer, adaptation latency, and update cost directly.

## Recent agent-evolution and economic precedents

- **DGM** (`dgm2026`, *ICLR* 2026), **Hyperagents** (Zhang et al., `hyperagents2026`,
  `arXiv:2603.19461`), and **CORAL** (Qu et al., `coral2026`, `arXiv:2604.01658`) demonstrate
  archive-gated empirical self-modification, metacognitive meta-agent editing (`DGM-H`), and
  persistent-memory asynchronous multi-agent evolution.
- **Economy of Minds** (Qi et al., `economyofminds2026`, `arXiv:2606.02859`) and **The AI
  Economist** (`zheng2022aieconomist`, *Science Advances* 2022) motivate market auctions, wealth
  feedback, and specialization rules without centralized scripting.

They do not establish that small local LLM agents with drive vectors will evolve useful social
types or grow a persistent world; EvolZen treats those transfers as hypotheses requiring matched
ablations.

## Diversity collapse is a testable population risk

Chen et al. (`diversitycollapse2026`, *ACL 2026 Findings*, `arXiv:2604.18005`) identify how
structural coupling, dense communication topologies, and authority-driven hierarchy create
"semantic black holes" that collapse idea diversity in multi-agent LLM populations. EvolZen
treats those mechanisms as testable hypotheses alongside **CVT-MAP-Elites** (`vassiliades2018cvtmape`,
*IEEE TEVC* 2018) and limited-resource QD (`qdlimited2024`, *ICML* 2024).

## Containment has moved past cgroup/eBPF

Systems and agent-security literature — **Firecracker** KVM microVMs (`agache2020firecracker`,
*USENIX NSDI* 2020), *Safety Must Precede Open-Ended AI* (Sheth et al., `safetyopenended2025`,
`arXiv:2502.04512`), and **Beyond Static Sandboxing** (Sidik & Rokach, `sidikrokach2026`,
`arXiv:2604.11839`, documenting ~15× tool overprovisioning in default runtimes and ~73% tool
reduction via PPO least-privilege capability scoping) — motivates hardware isolation,
continuous runtime evaluation, and fail-closed default-deny governance. The selected deployment
backend must still pass a target-host threat model before generated code runs outside tests.

## Full reference list

See [`references.bib`](references.bib).
