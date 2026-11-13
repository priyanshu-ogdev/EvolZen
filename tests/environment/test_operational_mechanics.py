"""Stage 3 Operational Mechanics tests: durability, norms, institutional fees, contract lifecycle, bounds."""
from __future__ import annotations

from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants
from evolzen.schemas.transition import Action, ExogenousInput
from evolzen.schemas.world import (
    ActionType,
    ArtifactRecord,
    ContractRecord,
    InstitutionRecord,
    NormRecord,
    WorldState,
)


def test_tool_durability_decay_and_fatigue_mitigation() -> None:
    """Verify tool durability decays upon gathering and improving location while mitigating fatigue."""
    engine = SocialSandboxEngine(default_seed=10, num_agents=2, num_locations=2)
    s0 = engine.reset(seed=10, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # 1. Baseline gather without tool: fatigue increases by 0.05
    act_gather = Action(
        agent_id="agent-0",
        action_type=ActionType.GATHER,
        params={"resource": "food", "amount": 1},
    )
    tr_no_tool = engine.step(s0, act_gather)
    w_no_tool = WorldState.from_state(tr_no_tool.next_state)
    assert round(w_no_tool.agents["agent-0"].fatigue - w0.agents["agent-0"].fatigue, 3) == 0.05

    # 2. Equip agent-0 with a tool artifact having durability 10 and sufficient materials to improve location
    tool = ArtifactRecord(
        artifact_id="art-tool-1",
        kind="tool",
        creator_id="agent-0",
        owner_id="agent-0",
        location_id=w0.agents["agent-0"].location_id,
        created_tick=0,
        durability=10,
    )
    artifacts = dict(w0.artifacts)
    artifacts["art-tool-1"] = tool
    a0 = w0.agents["agent-0"]
    inv = dict(a0.inventory)
    inv["wood"] = inv.get("wood", 0) + 5
    inv["stone"] = inv.get("stone", 0) + 5
    agents = dict(w0.agents)
    agents["agent-0"] = a0.model_copy(update={"inventory": inv})
    init_res = dict(w0.accounting.initial_resources)
    init_res["wood"] = init_res.get("wood", 0) + 5
    init_res["stone"] = init_res.get("stone", 0) + 5
    s_equipped = w0.model_copy(
        update={
            "artifacts": artifacts,
            "agents": agents,
            "accounting": w0.accounting.model_copy(update={"initial_resources": init_res}),
        }
    ).to_state()

    # Gather with tool: fatigue increases by only 0.025 (50% reduction), durability decays to 9
    tr_tool = engine.step(s_equipped, act_gather)
    w_tool = WorldState.from_state(tr_tool.next_state)
    assert round(w_tool.agents["agent-0"].fatigue - w0.agents["agent-0"].fatigue, 3) == 0.025
    assert w_tool.artifacts["art-tool-1"].durability == 9

    # 3. Test improve_location with tool: fatigue increases by 0.04 (not 0.08), durability decays by 2
    act_improve = Action(
        agent_id="agent-0",
        action_type=ActionType.IMPROVE_LOCATION,
        params={"target_resource": "food"},
    )
    tr_improve = engine.step(tr_tool.next_state, act_improve)
    w_improve = WorldState.from_state(tr_improve.next_state)
    assert w_improve.artifacts["art-tool-1"].durability == 7
    # 0.025 from gather + 0.04 from improve = 0.065
    assert round(w_improve.agents["agent-0"].fatigue - w0.agents["agent-0"].fatigue, 3) == 0.065


def test_norm_compliance_and_hypocrisy_social_friction() -> None:
    """Verify conservation norm compliance bonuses, hypocrisy penalties, and community friction."""
    engine = SocialSandboxEngine(default_seed=20, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=20, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # 1. Propose and adopt conservation norm by agent-0
    norm = NormRecord(
        norm_id="norm-conserve-1",
        title="Conserve Common Food",
        proposer_id="agent-0",
        rule_kind="conservation",
        adopters=("agent-0",),
        created_tick=0,
    )
    norms = {"norm-conserve-1": norm}
    w_normed = w0.model_copy(update={"norms": norms})
    # Agent-0 has adopted norm-conserve-1, both start at baseline status 0.5
    a0 = w_normed.agents["agent-0"].model_copy(update={"adopted_norms": ("norm-conserve-1",), "status": 0.5})
    a1 = w_normed.agents["agent-1"].model_copy(update={"status": 0.5})
    agents = dict(w_normed.agents)
    agents["agent-0"] = a0
    agents["agent-1"] = a1
    w_normed = w_normed.model_copy(update={"agents": agents})

    # 2. Sustainable gathering: food capacity is 50, food stock is 30 > 20% cap (30 >= 10)
    loc = w_normed.locations["plaza"]
    loc_res = dict(loc.resources)
    loc_res["food"] = 30
    init_res = dict(w_normed.accounting.initial_resources)
    init_res["food"] = init_res.get("food", 0) + (30 - loc.resources.get("food", 0))
    s_abundant = w_normed.model_copy(
        update={
            "locations": {"plaza": loc.model_copy(update={"resources": loc_res})},
            "accounting": w_normed.accounting.model_copy(update={"initial_resources": init_res}),
        }
    ).to_state()

    act_gather = Action(
        agent_id="agent-0",
        action_type=ActionType.GATHER,
        params={"resource": "food", "amount": 1},
    )
    tr_abundant = engine.step(s_abundant, act_gather)
    w_abundant = WorldState.from_state(tr_abundant.next_state)
    # Sustainable gather under conservation norm grants status bonus (+0.02)
    assert w_abundant.agents["agent-0"].status > a0.status
    assert round(w_abundant.agents["agent-0"].status, 2) == 0.52

    # 3. Depleting the commons: food stock drops below 20% of 50 (< 10)
    loc_res_scarce = dict(loc.resources)
    loc_res_scarce["food"] = 8
    init_res_scarce = dict(w_normed.accounting.initial_resources)
    init_res_scarce["food"] = init_res_scarce.get("food", 0) + (8 - loc.resources.get("food", 0))
    s_scarce = w_normed.model_copy(
        update={
            "locations": {"plaza": loc.model_copy(update={"resources": loc_res_scarce})},
            "accounting": w_normed.accounting.model_copy(update={"initial_resources": init_res_scarce}),
        }
    ).to_state()

    # Agent-0 (adopter) depletes scarce commons -> Hypocrisy penalty (-0.1)
    tr_scarce = engine.step(s_scarce, act_gather)
    w_scarce = WorldState.from_state(tr_scarce.next_state)
    assert w_scarce.agents["agent-0"].status < a0.status
    assert round(w_scarce.agents["agent-0"].status, 2) == 0.40

    # 4. Agent-1 (non-adopter) gathers during scarcity with co-located adopter -> Social friction (-0.05)
    act_gather_a1 = Action(
        agent_id="agent-1",
        action_type=ActionType.GATHER,
        params={"resource": "food", "amount": 1},
    )
    tr_friction = engine.step(s_scarce, act_gather_a1)
    w_friction = WorldState.from_state(tr_friction.next_state)
    assert w_friction.agents["agent-1"].status < a1.status
    assert round(w_friction.agents["agent-1"].status, 2) == 0.45


def test_institutional_trade_fee_withholding_and_currency_conservation() -> None:
    """Verify trade fees are withheld to local institution currency_reserve without breaking conservation."""
    engine = SocialSandboxEngine(default_seed=30, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=30, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # Establish guild with 20% contribution rate (0.2)
    inst = InstitutionRecord(
        institution_id="guild-plaza",
        name="Plaza Guild",
        founder_id="agent-0",
        location_id="plaza",
        member_ids=("agent-0",),
        treasury={},
        currency_reserve=0,
        contribution_rate=0.2,
        created_tick=0,
    )
    institutions = {"guild-plaza": inst}
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"institution_ids": ("guild-plaza",)})
    s_inst = w0.model_copy(update={"institutions": institutions, "agents": agents}).to_state()

    # Trade: agent-0 sells 1 food to agent-1 for price = 10
    # Fee = int(round(10 * 0.2)) = 2
    # Buyer pays 10 (agent-1: 20 -> 10)
    # Seller receives 10 - 2 = 8 (agent-0: 20 -> 28)
    # Guild receives fee = 2 (reserve: 0 -> 2)
    act_trade = Action(
        agent_id="agent-0",
        action_type=ActionType.TRADE,
        params={
            "counterparty_id": "agent-1",
            "offer_resource": "food",
            "offer_qty": 1,
            "price": 10,
        },
    )
    tr_trade = engine.step(s_inst, act_trade)
    assert tr_trade.emission.data["accepted"] is True
    assert "withheld 2 institutional fee" in tr_trade.emission.data["reason"]

    w_trade = WorldState.from_state(tr_trade.next_state)
    assert w_trade.agents["agent-1"].currency == 10
    assert w_trade.agents["agent-0"].currency == 28
    assert w_trade.institutions["guild-plaza"].currency_reserve == 2

    # Verify exact currency conservation holds
    report = check_invariants(w0, w_trade)
    assert report.passed is True


def test_institution_currency_contribution_mechanics() -> None:
    """Verify agents can directly contribute currency to institutional currency reserves."""
    engine = SocialSandboxEngine(default_seed=40, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=40, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    inst = InstitutionRecord(
        institution_id="bank",
        name="Civic Bank",
        founder_id="agent-0",
        location_id="plaza",
        member_ids=("agent-0", "agent-1"),
        treasury={},
        currency_reserve=5,
        contribution_rate=0.0,
        created_tick=0,
    )
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"institution_ids": ("bank",)})
    agents["agent-1"] = agents["agent-1"].model_copy(update={"institution_ids": ("bank",)})
    obs_currency = sum(a.currency for a in agents.values()) + 5
    s_bank = w0.model_copy(
        update={
            "institutions": {"bank": inst},
            "agents": agents,
            "accounting": w0.accounting.model_copy(update={"initial_currency": obs_currency}),
        }
    ).to_state()

    # Agent-0 contributes 6 currency
    act_contrib = Action(
        agent_id="agent-0",
        action_type=ActionType.CONTRIBUTE_INSTITUTION,
        params={"institution_id": "bank", "currency": 6},
    )
    tr = engine.step(s_bank, act_contrib)
    assert tr.emission.data["accepted"] is True
    w_end = WorldState.from_state(tr.next_state)

    assert w_end.agents["agent-0"].currency == 14  # 20 - 6
    assert w_end.institutions["bank"].currency_reserve == 11  # 5 + 6
    report = check_invariants(WorldState.from_state(s_bank), w_end)
    assert report.passed is True


def test_contract_cancellation_and_auto_expiration_sweep() -> None:
    """Verify open contracts can be cancelled by parties or auto-expire when past TTL."""
    engine = SocialSandboxEngine(default_seed=50, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=50, initial_agent_age=300)

    # 1. Propose contract
    act_prop = Action(
        agent_id="agent-0",
        action_type=ActionType.PROPOSE_CONTRACT,
        params={
            "contract_id": "contract-test-1",
            "counterparty_id": "agent-1",
            "offer_resource": "wood",
            "offer_qty": 1,
            "request_resource": "food",
            "request_qty": 1,
        },
    )
    tr_prop = engine.step(s0, act_prop)
    assert tr_prop.emission.data["accepted"] is True
    w_prop = WorldState.from_state(tr_prop.next_state)
    assert w_prop.contracts["contract-test-1"].status == "open"

    # 2. Cancel contract via ActionType.FULFILL_CONTRACT with cancel=True
    act_cancel = Action(
        agent_id="agent-0",
        action_type=ActionType.FULFILL_CONTRACT,
        params={"contract_id": "contract-test-1", "cancel": True},
    )
    tr_cancel = engine.step(tr_prop.next_state, act_cancel)
    assert tr_cancel.emission.data["accepted"] is True
    w_cancel = WorldState.from_state(tr_cancel.next_state)
    assert w_cancel.contracts["contract-test-1"].status == "cancelled"

    # 3. Test auto-expiration sweep: contract created at tick 0, advanced past TTL 100 ticks
    stale_contract = ContractRecord(
        contract_id="contract-stale",
        proposer_id="agent-0",
        counterparty_id="agent-1",
        offer_resource="wood",
        offer_qty=1,
        request_resource="food",
        request_qty=1,
        status="open",
        created_tick=0,
    )
    contracts = dict(w_cancel.contracts)
    contracts["contract-stale"] = stale_contract
    s_stale = w_cancel.model_copy(update={"contracts": contracts, "tick": 150}).to_state()

    # Step engine: auto-expiration sweep should cancel contract-stale
    act_wait = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    tr_swept = engine.step(s_stale, act_wait)
    w_swept = WorldState.from_state(tr_swept.next_state)
    assert w_swept.contracts["contract-stale"].status == "cancelled"


def test_bounded_collection_and_status_invariants_fr2() -> None:
    """Verify FR-2 bounded collections and status invariants reject out-of-bound entities."""
    engine = SocialSandboxEngine(default_seed=60, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=60, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # 1. Artifact collection capacity (512 max)
    artifacts = {
        f"art-{i}": ArtifactRecord(
            artifact_id=f"art-{i}",
            kind="tool",
            creator_id="agent-0",
            owner_id="agent-0",
            location_id="plaza",
            created_tick=0,
        )
        for i in range(512)
    }
    s_full_artifacts = w0.model_copy(update={"artifacts": artifacts}).to_state()
    act_craft = Action(
        agent_id="agent-0",
        action_type=ActionType.CRAFT,
        params={"kind": "tool"},
    )
    tr_art_rejected = engine.step(s_full_artifacts, act_craft)
    assert tr_art_rejected.emission.data["accepted"] is False
    assert "artifact collection capacity reached" in tr_art_rejected.emission.data["reason"]

    # 2. Status out-of-bounds check in _check_bounded_state
    bad_status_agent = w0.agents["agent-0"].model_copy(update={"status": 1.5})
    w_bad_status = w0.model_copy(update={"agents": {"agent-0": bad_status_agent}})
    report = check_invariants(None, w_bad_status)
    assert report.passed is False
    bounded_check = next(c for c in report.checks if c.name == "bounded_state")
    assert any("status" in d for d in bounded_check.details.split("; "))


def test_exogenous_unhandled_event_provenance() -> None:
    """Verify unknown exogenous events are recorded in applied provenance rather than lost."""
    engine = SocialSandboxEngine(default_seed=70, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=70, initial_agent_age=300)

    exog = ExogenousInput(
        tick=0,
        events=({"type": "solar_flare", "severity": 0.9},),
    )
    act_wait = Action(agent_id="agent-0", action_type=ActionType.WAIT)
    tr = engine.step(s0, act_wait, exogenous_input=exog)
    assert tr.emission.data["accepted"] is True
    assert "unhandled:solar_flare" in tr.emission.data["exogenous_applied"]
