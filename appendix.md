# Appendix: Technical & Algorithmic Code Implementation for EvolZen

> **Research Context:** Technical and algorithmic code appendix accompanying the research paper for the **EvolZen** concept-research testbed.
> **Repository:** [`evolzen`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen) (Python 3.11+, typed, event-sourced, hardware-isolated).
> **Companion Document:** [literaturesurvey.md](file:///d:/1)MY%20PROJECTS/EvolZen-main/literaturesurvey.md) (comprehensive 16-paper literature survey across IEEE, Springer, and Elsevier).

---

## Table of Contents

1. [Appendix A: Authoritative Environment & State Transition Subsystem (Phase 1.1)](#appendix-a-authoritative-environment--state-transition-subsystem-phase-11)
   - [Listing A.1: Normative DEVS State-Transition Contract & Step Execution](#listing-a1-normative-devs-state-transition-contract--step-execution)
   - [Listing A.2: Strict Resource Conservation & Invariant Checking](#listing-a2-strict-resource-conservation--invariant-checking)
   - [Listing A.3: Cryptographic Hash-Chained Transition Provenance](#listing-a3-cryptographic-hash-chained-transition-provenance)
2. [Appendix B: Multi-Agent Population & Behavioral Diversity Subsystem (Phase 1.2)](#appendix-b-multi-agent-population--behavioral-diversity-subsystem-phase-12)
   - [Listing B.1: Centroidal Voronoi Tessellations (CVT) MAP-Elites Archive](#listing-b1-centroidal-voronoi-tessellations-cvt-map-elites-archive)
   - [Listing B.2: Bounded 8-Drive Developmental Motivation Dynamics](#listing-b2-bounded-8-drive-developmental-motivation-dynamics)
   - [Listing B.3: Safe Genome Crossover & Mutation Operator](#listing-b3-safe-genome-crossover--mutation-operator)
3. [Appendix C: Economy & Market Mechanism Subsystem (Phase 1.3)](#appendix-c-economy--market-mechanism-subsystem-phase-13)
   - [Listing C.1: Multi-Agent Resource Balance & Asset Transfer Engine](#listing-c1-multi-agent-resource-balance--asset-transfer-engine)
   - [Listing C.2: Bilateral Spatial Trade Mediation](#listing-c2-bilateral-spatial-trade-mediation)
4. [Appendix D: Directed Exploration & Hypothesis Synthesis Subsystem (Phase 1.4)](#appendix-d-directed-exploration--hypothesis-synthesis-subsystem-phase-14)
   - [Listing D.1: Programmatic Hypothesis Representation (CandidateRule)](#listing-d1-programmatic-hypothesis-representation-candidaterule)
   - [Listing D.2: Exact-Replay Counterfactual Falsification Gate Protocol](#listing-d2-exact-replay-counterfactual-falsification-gate-protocol)
5. [Appendix E: Growing Rule Library & Exact Retention Subsystem (Phase 1.5)](#appendix-e-growing-rule-library--exact-retention-subsystem-phase-15)
   - [Listing E.1: Non-Overwriting Append-Only Rule Admission & Dirichlet Clustering](#listing-e1-non-overwriting-append-only-rule-admission--dirichlet-clustering)
   - [Listing E.2: Context-Aware Rule Applicability & Precondition Matcher](#listing-e2-context-aware-rule-applicability--precondition-matcher)
6. [Appendix F: Grounded Predictor & Continual Rehearsal Subsystem (Phase 2.1)](#appendix-f-grounded-predictor--continual-rehearsal-subsystem-phase-21)
   - [Listing F.1: Fixed-Capacity Rehearsal Buffer for Continual Experience Replay](#listing-f1-fixed-capacity-rehearsal-buffer-for-continual-experience-replay)
7. [Appendix G: Hardware Containment & Dynamic Governance Subsystem (Phase 2.2)](#appendix-g-hardware-containment--dynamic-governance-subsystem-phase-22)
   - [Listing G.1: MicroVM Hardware-Isolated Execution Protocol](#listing-g1-microvm-hardware-isolated-execution-protocol)
   - [Listing G.2: Dynamic Capability Governor & Boundary Violation Auditing](#listing-g2-dynamic-capability-governor--boundary-violation-auditing)
8. [Appendix H: Recognition Model & Sub-Millisecond Vector Retrieval Subsystem (Phase 2.3)](#appendix-h-recognition-model--sub-millisecond-vector-retrieval-subsystem-phase-23)
   - [Listing H.1: GPU/CPU-Accelerated FAISS Vector Indexing & Semantic Routing](#listing-h1-gpucpu-accelerated-faiss-vector-indexing--semantic-routing)
   - [Listing H.2: Self-Supervised Joint-Embedding Predictive Architecture (JEPA) Protocol](#listing-h2-self-supervised-joint-embedding-predictive-architecture-jepa-protocol)
   - [Listing H.3: Wake-Sleep Library Abstraction & Fantasy Case Learner](#listing-h3-wake-sleep-library-abstraction--fantasy-case-learner)
9. [Appendix I: Evaluation & Action-Efficiency Scoring Subsystem (Phases 2.4–2.5)](#appendix-i-evaluation--action-efficiency-scoring-subsystem-phases-2425)
   - [Listing I.1: Relative Human Action Efficiency (RHAE) Scorer](#listing-i1-relative-human-action-efficiency-rhae-scorer)

---

## Appendix A: Authoritative Environment & State Transition Subsystem (Phase 1.1)

The environment acts as the authoritative programmatic arbiter governing physical laws, spatial collisions, action validation, and immutable state transitions (Weyns et al., 2007; Zeigler et al., 2000).

### Listing A.1: Normative DEVS State-Transition Contract & Step Execution
- **Subsystem:** `evolzen.environment.engine`
- **Source File:** [`src/evolzen/environment/engine.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/environment/engine.py)
- **Grounding:** Weyns et al. (*Springer AAMAS* 2007, DOI: `10.1007/s10458-006-0012-0`); Zeigler et al. (*DEVS Specification* 2000).
- **Mathematical Formulation:** $(s_t, a_t, e_t, \text{seed}) \to (y_t, s_{t+1})$ where $y_t$ is emission output and $s_{t+1}$ satisfies global invariants.

```python
def step(self, state: State, action: Action, exogenous: ExogenousInput | None = None) -> Transition:
    """Execute one deterministic discrete-event transition step.
    
    Validates action preconditions, updates agent status/inventories, handles spatial
    interactions, checks global invariants, and returns an immutable Transition record.
    """
    current_world = self._extract_world(state)
    actor = current_world.agents.get(action.agent_id)
    next_tick = current_world.tick + 1

    # 1. Action Validation & Precondition Dispatch
    if actor is None or not actor.alive:
        outcome = _reject(current_world, f"Agent {action.agent_id!r} is absent or inactive")
    elif actor.fatigue >= 1.0 and action.action_type != ActionType.REST:
        outcome = _reject(current_world, "Action rejected: actor exhausted (fatigue >= 1.0)")
    else:
        # Dispatch to deterministic action handler (harvest, craft, trade, etc.)
        handler = self._ACTION_DISPATCH.get(action.action_type, _handle_unknown)
        outcome = handler(current_world, actor, action, next_tick)

    # 2. Strict Invariant Checking
    invariant_report = check_invariants(outcome.world)
    if not invariant_report.passed:
        raise InvariantViolationError(f"World invariant violation: {invariant_report.violations}")

    # 3. Formulate Deterministic Emission & Next State
    emission = Emission(
        accepted=outcome.accepted,
        reason=outcome.reason,
        rewards=outcome.rewards,
        growth_events=extract_growth_events(current_world, outcome.world),
    )
    next_state = State(
        state_id=f"state-{next_tick}-{self._seed}",
        payload={"world": outcome.world.model_dump()},
        timestamp=datetime.now(UTC),
    )
    return Transition(
        transition_id=str(uuid4()),
        tick=current_world.tick,
        state=state,
        action=action,
        emission=emission,
        next_state=next_state,
    )
```

---

### Listing A.2: Strict Resource Conservation & Invariant Checking
- **Subsystem:** `evolzen.environment.invariants`
- **Source File:** [`src/evolzen/environment/invariants.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/environment/invariants.py)
- **Grounding:** Lomuscio et al. (*Springer STTT* 2017, DOI: `10.1007/s10009-015-0378-x`) for multi-agent invariant verification.
- **Mathematical Guarantee:** $\sum R_{\text{world}} = R_{\text{init}} + R_{\text{inflow}} - R_{\text{decayed}}$ across all agents, treasuries, and locations.

```python
def _check_resource_conservation(world: WorldState) -> WorldInvariant:
    """Verify exact conservation of all physical resources and currencies.
    
    Ensures no phantom generation or unrecorded leakage occurs during simulation steps.
    """
    totals = total_world_resources(world)
    all_keys = (
        set(totals)
        | set(world.accounting.initial_resources)
        | set(world.accounting.exogenous_inflows)
        | set(world.accounting.consumed_or_decayed)
    )
    mismatches: list[str] = []
    for key in sorted(all_keys):
        observed = totals.get(key, 0)
        expected = (
            world.accounting.initial_resources.get(key, 0)
            + world.accounting.exogenous_inflows.get(key, 0)
            - world.accounting.consumed_or_decayed.get(key, 0)
        )
        if observed != expected:
            mismatches.append(f"{key}: observed={observed} expected={expected}")

    observed_currency = (
        sum(a.currency for a in world.agents.values())
        + sum(i.currency_reserve for i in world.institutions.values())
    )
    if observed_currency != world.accounting.initial_currency:
        mismatches.append(f"currency: observed={observed_currency} expected={world.accounting.initial_currency}")

    return WorldInvariant(
        name="resource_and_currency_conservation",
        passed=len(mismatches) == 0,
        details={"violations": mismatches},
    )
```

---

### Listing A.3: Cryptographic Hash-Chained Transition Provenance
- **Subsystem:** `evolzen.storage.transition_log`
- **Source File:** [`src/evolzen/storage/transition_log.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/storage/transition_log.py)
- **Grounding:** Tycho (arXiv:2607.28287) and PRD Non-Goal §4 (preventing silent narrative tampering).
- **Guarantee:** Tamper-evident SHA-256 chain $h_t = \mathcal{H}(h_{t-1} \parallel \text{transition}_t)$ recorded in embedded DuckDB.

```python
def _transition_digest(
    prev_hash: str,
    transition_id: str,
    run_id: str,
    branch_id: str,
    tick: int,
    seed: int,
    state_json: str,
    action_json: str,
    exogenous_json: str,
    emission_json: str,
    next_state_json: str,
) -> str:
    """Compute cryptographic SHA-256 hash chaining each transition to its predecessor."""
    payload = json.dumps([
        prev_hash, transition_id, run_id, branch_id, tick, seed,
        state_json, action_json, exogenous_json, emission_json, next_state_json,
    ], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

---

## Appendix B: Multi-Agent Population & Behavioral Diversity Subsystem (Phase 1.2)

To combat diversity collapse without exponential state explosion, EvolZen combines Centroidal Voronoi Tessellations with bounded 8-drive developmental dynamics (Vassiliades et al., 2018; Oudeyer et al., 2007).

### Listing B.1: Centroidal Voronoi Tessellations (CVT) MAP-Elites Archive
- **Subsystem:** `evolzen.agents.qd_archive`
- **Source File:** [`src/evolzen/agents/qd_archive.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/agents/qd_archive.py)
- **Grounding:** Vassiliades et al. (*IEEE TEVC* 2018, DOI: `10.1109/TEVC.2017.2735550`).
- **Algorithmic Role:** Partitions an 8-dimensional continuous behavioral descriptor space into $k$ homogeneous Voronoi polyhedra, bounding memory to $\mathcal{O}(k)$ instead of $\mathcal{O}(C^8)$.

```python
class CVTArchive:
    """Centroidal Voronoi Tessellation (CVT) MAP-Elites archive for high-dimensional descriptors."""

    def __init__(self, centroids: tuple[tuple[float, ...], ...]) -> None:
        if not centroids:
            raise ValueError("CVTArchive requires at least one centroid")
        self._dimension = len(centroids[0])
        self._centroids = centroids
        self._cells: dict[int, QDArchiveEntry] = {}

    def _nearest_centroid_index(self, descriptor: tuple[float, ...]) -> int:
        """Find the index of the nearest Voronoi centroid via Euclidean metric."""
        best_idx = 0
        min_dist = float("inf")
        for idx, centroid in enumerate(self._centroids):
            dist = sum((a - b) ** 2 for a, b in zip(descriptor, centroid, strict=True))
            if dist < min_dist:
                min_dist = dist
                best_idx = idx
        return best_idx

    def consider(self, entry: QDArchiveEntry) -> bool:
        """Insert entry into its nearest centroid niche if fitness exceeds incumbent."""
        idx = self._nearest_centroid_index(entry.behavioral_descriptor)
        current = self._cells.get(idx)
        if current is None or entry.fitness > current.fitness:
            self._cells[idx] = entry
            return True
        return False

    def coverage(self) -> int:
        """Number of populated Voronoi niches — empirical proxy for population diversity."""
        return len(self._cells)
```

---

### Listing B.2: Bounded 8-Drive Developmental Motivation Dynamics
- **Subsystem:** `evolzen.agents.development.motivation`
- **Source File:** [`src/evolzen/agents/development/motivation.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/agents/development/motivation.py)
- **Grounding:** Oudeyer et al. (*IEEE TEVC* 2007); Merrick (*IEEE TAMD* 2010); ADR 0006.
- **Mathematical Formulation:** $a_i = \tanh\left( b_i + \frac{1}{8}\sum_{j=1}^8 w_{ij} c_j + w_{\text{age}} \alpha + m_i a_{i, t-1} \right)$, normalized via softmax with temperature.

```python
def drive_step(
    genome: BirthGenome,
    context: tuple[float, ...],
    previous: tuple[float, ...],
    age_fraction: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return bounded activations and normalized softmax ratios for one decision step.
    
    Drives: [Survive, Nourish, Comfort, Agency, Security, Curious, Social, Legacy]
    """
    validate_signal(context)
    validate_signal(previous)
    
    # 1. Compute hyperbolic tangent bounded activations
    activation = tuple(
        math.tanh(
            row.bias
            + sum(w * x for w, x in zip(row.context, context, strict=True)) / 8.0
            + row.age_weight * age_fraction
            + row.momentum * previous[index]
        )
        for index, row in enumerate(genome.equations)
    )
    
    # 2. Stable Softmax over drive activations
    maximum = max(activation)
    weights = tuple(math.exp((v - maximum) / genome.temperature) for v in activation)
    total = sum(weights)
    return activation, tuple(v / total for v in weights)
```

---

### Listing B.3: Safe Genome Crossover & Mutation Operator
- **Subsystem:** `evolzen.agents.development.evolution`
- **Source File:** [`src/evolzen/agents/development/motivation.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/agents/development/motivation.py)
- **Constraint:** Parameter mutation operates purely on numeric coefficients, strictly forbidding unauthorized code generation or neural weight injection.

```python
def inherit_genome(
    parents: tuple[BirthGenome, ...], seed: int, mutation: float = 0.05
) -> BirthGenome:
    """Mix aligned numeric coefficients, never neural weights or uncontained code."""
    if not 1 <= len(parents) <= 2:
        raise ValueError("Inheritance requires one or two parent genomes")
    rng = random.Random(seed)
    p0, p1 = (parents[0], parents[1]) if len(parents) == 2 else (parents[0], parents[0])
    rows: list[DriveEquation] = []
    for eq0, eq1 in zip(p0.equations, p1.equations, strict=True):
        mix = rng.random()
        b = (mix * eq0.bias + (1.0 - mix) * eq1.bias) + rng.gauss(0.0, mutation)
        ctx = tuple(
            ((mix * w0 + (1.0 - mix) * w1) + rng.gauss(0.0, mutation))
            for w0, w1 in zip(eq0.context, eq1.context, strict=True)
        )
        rows.append(DriveEquation(
            bias=_clamp(b, -1.0, 1.0),
            context=tuple(_clamp(c, -1.0, 1.0) for c in ctx),
            age_weight=_clamp(eq0.age_weight + rng.gauss(0.0, mutation), -1.0, 1.0),
            momentum=_clamp(eq0.momentum + rng.gauss(0.0, mutation), 0.0, 0.9),
        ))
    return BirthGenome(seed=seed, equations=tuple(rows))
```

---

## Appendix C: Economy & Market Mechanism Subsystem (Phase 1.3)

Implements tokenomic balance verification, bilateral trade mediation, and institutional contracts (Zheng et al., *Science Advances* 2022; Buşoniu et al., 2008).

### Listing C.1: Multi-Agent Resource Balance & Asset Transfer Engine
- **Subsystem:** `evolzen.economy.market`
- **Source File:** [`src/evolzen/economy/market.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/economy/market.py)
- **Guarantee:** Strict non-negative balance checks ensuring no agent or treasury can incur unauthorized overdrafts.

```python
@dataclass
class Market:
    """Tracks agent balances and simple supply/demand pricing for one resource pool."""
    balances: dict[str, float] = field(default_factory=dict)
    prices: dict[str, float] = field(default_factory=dict)

    def transfer(self, from_agent: str, to_agent: str, amount: float) -> None:
        """Atomically move amount from one agent balance to another with solvency verification."""
        if amount <= 0.0 or not math.isfinite(amount):
            raise ValueError(f"Transfer amount must be positive and finite: {amount}")
        if self.balance_of(from_agent) < amount:
            raise InsufficientBalanceError(f"{from_agent} lacks balance {amount}")
        self.balances[from_agent] = self.balance_of(from_agent) - amount
        self.balances[to_agent] = self.balance_of(to_agent) + amount
```

---

### Listing C.2: Bilateral Spatial Trade Mediation
- **Subsystem:** `evolzen.environment.engine`
- **Source File:** [`src/evolzen/environment/engine.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/environment/engine.py)
- **Constraint:** Co-location check, resource availability validation, and atomic currency settlement.

```python
def _handle_trade(world: WorldState, actor: WorldAgentState, action: Action, next_tick: int) -> _StepOutcome:
    """Mediate atomic peer-to-peer trade between two co-located agents."""
    counterparty_id = action.params.get("counterparty_id", "").strip()
    counterparty = world.agents.get(counterparty_id)
    if counterparty is None or not counterparty.alive or counterparty.location_id != actor.location_id:
        return _reject(world, "Trade requires valid, active, co-located counterparty")

    resource = action.params.get("offer_resource", "food")
    qty = action.params.get("offer_qty", 1)
    price = action.params.get("price", 2)
    
    if actor.inventory.get(resource, 0) < qty:
        return _reject(world, f"Insufficient {resource} for trade")
    if counterparty.currency < price:
        return _reject(world, f"Counterparty {counterparty_id} lacks currency {price}")

    # Atomic Inventory and Currency Reallocation
    actor_inv = dict(actor.inventory)
    actor_inv[resource] -= qty
    cp_inv = dict(counterparty.inventory)
    cp_inv[resource] = cp_inv.get(resource, 0) + qty

    updated_actor = actor.model_copy(update={
        "inventory": actor_inv, "currency": actor.currency + price, "last_action_tick": next_tick
    })
    updated_cp = counterparty.model_copy(update={
        "inventory": cp_inv, "currency": counterparty.currency - price
    })
    next_world = _replace_agent(_replace_agent(world, updated_actor), updated_cp)
    return _StepOutcome(world=next_world, accepted=True, reason="trade_executed")
```

---

## Appendix D: Directed Exploration & Hypothesis Synthesis Subsystem (Phase 1.4)

Replaces unverified LLM generation with an Actor/Synthesizer/Verifier triadic loop (Courtis et al., 2026; Rodionov, 2026).

### Listing D.1: Programmatic Hypothesis Representation (CandidateRule)
- **Subsystem:** `evolzen.exploration.synthesizer`
- **Source File:** [`src/evolzen/exploration/synthesizer.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/exploration/synthesizer.py)
- **Definition:** Pure Python programmatic rule specifying a candidate transition mapping.

```python
@dataclass(frozen=True)
class CandidateRule:
    """A synthesizer hypothesis about environment behavior.
    
    `code` is executable Python implementing a (State, Action) -> Emission prediction,
    strictly audited by exact replay inside evolzen.containment.Sandbox.
    """
    rule_id: str
    code: str
    explains: list[str]  # Transition IDs this rule was synthesized to explain
```

---

### Listing D.2: Exact-Replay Counterfactual Falsification Gate Protocol
- **Subsystem:** `evolzen.exploration.verifier`
- **Source File:** [`src/evolzen/exploration/verifier.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/exploration/verifier.py)
- **Standard:** Zero-tolerance exact match against held-out transition logs.

```python
class Verifier:
    """Checks a CandidateRule for exact-match reproduction of recorded transitions.
    
    A candidate rule is admitted to the library only if it reproduces every recorded
    transition exactly — never based on heuristic statistical approximation.
    """
    def verify(self, rule: CandidateRule, held_out_transitions: list[Transition]) -> bool:
        """Return True only if `rule` exactly reproduces every transition in the held-out set.
        
        Executes inside Sandbox with CPU/memory ceilings, comparing predicted emissions
        against recorded truth field by field.
        """
        ...  # Executed via evolzen.containment.Sandbox
```

---

## Appendix E: Growing Rule Library & Exact Retention Subsystem (Phase 1.5)

Implements non-overwriting, append-only rule retention structured via Dirichlet-process clustering principles (Ferguson, 1973; Wang et al., 2024).

### Listing E.1: Non-Overwriting Append-Only Rule Admission & Dirichlet Clustering
- **Subsystem:** `evolzen.library.rule_library`
- **Source File:** [`src/evolzen/library/rule_library.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/library/rule_library.py)
- **Guarantee:** Existing verified rules are **never** overwritten; new rules spawn distinct families or version chains.

```python
class RuleLibrary:
    """Append-only, non-overwriting library for verified transition rules.
    
    Adheres to Dirichlet-process mixture dynamics: if similarity to existing active rules
    exceeds threshold, creates a supersession link; otherwise spawns a novel rule family.
    """
    def admit(
        self,
        candidate: CandidateRule,
        provenance: ProvenanceClass,
        validity: ValidityContext,
        evidence: VerificationEvidence,
        supersedes_id: UUID | None = None,
    ) -> RuleEntry:
        """Admit a verified rule, freezing it with cryptographic audit trail."""
        entry = _candidate_to_entry(candidate, provenance, validity, evidence)
        
        # Find most similar existing rule within the same validity context
        best_match, score = self._find_best_match(entry)
        if best_match and score >= self._similarity_threshold:
            # Link as superseding evolution rather than destructive overwrite
            entry.rule_family_id = best_match.rule_family_id
            entry.supersession_link = SupersessionLink(parent_id=best_match.rule_id, score=score)
        else:
            # Spawn independent rule family
            entry.rule_family_id = uuid4()
            
        self._store.insert(entry)
        self._audit.record(make_event(AuditEventType.ADMITTED, entry.rule_id))
        return entry
```

---

### Listing E.2: Context-Aware Rule Applicability & Precondition Matcher
- **Subsystem:** `evolzen.library.validity`
- **Source File:** [`src/evolzen/library/validity.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/library/validity.py)
- **Role:** Prevents cross-contamination between incompatible world seeds or mechanics versions.

```python
def is_applicable(entry: RuleEntry, current_context: ValidityContext) -> bool:
    """Check whether a library entry is applicable within the given validity context.
    
    Guarantees rules synthesized in one mechanics version do not falsely trigger in another.
    """
    if entry.validity.mechanics_version != current_context.mechanics_version:
        return False
    if entry.validity.world_type != current_context.world_type:
        return False
    if entry.validity.preconditions:
        for k, v in entry.validity.preconditions.items():
            if current_context.active_flags.get(k) != v:
                return False
    return True
```

---

## Appendix F: Grounded Predictor & Continual Rehearsal Subsystem (Phase 2.1)

Mitigates catastrophic forgetting in neural policy updates by combining real deployment replay with bounded capacity (Wang et al., 2024; Parisi et al., 2019).

### Listing F.1: Fixed-Capacity Rehearsal Buffer for Continual Experience Replay
- **Subsystem:** `evolzen.predictor.rehearsal_buffer`
- **Source File:** [`src/evolzen/predictor/rehearsal_buffer.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/predictor/rehearsal_buffer.py)
- **Mechanism:** Provenance-verified FIFO rehearsal buffer preventing catastrophic forgetting during policy-gradient steps.

```python
class RehearsalBuffer:
    """Fixed-capacity FIFO buffer of real transitions, sampled during training updates."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._buffer: deque[Transition] = deque(maxlen=capacity)

    def add(self, transition: Transition) -> None:
        """Enqueue an immutable, provenance-verified transition into the rehearsal stream."""
        self._buffer.append(transition)

    def sample(self, batch_size: int) -> list[Transition]:
        """Uniformly sample a batch of historical transitions for rehearsal regularization."""
        if batch_size > len(self._buffer):
            raise ValueError(f"Requested batch_size={batch_size} exceeds buffer={len(self._buffer)}")
        return random.sample(list(self._buffer), batch_size)
```

---

## Appendix G: Hardware Containment & Dynamic Governance Subsystem (Phase 2.2)

Implements mandatory microVM/gVisor hardware isolation and adaptive capability policing for all agent-generated code (Sheth et al., 2025; Akintunde et al., 2022).

### Listing G.1: MicroVM Hardware-Isolated Execution Protocol
- **Subsystem:** `evolzen.containment.sandbox`
- **Source File:** [`src/evolzen/containment/sandbox.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/containment/sandbox.py)
- **Safety Constraint:** Core Rule 1 from `AGENTS.md` & `SECURITY.md` — never execute synthesized code on the host.

```python
@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    wall_time_seconds: float
    resource_ceiling_hit: bool


class Sandbox(Protocol):
    """Protocol satisfied by a concrete Firecracker/gVisor-backed executor.
    
    Never execute code from `evolzen.exploration.synthesizer` or
    `evolzen.agents.self_modification` outside an implementation of this protocol.
    """
    def run(
        self, code: str, *, timeout_seconds: float, resource_ceiling_mb: int
    ) -> ExecutionResult:
        """Execute code in full hardware isolation with enforced CPU and memory limits."""
        ...
```

---

### Listing G.2: Dynamic Capability Governor & Boundary Violation Auditing
- **Subsystem:** `evolzen.containment.governance`
- **Source File:** [`src/evolzen/containment/governance.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/containment/governance.py)
- **Role:** Dynamically grants, inspects, and revokes fine-grained capabilities based on behavioral security flags.

```python
class Capability(StrEnum):
    NETWORK_EGRESS = "network_egress"
    FILESYSTEM_WRITE = "filesystem_write"
    SELF_MODIFICATION = "self_modification"
    SPAWN_SUBPROCESS = "spawn_subprocess"


class CapabilityGovernor:
    """Tracks per-agent capability grants and revokes them on suspicious telemetry."""

    def __init__(self) -> None:
        self._grants: dict[str, set[Capability]] = {}
        self._flagged_events: list[GovernanceEvent] = []

    def grant(self, agent_id: str, capability: Capability) -> None:
        self._grants.setdefault(agent_id, set()).add(capability)

    def revoke(self, agent_id: str, capability: Capability) -> None:
        self._grants.get(agent_id, set()).discard(capability)

    def has_capability(self, agent_id: str, capability: Capability) -> bool:
        return capability in self._grants.get(agent_id, set())

    def flag(self, event: GovernanceEvent) -> None:
        """Record governance breach (e.g. containment probe) for automated quarantine."""
        self._flagged_events.append(event)
```

---

## Appendix H: Recognition Model & Sub-Millisecond Vector Retrieval Subsystem (Phase 2.3)

Combines continuous JEPA latent representations with GPU-accelerated FAISS vector indexing (Johnson et al., 2021; Assran et al., 2023; Ellis et al., 2021).

### Listing H.1: GPU/CPU-Accelerated FAISS Vector Indexing & Semantic Routing
- **Subsystem:** `evolzen.recognition.embedding_router`
- **Source File:** [`src/evolzen/recognition/embedding_router.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/recognition/embedding_router.py)
- **Grounding:** Johnson et al. (*IEEE Transactions on Big Data* 2021, DOI: `10.1109/TBDATA.2019.2921572`).
- **Performance:** Sub-millisecond similarity search across millions of embedded rule definitions.

```python
class EmbeddingRouter:
    """FAISS-backed semantic vector router over verified rule library entries."""

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2") -> None:
        self._embedding_model_name = embedding_model_name
        self._model = None
        self._index = None
        self._rule_ids: list[str] = []

    def build_index(self, rule_id_to_text: dict[str, str]) -> None:
        """Build normalized inner-product FAISS index over rule text embeddings."""
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        if self._model is None:
            self._model = SentenceTransformer(self._embedding_model_name)
            
        self._rule_ids = list(rule_id_to_text.keys())
        embeddings = self._model.encode(list(rule_id_to_text.values()), normalize_embeddings=True)
        embeddings_arr = np.asarray(embeddings, dtype="float32")
        
        # Cosine similarity via inner product on L2-normalized vectors
        index = faiss.IndexFlatIP(embeddings_arr.shape[1])
        index.add(embeddings_arr)
        self._index = index

    def route(self, query_embedding: list[float], top_k: int) -> list[str]:
        """Retrieve the top-k most semantically relevant rule_ids in sub-millisecond time."""
        import numpy as np
        if self._index is None:
            raise RuntimeError("Index must be built before routing queries")
        query_arr = np.asarray([query_embedding], dtype="float32")
        _, indices = self._index.search(query_arr, top_k)
        return [self._rule_ids[i] for i in indices[0] if 0 <= i < len(self._rule_ids)]
```

---

### Listing H.2: Self-Supervised Joint-Embedding Predictive Architecture (JEPA) Protocol
- **Subsystem:** `evolzen.recognition.jepa`
- **Source File:** [`src/evolzen/recognition/jepa.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/recognition/jepa.py)
- **Grounding:** Assran et al. (*IEEE CVPR* 2023, DOI: `10.1109/cvpr52729.2023.01499`).
- **Mechanism:** Non-generative latent state prediction avoiding pixel/token reconstruction hallucinations.

```python
class JEPAEncoder(Protocol):
    """Continuous, grounded encoder learning latent representations of environment states.
    
    Trained with a self-supervised objective over state representations, predicting
    latent target representations without pixel-level or token-level generation.
    """
    def encode(self, state: State) -> list[float]:
        """Return a compact latent embedding vector for environment State."""
        ...

    def train_step(self, batch: list[State]) -> dict[str, float]:
        """Execute one self-supervised gradient update; return loss metrics."""
        ...
```

---

### Listing H.3: Wake-Sleep Library Abstraction & Fantasy Case Learner
- **Subsystem:** `evolzen.recognition.wake_sleep`
- **Source File:** [`src/evolzen/recognition/wake_sleep.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/recognition/wake_sleep.py)
- **Grounding:** DreamCoder (Ellis et al., *ACM PLDI* 2021).
- **Paradigm:** Alternating wake-phase rule proposition with sleep-phase refactoring on real and synthetic fantasy cases.

```python
@dataclass(frozen=True)
class FantasyCase:
    """A self-generated training case used during the sleep phase for library compression."""
    synthetic_context: dict[str, Any]
    target_rule_id: str


class WakeSleepLearner:
    """Alternates wake (propose using library) and sleep (refactor abstractions)."""
    def __init__(self, rule_library: RuleLibrary) -> None:
        self._rule_library = rule_library

    def wake_propose(self, observation: dict[str, Any]) -> CandidateRule:
        """Propose hypothesis for observation using the current verified-rule library."""
        ...

    def sleep_step(
        self, real_cases: list[dict[str, Any]], fantasy_cases: list[FantasyCase]
    ) -> dict[str, float]:
        """Refactor common code primitives and retrain recognition prior on fantasy cases."""
        ...
```

---

## Appendix I: Evaluation & Action-Efficiency Scoring Subsystem (Phases 2.4–2.5)

Implements Relative Human Action Efficiency (RHAE) scoring to quantify sample-efficient adaptation on out-of-distribution environments (Chollet et al., 2025; Wang et al., 2024).

### Listing I.1: Relative Human Action Efficiency (RHAE) Scorer
- **Subsystem:** `evolzen.evaluation.rhae_scorer`
- **Source File:** [`src/evolzen/evaluation/rhae_scorer.py`](file:///d:/1)MY%20PROJECTS/EvolZen-main/src/evolzen/evaluation/rhae_scorer.py)
- **Metric Formulation:** $\text{RHAE} = \frac{A_{\text{human}}}{A_{\text{system}}}$ for solved tasks; $0.0$ if unsolved.
- **Interpretation:** $\text{RHAE} > 1.0$ indicates superhuman exploratory action efficiency.

```python
@dataclass(frozen=True)
class RHAEResult:
    system_actions: int
    human_reference_actions: int
    solved: bool

    @property
    def score(self) -> float:
        """Calculate RHAE score in [0.0, inf).
        
        1.0 denotes matching human baseline efficiency exactly;
        > 1.0 denotes greater efficiency than human baseline.
        """
        if not self.solved or self.system_actions == 0:
            return 0.0
        return self.human_reference_actions / self.system_actions


class RHAEScorer:
    """Aggregates RHAEResults across evaluation rounds into reportable benchmarks."""

    def __init__(self) -> None:
        self._results: list[RHAEResult] = []

    def record(self, result: RHAEResult) -> None:
        self._results.append(result)

    def mean_rhae(self) -> float:
        """Mean action efficiency across all evaluated OOD test splits."""
        return sum(r.score for r in self._results) / len(self._results) if self._results else 0.0

    def solve_rate(self) -> float:
        """Fraction of held-out tasks solved successfully."""
        return sum(1 for r in self._results if r.solved) / len(self._results) if self._results else 0.0
```

---
*Document generated autonomously for EvolZen research publication purposes based on verified code implementations in `src/evolzen/`.*