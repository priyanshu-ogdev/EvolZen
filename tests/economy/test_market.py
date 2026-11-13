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


def test_market_sync_from_world() -> None:
    """Verify sync_from_world synchronizes agent currency and institution reserves into balances."""
    engine = SocialSandboxEngine(default_seed=42, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=42)
    w0 = WorldState.from_state(s0)

    agents = dict(w0.agents)
    agents["agent-0"] = agents["agent-0"].model_copy(update={"currency": 45})
    agents["agent-1"] = agents["agent-1"].model_copy(update={"currency": 15})

    guild = InstitutionRecord(
        institution_id="guild-central",
        name="Central Guild",
        founder_id="agent-0",
        location_id="plaza",
        member_ids=("agent-0",),
        treasury={},
        currency_reserve=30,
        contribution_rate=0.1,
        created_tick=0,
    )
    w_updated = w0.model_copy(update={"agents": agents, "institutions": {"guild-central": guild}})

    m = Market()
    m.sync_from_world(w_updated)

    assert m.balance_of("agent-0") == 45
    assert m.balance_of("agent-1") == 15
    assert m.balance_of("guild-central") == 30
    assert m.balance_of("unknown-entity") == 0


def test_market_set_balance() -> None:
    """Verify set_balance updates balances and rejects negative values."""
    m = Market()
    m.set_balance("agent-A", 100)
    assert m.balance_of("agent-A") == 100

    # Float int-equivalent
    m.set_balance("agent-B", 50.0)
    assert m.balance_of("agent-B") == 50

    with pytest.raises(ValueError, match="cannot be negative"):
        m.set_balance("agent-A", -10)


def test_market_transfer_float_backward_compatibility() -> None:
    """Verify transfer accepts int-equivalent floats and rejects fractional floats."""
    m = Market(balances={"agent-1": 20, "agent-2": 5})

    # Float int-equivalent
    m.transfer("agent-1", "agent-2", 10.0)
    assert m.balance_of("agent-1") == 10
    assert m.balance_of("agent-2") == 15

    # Non-integer float
    with pytest.raises(ValueError, match="integer-equivalent"):
        m.transfer("agent-1", "agent-2", 4.5)


def test_create_trade_action_explicit_params() -> None:
    """Verify create_trade_action constructs typed Action from discrete parameters."""
    m = Market()
    act = m.create_trade_action(
        seller_id="seller-1",
        buyer_id="buyer-2",
        offer_resource="food",
        offer_qty=5,
        price=15,
    )
    assert act.action_type == ActionType.TRADE
    assert act.agent_id == "seller-1"
    assert act.params["counterparty_id"] == "buyer-2"
    assert act.params["offer_resource"] == "food"
    assert act.params["offer_qty"] == 5
    assert act.params["price"] == 15


def test_record_transaction_ema_prices() -> None:
    """Verify record_transaction updates exponential moving average prices."""
    m = Market()
    assert "food" not in m.prices

    # First transaction initializes price
    m.record_transaction("food", price=10.0, alpha=0.2)
    assert m.prices["food"] == 10.0

    # Second transaction updates with EMA: 0.8 * 10.0 + 0.2 * 20.0 = 12.0
    m.record_transaction("food", price=20.0, alpha=0.2)
    assert pytest.approx(m.prices["food"], rel=1e-5) == 12.0

    # Custom alpha = 0.5: 0.5 * 12.0 + 0.5 * 16.0 = 14.0
    m.record_transaction("food", price=16.0, alpha=0.5)
    assert pytest.approx(m.prices["food"], rel=1e-5) == 14.0

    # Invalid alpha
    with pytest.raises(ValueError, match="alpha must be in"):
        m.record_transaction("food", price=10.0, alpha=0.0)
    with pytest.raises(ValueError, match="alpha must be in"):
        m.record_transaction("food", price=10.0, alpha=1.5)


def test_order_book_side_validation_and_ask_cancel() -> None:
    """Verify OrderBook validates order side and cancels asks."""
    ob = OrderBook(resource="food", location_id="plaza")

    ask = Order(agent_id="s1", side=OrderSide.ASK, resource="food", quantity=2, limit_price=5)
    bid = Order(agent_id="b1", side=OrderSide.BID, resource="food", quantity=2, limit_price=5)

    with pytest.raises(ValueError, match="Cannot add ask order to bids"):
        ob.add_bid(ask)

    with pytest.raises(ValueError, match="Cannot add bid order to asks"):
        ob.add_ask(bid)

    ob.add_ask(ask)
    assert len(ob.asks) == 1
    assert ob.cancel_order(ask.order_id) is True
    assert len(ob.asks) == 0


def test_market_transfer_type_error() -> None:
    """Verify transfer raises TypeError on invalid types."""
    m = Market(balances={"a": 10})
    with pytest.raises(TypeError, match="Transfer amount must be int or float"):
        m.transfer("a", "b", "not-a-number")  # type: ignore[arg-type]


def test_create_trade_action_missing_params() -> None:
    """Verify create_trade_action raises ValueError when params are incomplete."""
    m = Market()
    with pytest.raises(ValueError, match="When not passing a TradeSettlement"):
        m.create_trade_action(seller_id="seller-1")  # type: ignore[call-overload]


def test_settle_in_world_error_branches() -> None:
    """Verify settle_in_world raises on invalid agents, insufficient currency, or insufficient inventory."""
    engine = SocialSandboxEngine(default_seed=10, num_agents=2, num_locations=1)
    s0 = engine.reset(seed=10)
    w0 = WorldState.from_state(s0)

    m = Market()

    # Invalid agent
    bad_settlement = TradeSettlement(
        buyer_id="unknown-buyer",
        seller_id="agent-0",
        resource="food",
        quantity=1,
        price_per_unit=5,
        total_price=5,
        fee_withheld=0,
        location_id="loc-0",
    )
    with pytest.raises(KeyError, match="Settlement references invalid agents"):
        m.settle_in_world(bad_settlement, w0)

    # Insufficient buyer currency
    broke_buyer_settlement = TradeSettlement(
        buyer_id="agent-1",
        seller_id="agent-0",
        resource="food",
        quantity=1,
        price_per_unit=1000,
        total_price=1000,
        fee_withheld=0,
        location_id="loc-0",
    )
    with pytest.raises(ValueError, match="insufficient currency"):
        m.settle_in_world(broke_buyer_settlement, w0)

    # Insufficient seller inventory
    empty_seller_settlement = TradeSettlement(
        buyer_id="agent-1",
        seller_id="agent-0",
        resource="exotic_gem",
        quantity=10,
        price_per_unit=1,
        total_price=10,
        fee_withheld=0,
        location_id="loc-0",
    )
    with pytest.raises(ValueError, match="insufficient exotic_gem"):
        m.settle_in_world(empty_seller_settlement, w0)


def test_order_book_spread_open_no_clearing() -> None:
    """Verify OrderBook halts clearing when the highest bid is strictly below lowest ask."""
    ob = OrderBook(resource="food", location_id="plaza")
    ob.add_bid(Order(agent_id="b1", side=OrderSide.BID, resource="food", quantity=5, limit_price=10))
    ob.add_ask(Order(agent_id="s1", side=OrderSide.ASK, resource="food", quantity=5, limit_price=15))

    # Spread is open: bid (10) < ask (15) -> 0 settlements
    settlements = ob.clear_orders(fee_rate=0.0, current_tick=1)
    assert len(settlements) == 0
    assert len(ob.bids) == 1
    assert len(ob.asks) == 1


def test_order_book_partial_fills() -> None:
    """Verify OrderBook partially fills orders when quantities do not match exactly."""
    ob = OrderBook(resource="wood", location_id="forest")
    # Bid wants 10 units @ 20, Ask offers 4 units @ 15
    ob.add_bid(Order(agent_id="buyer", side=OrderSide.BID, resource="wood", quantity=10, limit_price=20))
    ob.add_ask(Order(agent_id="seller", side=OrderSide.ASK, resource="wood", quantity=4, limit_price=15))

    settlements = ob.clear_orders(fee_rate=0.0, current_tick=5)
    assert len(settlements) == 1
    assert settlements[0].quantity == 4
    # Ask should be fully consumed, Bid should have 6 remaining
    assert len(ob.asks) == 0
    assert len(ob.bids) == 1
    assert ob.bids[0].quantity == 6
    assert ob.bids[0].agent_id == "buyer"


