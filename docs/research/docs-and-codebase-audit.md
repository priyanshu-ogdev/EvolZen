# Full `docs/` Validation, Literature Expansion & Codebase Progress Match

**Audit date:** 2026-11-12 (updated for branch `env` @ `81ee6eb`, rebased onto `origin/main`)
**Scope:** Automated validation of all files in `docs/` (`mkdocs.yml` navigation, relative markdown links, `arXiv`/`references.bib` cross-checks, `mkdocs build --strict`), section-by-section documentation analysis, peer-reviewed IEEE/ML citation expansion, and empirical matching against `src/evolzen/` and `tests/`.

---

## 1. Automated `docs/` Structural Validation

| Validation check | Result |
|---|---|
| Markdown files inventoried under `docs/` | 58 `.md` files |
| `uv run --group docs mkdocs build --strict` | **Pass** (exit 0, 0 `griffe` warnings after `src/evolzen/schemas/library.py` docstring fix) |
| Missing `mkdocs.yml` nav targets | **0** |
| Orphan `.md` files missing from `mkdocs.yml` | **0** |
| Broken internal relative markdown links | **0** |
| Missing `arXiv:` BibTeX keys in `references.bib` | **0** |

---

## 2. Section-by-Section Documentation vs. Codebase Match

| Documentation section | Verified peer-reviewed / conference citations added | Codebase state (`src/evolzen/` + `tests/`) | Match verdict |
|---|---|---|---|
| **Overview & Foundations** (`PRD.md`, `ARCHITECTURE.md`, `PAPER.md`, `phase-0-foreground.md`, `dependency-stack.md`, `ci-cd.md`) | `references.bib` expanded from 38 to 49 entries (adds IEEE TEVC, TCDS, TPAMI, TBDATA, Nature, Science Advances, PNAS, USENIX NSDI, ICML, NeurIPS, CVPR, TMLR) | `config.py`, `logging.py`, `tracking.py`, `schemas/` (`transition.py`, `world.py`, `development.py`, `library.py`, `manual.py`, `drive_vector.py`), `storage/transition_log.py` (`TransitionLogStore` implemented; 4 tests), `tests/core/` (10 tests), `cli/main.py` (stub `NotImplementedError` ×3), `ci.yml` | **Aligned** (`phase-0-foreground.md` now lists the implemented `environment`, `agents/development/`, `storage/transition_log.py`, and `library/` baselines while marking the Phase 0 checklist as historical); `configs/**` and `src/evolzen/cli/**` remain outside `ci.yml` test path filters |
| **Phase 1.1 Environment** ([1.1-environment.md](../phases/1.1-environment.md), [subsystems/environment](../subsystems/environment/README.md)) | Terry et al. (*PettingZoo*, *NeurIPS* 2021); Faldor et al. (*OMNI-EPIC*, `arXiv:2405.15568`) contrast; Cobbe et al. (*Procgen*, *ICML* 2020) | Implemented code baseline (`0` stubs): `SocialSandboxEngine` (17 `ActionType` handlers), `schemas/world.py`, `TransitionLogStore` (DuckDB + SHA-256 hash chain + snapshots/branches), `invariants.py`, `growth.py`, `replay.py`, `interventions.py`, `adapter.py`, `SocialSandboxAECEnv` (`pettingzoo_env.py`), `pilot.py`; **35 tests** (27 `tests/environment/` + 4 `tests/schemas/test_world.py` + 4 `tests/storage/`) | **Implemented baseline with documented hardening backlog:** open issues `ENV-01`–`ENV-08` (replay state propagation, `up_to_tick` inclusion for `same_tick=True`, `apply_intervention` indexing/`initial_currency`, `SocialSandboxAECEnv` exogenous/seed/store hooks, `max_agents` counting dead agents, unbounded `WorldState` collections and `status` upper bound, unreachable `ENDOGENOUS_PROCESS`), partial mechanics (`ContractRecord` cancel/expiry, `REGISTER_CAPABILITY` `CRAFT`-only, `contribution_rate`, `durability`, `NormRecord` enforcement, unknown exogenous events), `adapter.legal_candidates` surfacing 7/17 `ActionType`s, `invariants.py` 18 failure branches untested, Hypothesis/long-horizon/target-rig empirical pilots **untested** |
| **Phase 1.2 Agents** ([1.2-agents.md](../phases/1.2-agents.md), [subsystems/agents/](../subsystems/agents/README.md)) | Oudeyer et al. (*IEEE TEVC* 2007), Santucci et al. (*IEEE TCDS* 2016), Vassiliades et al. (*IEEE TEVC* 2018), Pugh et al. (*Frontiers* 2016), *Hyperagents* (`arXiv:2603.19461`) | `agents/development/` deterministic 8-drive core + `schemas/development.py` implemented (**32 test cases**: 29 in `tests/agents/development/` + 3 in `tests/schemas/test_development.py`); legacy 5-drive `Agent`, `qd_archive.py` (**2 tests**), `self_modification.py`, `inference.py` (`NotImplementedError` ×2) remain separate | **Matches doc status:** dual-path split is accurately flagged in `agents/README.md`; `AgentProfile` schema, LLM/constrained decoding, scheduler, and multi-generation empirical runs remain unimplemented |
| **Phase 1.3 Economy** ([1.3-economy.md](../phases/1.3-economy.md), [subsystems/economy](../subsystems/economy/README.md)) | Shumailov et al. (*Nature* 2024, enriched DOI), Zheng et al. (*The AI Economist*, *Science Advances* 2022) | `schemas/manual.py`, `economy/manuals.py` (`ManualStore`), `economy/market.py` (`Market`); **5 tests** | **Matches doc status:** basic ledger/provenance helpers exist; `NonNegInt` currency/`ActionType.TRADE` alignment with `WorldState`, `ProvenanceRecord`, and manual falsification loop remain unimplemented |
| **Phase 1.4 Exploration** ([1.4-exploration.md](../phases/1.4-exploration.md), [subsystems/exploration](../subsystems/exploration/README.md)) | Romera-Paredes et al. (*FunSearch*, *Nature* 2024), Pathak et al. (*ICM*, *ICML* 2017), Wang et al. (*Voyager*, *TMLR* 2023) | `exploration/actor.py` (minimal, **1 test**), `synthesizer.py` (`Protocol` + `CandidateRule`), `verifier.py` (`NotImplementedError`) | **Matches doc status:** verifier, 4-arg transition contract alignment, and sandboxed harness integration remain unimplemented |
| **Phase 1.5 Library** ([1.5-library.md](../phases/1.5-library.md), [subsystems/library](../subsystems/library/README.md), [ADR 0007](../adr/0007-library-persistence.md)) | Wang et al. (*IEEE TPAMI* 2024), Wang et al. (*Voyager*, *TMLR* 2023), Ferguson (1973) | Full DuckDB + JSONL implementation (`schemas/library.py` with `Attributes:` docstrings, `persistence.py`, `rule_library.py`, `validity.py`, `audit.py`, `regression_bank.py`, `LibrarySettings`, `configs/library.yaml`); **77 tests** including 3-round zero-forgetting test | **Implemented with explicit boundary:** fixture-based bank verified locally; live Phase 1.4 verifier + Phase 2.2 `Sandbox` execution remains **untested** until those phases leave stub status |
| **Phase 2.1 Predictor** ([2.1-predictor.md](../phases/2.1-predictor.md), [subsystems/predictor](../subsystems/predictor/README.md)) | Wang et al. (*IEEE TPAMI* 2024), Rolnick et al. (*CLEAR*, *NeurIPS* 2019), Kirkpatrick et al. (*EWC*, *PNAS* 2017), Shao et al. (*DeepSeekMath/GRPO*, `arXiv:2402.03300`) | `rehearsal_buffer.py` (**2 tests**); `planner.py` (`NotImplementedError` ×2) | **Matches doc status:** buffer helper exists; training/metrics and `TransitionLogStore` batching remain unimplemented |
| **Phase 2.2 Containment** ([2.2-containment.md](../phases/2.2-containment.md), [subsystems/containment](../subsystems/containment/README.md)) | Agache et al. (*Firecracker*, *USENIX NSDI* 2020) | `governance.py` (**2 tests**); `sandbox.py` (`Protocol` + `ExecutionResult` only) | **Matches doc status:** static capability check exists; KVM/gVisor backend, `CapabilityPackage` wiring, & kill-switch verification remain unimplemented |
| **Phase 2.3 Recognition** ([2.3-recognition.md](../phases/2.3-recognition.md), [subsystems/recognition](../subsystems/recognition/README.md)) | Assran et al. (*I-JEPA*, *CVPR* 2023), Johnson et al. (*FAISS*, *IEEE TBDATA* 2019), Ellis et al. (*DreamCoder*, *PLDI* 2021) | `embedding_router.py` (**1 test**), `moe_library.py` (wired to `RuleLibrary.get` → `RuleEntry`), `jepa.py` (empty scaffold), `wake_sleep.py` (`NotImplementedError` ×2) | **Matches doc status:** router scaffold exists; JEPA/wake-sleep training & ablation matrix remain unimplemented |
| **Phase 2.4–2.5 Evaluation** ([2.4-2.5-evaluation.md](../phases/2.4-2.5-evaluation.md), [subsystems/evaluation](../subsystems/evaluation/README.md)) | Cobbe et al. (*Procgen*, *ICML* 2020), Chollet (`arXiv:1911.01547`), Chollet et al. (*ARC-AGI-2*, `arXiv:2505.11831`) | `report.py` (**3 tests**), `rhae_scorer.py` (**3 tests**), `procedural_env_gen.py` (`NotImplementedError`) | **Matches doc status:** legacy helpers only; `EAE_B` formula from `agents/evaluation.md` and procedural generator remain unimplemented |

---

## 3. Repository Test Snapshot (Verified 2026-11-12 on `env` @ `81ee6eb`)

- **Core / shared (`tests/core/`):** **10** tests passing (`test_config.py`: 5, `test_schemas.py`: 3, `test_tracking.py`: 2)
- **Developmental agents (`tests/agents/` + `tests/schemas/test_development.py`):** **34** tests passing (`tests/agents/development/`: 29 + `tests/schemas/test_development.py`: 3 = 32 developmental-core cases; `tests/agents/test_qd_archive.py`: 2 legacy QD)
- **Economy (`tests/economy/`):** **5** tests passing (`test_manuals.py`: 3, `test_market.py`: 2)
- **Environment & storage (`tests/environment/` + `tests/schemas/test_world.py` + `tests/storage/`):** **35** tests passing (`tests/environment/`: 27, `tests/schemas/test_world.py`: 4, `tests/storage/`: 4)
- **Exploration (`tests/exploration/`):** **1** test passing (`test_actor.py`: 1)
- **Library (`tests/library/`):** **77** tests passing (`test_audit.py`: 12, `test_integration.py`: 1, `test_persistence.py`: 12, `test_regression_bank.py`: 13, `test_rule_library.py`: 15, `test_schemas.py`: 12, `test_validity.py`: 12)
- **Predictor (`tests/predictor/`):** **2** tests passing (`test_rehearsal_buffer.py`: 2)
- **Containment (`tests/containment/`):** **2** tests passing (`test_governance.py`: 2)
- **Recognition (`tests/recognition/`):** **1** test passing (`test_embedding_router.py`: 1)
- **Evaluation (`tests/evaluation/`):** **6** tests passing (`test_report.py`: 3, `test_rhae_scorer.py`: 3)
- **Total:** **173 passed** (`uv run pytest -v`), `uv run ruff check .` clean, `uv run mypy src` clean (65 source files, 0 issues), `uv run --group docs mkdocs build --strict` clean (0 warnings).

---

## 4. Research Domain Validation & Verified Paper Breakdown

Every 2025–2026 citation in `references.bib` and newly added peer-reviewed IEEE/ML papers were
verified against public bibliographic records (authors, venues, DOIs/arXiv IDs, and mechanisms):

| Domain pillar | Verified primary papers | Mechanism validated in EvolZen | Boundary / untested scope |
|---|---|---|---|
| **Interactive World Modeling** | **OPINE-World** (`arXiv:2607.01531`, Courtis, Li & Sanner); **Tycho** (`arXiv:2607.28287`, Lehmann, Aioanei & Vahdati); **Executable World Models** (`arXiv:2605.05138`, Rodionov) | Separable proto-ontology + executable hypothesis verification + MDL refactoring in `exploration` (`Actor` / `Synthesizer` / `Verifier`) | Tested on ARC-AGI-3 interactive grids; persistent social-sandbox transfer remains **untested** |
| **Intrinsic Developmental Agents & QD** | Oudeyer et al. (*IEEE TEVC* 2007); Santucci et al. (*IEEE TCDS* 2016); Vassiliades et al. (*IEEE TEVC* 2018); Chen et al. (*ACL 2026 Findings*, `arXiv:2604.18005`) | Separating behavioral descriptors from fitness, CVT scaling, and avoiding semantic-collapse topologies | Greedy `agents/development` choice scoring lacks competence-progress exploration until controlled ablation |
| **Lifelong Rule Libraries & Continual Learning** | Wang et al. (*IEEE TPAMI* 2024); Rolnick et al. (*CLEAR*, *NeurIPS* 2019); Wang et al. (*Voyager*, *TMLR* 2023); Ganguli (`arXiv:2605.15053`); Fallah et al. (`arXiv:2606.05559`) | Append-only parameter/rule isolation (`LibraryStore` + `RegressionBank` + `ValidityContext`) + bounded replay (`RehearsalBuffer`) | Fixture regression verified locally (`tests/library/`); neural predictor replay/transfer curves unmeasured |
| **Latent Representation & Sparse Routing** | Assran et al. (*I-JEPA*, *CVPR* 2023); Balestriero & LeCun (`arXiv:2511.08544`); Balogh (`arXiv:2603.25975`); Johnson et al. (*IEEE TBDATA* 2019) | SIGReg regularized predictive latents (`JEPAEncoder`), wake-sleep operators, and FAISS inner-product routing (`EmbeddingRouter`) | Untested hypothesis vs simpler symbolic/MLP encoders (`2.3-recognition.md`) |
| **Containment & Capability Governance** | Agache et al. (*Firecracker*, *USENIX NSDI* 2020); Sidik & Rokach (`arXiv:2604.11839`); Sheth et al. (`arXiv:2502.04512`) | KVM microVMs (~5 MB footprint), continuous safety evaluation, and default-deny least-privilege scoping (mitigating ~15× default tool overprovisioning) | `CapabilityGovernor` implemented; Firecracker/gVisor backend and target-host threat tests pending |
| **OOD Evaluation & Non-AGI Scope** | Chollet (`arXiv:1911.01547`); Chollet et al. (`arXiv:2505.11831`, *ARC-AGI-2*); Cobbe et al. (*ICML* 2020, *Procgen*) | Procedural seed/mechanic splits (`reused-vs-fresh`) separating memorized priors from fluid adaptation (`EAE`) | Reaffirms `PRD.md` §4 (`NG1`): bounded evaluation only, zero AGI/ASI claims |
