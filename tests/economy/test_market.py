"""Tests for Phase 1.3 Market, OrderBook, dynamic pricing, and WorldState settlement."""
from __future__ import annotations

import pytest

from evolzen.economy.market import Market, Order, OrderBook, OrderSide, TradeSettlement
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.environment.invariants import check_invariants
from evolzen.schemas.world import ActionType, InstitutionRecord, WorldState


def test_transfer_moves_integer_balance() -> None:
    """Verify integer currency moves accurately between entities."""
    m = Market(balances={"a": 10, "b": 0})
    m.transfer("a", "b", 4)
    assert m.balance_of("a") == 6
    assert m.balance_of("b") == 4


def test_transfer_raises_on_insufficient_balance() -> None:
    """Verify overdraft transfers fail with ValueError."""
    m = Market(balances={"a": 1})
    with pytest.raises(ValueError, match="insufficient balance"):
        m.transfer("a", "b", 5)


def test_transfer_raises_on_negative_amount() -> None:
    """Verify negative transfers are rejected."""
    m = Market(balances={"a": 10, "b": 5})
    with pytest.raises(ValueError, match="non-negative"):
        m.transfer("a", "b", -2)


def test_quote_price_hayekian_scarcity_dynamics() -> None:
    """Verify Hayekian dynamic pricing reflects supply and demand ratios."""
    m = Market(base_prices={"food": 2, "wood": 3})

    # Balanced supply and demand (5 vs 5): price approx base
    p_bal = m.quote_price("food", local_supply=5, local_demand=5)
    assert p_bal == 2

    # High scarcity: demand 20, supply 1 -> price increases
    p_scarce = m.quote_price("food", local_supply=1, local_demand=20)
    assert p_scarce > p_bal
    assert p_scarce == 21  # 2 * 21 / 2 = 21

    # High abundance: supply 50, demand 1 -> price hits minimum floor 1
    p_abund = m.quote_price("food", local_supply=50, local_demand=1)
    assert p_abund == 1


def test_order_book_sorting_and_matching() -> None:
    """Verify OrderBook sorts bids descending, asks ascending, and clears crossing spreads."""
    ob = OrderBook(resource="food", location_id="plaza")

    # Add bids (buyers)
    b1 = Order(agent_id="buyer-1", side=OrderSide.BID, resource="food", quantity=2, limit_price=10)
    b2 = Order(agent_id="buyer-2", side=OrderSide.BID, resource="food", quantity=3, limit_price=12)
    ob.add_bid(b1)
    ob.add_bid(b2)
    # Highest bid first
    assert ob.bids[0].agent_id == "buyer-2"

    # Add asks (sellers)
    a1 = Order(agent_id="seller-1", side=OrderSide.ASK, resource="food", quantity=1, limit_price=8)
    a2 = Order(agent_id="seller-2", side=OrderSide.ASK, resource="food", quantity=4, limit_price=6)
    ob.add_ask(a1)
    ob.add_ask(a2)
    # Lowest ask first
    assert ob.asks[0].agent_id == "seller-2"

    # Clear orders with 10% institutional fee
    settlements = ob.clear_orders(fee_rate=0.1, current_tick=10)
    assert len(settlements) >= 1

    first = settlements[0]
    assert first.buyer_id == "buyer-2"
    assert first.seller_id == "seller-2"
    assert first.quantity == 3
    # Crossing price: (12 + 6) // 2 = 9
    assert first.price_per_unit == 9
    assert first.total_price == 27
    assert first.fee_withheld == 3  # round(27 * 0.1) = 3


def test_order_book_cancellation() -> None:
    """Verify active orders can be cancelled from the order book."""
    ob = OrderBook(resource="wood", location_id="forest")
    ord1 = Order(agent_id="agent-0", side=OrderSide.BID, resource="wood", quantity=5, limit_price=4)
    ob.add_bid(ord1)
    assert len(ob.bids) == 1

    cancelled = ob.cancel_order(ord1.order_id)
    assert cancelled is True
    assert len(ob.bids) == 0

    assert ob.cancel_order("non-existent") is False


def test_market_place_order_and_action_emission() -> None:
    """Verify Market.place_order matches orders and creates typed Actions."""
    m = Market()

    # Place ask
    ask = Order(agent_id="seller-A", side=OrderSide.ASK, resource="stone", quantity=2, limit_price=4)
    trades_empty = m.place_order(ask, location_id="quarry")
    assert len(trades_empty) == 0

    # Place crossing bid
    bid = Order(agent_id="buyer-B", side=OrderSide.BID, resource="stone", quantity=2, limit_price=6)
    trades = m.place_order(bid, location_id="quarry", fee_rate=0.05, current_tick=5)
    assert len(trades) == 1
    t = trades[0]
    assert t.quantity == 2
    assert t.price_per_unit == 5
    assert t.total_price == 10

    # Convert to typed Action
    act = m.create_trade_action(t)
    assert act.action_type == ActionType.TRADE
    assert act.agent_id == "seller-A"
    assert act.params["counterparty_id"] == "buyer-B"
    assert act.params["offer_resource"] == "stone"
    assert act.params["offer_qty"] == 2
    assert act.params["price"] == 10


def test_market_settle_in_world_preserves_conservation() -> None:
    """Verify settle_in_world updates WorldState and maintains exact invariants."""
    engine = SocialSandboxEngine(default_seed=50, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=50, initial_agent_age=300)
    w0 = WorldState.from_state(s0)

    # Establish guild with 20% contribution fee
    guild = InstitutionRecord(
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
    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"institution_ids": ("guild-plaza",)})
    w_start = w0.model_copy(update={"institutions": {"guild-plaza": guild}, "agents": agents})

    # Prepare settlement: agent-0 sells 1 food to agent-1 for 10 currency, fee = 2
    settlement = TradeSettlement(
        buyer_id="agent-1",
        seller_id="agent-0",
        resource="food",
        quantity=1,
        price_per_unit=10,
        total_price=10,
        fee_withheld=2,
        location_id="plaza",
        tick=300,
    )

    m = Market()
    w_settled = m.settle_in_world(settlement, w_start)

    # Buyer paid 10: 20 -> 10
    assert w_settled.agents["agent-1"].currency == 10
    assert w_settled.agents["agent-1"].inventory["food"] == w_start.agents["agent-1"].inventory["food"] + 1

    # Seller received 8 (10 - 2 fee): 20 -> 28
    assert w_settled.agents["agent-0"].currency == 28
    assert w_settled.agents["agent-0"].inventory["food"] == w_start.agents["agent-0"].inventory["food"] - 1

    # Guild received 2 fee
    assert w_settled.institutions["guild-plaza"].currency_reserve == 2

    # Invariants must strictly hold
    report = check_invariants(w_start, w_settled)
    assert report.passed is True
