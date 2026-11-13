"""Specialization and market dynamics (Phase 1.3).

Scoped to Phase 1.1 domain contracts — integer currency, specialization incentives,
Hayekian dynamic scarcity pricing, and order-clearing mechanisms with institutional fee withholding.

Design authority: `docs/phases/1.3-economy.md`.
Citations:
    - Decentralized markets & dynamic pricing: Qi et al. (arXiv:2606.02859, 2026, "Economy of Minds").
    - Multi-agent economic equilibrium & taxation: Zheng et al. (Science Advances, 2022, DOI: 10.1126/sciadv.abk2607).
    - Institutional governance: Ostrom (1990, Governing the Commons).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, overload
from uuid import uuid4

from pydantic import BaseModel, Field

from evolzen.schemas.transition import Action
from evolzen.schemas.world import ActionType, WorldState


class OrderSide(StrEnum):
    """Side of a market limit order."""

    BID = "bid"
    ASK = "ask"


class Order(BaseModel):
    """A limit order to buy or sell resources in a local market."""

    order_id: str = Field(default_factory=lambda: f"ord-{uuid4().hex[:8]}")
    agent_id: str
    side: OrderSide
    resource: str
    quantity: int = Field(ge=1)
    limit_price: int = Field(ge=1, description="Max willing to pay for bid; min willing to accept for ask.")
    created_tick: int = 0


class TradeSettlement(BaseModel):
    """Result of clearing two matched orders in an order book."""

    trade_id: str = Field(default_factory=lambda: f"trade-{uuid4().hex[:8]}")
    buyer_id: str
    seller_id: str
    resource: str
    quantity: int = Field(ge=1)
    price_per_unit: int = Field(ge=1)
    total_price: int = Field(ge=1)
    fee_withheld: int = Field(ge=0)
    location_id: str
    tick: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderBook:
    """Continuous double auction order book for one resource at one location."""

    def __init__(self, resource: str, location_id: str) -> None:
        self.resource = resource
        self.location_id = location_id
        self._bids: list[Order] = []  # Sorted descending by price
        self._asks: list[Order] = []  # Sorted ascending by price

    @property
    def bids(self) -> tuple[Order, ...]:
        return tuple(self._bids)

    @property
    def asks(self) -> tuple[Order, ...]:
        return tuple(self._asks)

    def add_bid(self, order: Order) -> None:
        """Add a buy order sorted descending by limit price."""
        if order.side != OrderSide.BID:
            raise ValueError(f"Cannot add {order.side} order to bids")
        self._bids.append(order)
        self._bids.sort(key=lambda o: (-o.limit_price, o.created_tick))

    def add_ask(self, order: Order) -> None:
        """Add a sell order sorted ascending by limit price."""
        if order.side != OrderSide.ASK:
            raise ValueError(f"Cannot add {order.side} order to asks")
        self._asks.append(order)
        self._asks.sort(key=lambda o: (o.limit_price, o.created_tick))

    def cancel_order(self, order_id: str) -> bool:
        """Cancel and remove an active order by ID."""
        for i, b in enumerate(self._bids):
            if b.order_id == order_id:
                self._bids.pop(i)
                return True
        for i, a in enumerate(self._asks):
            if a.order_id == order_id:
                self._asks.pop(i)
                return True
        return False

    def clear_orders(
        self,
        fee_rate: float = 0.0,
        current_tick: int = 0,
    ) -> list[TradeSettlement]:
        """Match crossing bids and asks (bid price >= ask price) using midpoint clearing price.

        Args:
            fee_rate: Proportion of total price withheld for the local institution reserve.
            current_tick: Current world tick for settlement provenance.

        Returns:
            List of executed :class:`TradeSettlement` records.
        """
        settlements: list[TradeSettlement] = []

        while self._bids and self._asks:
            best_bid = self._bids[0]
            best_ask = self._asks[0]

            if best_bid.limit_price < best_ask.limit_price:
                break  # Spread is open; no further matches possible

            matched_qty = min(best_bid.quantity, best_ask.quantity)
            clearing_price = (best_bid.limit_price + best_ask.limit_price) // 2
            total_price = matched_qty * clearing_price
            fee = int(round(total_price * fee_rate))

            settlement = TradeSettlement(
                buyer_id=best_bid.agent_id,
                seller_id=best_ask.agent_id,
                resource=self.resource,
                quantity=matched_qty,
                price_per_unit=clearing_price,
                total_price=total_price,
                fee_withheld=fee,
                location_id=self.location_id,
                tick=current_tick,
            )
            settlements.append(settlement)

            # Update or pop orders
            if best_bid.quantity == matched_qty:
                self._bids.pop(0)
            else:
                self._bids[0] = best_bid.model_copy(update={"quantity": best_bid.quantity - matched_qty})

            if best_ask.quantity == matched_qty:
                self._asks.pop(0)
            else:
                self._asks[0] = best_ask.model_copy(update={"quantity": best_ask.quantity - matched_qty})

        return settlements


@dataclass
class Market:
    """Manages currency balances, dynamic pricing, and decentralized order clearing.

    Aligned with Phase 1.1 `NonNegInt` integer currency and `ActionType.TRADE` contracts.
    """

    balances: dict[str, int] = field(default_factory=dict)
    base_prices: dict[str, int] = field(default_factory=lambda: {"food": 2, "wood": 2, "stone": 3})
    prices: dict[str, float] = field(default_factory=dict)
    order_books: dict[str, OrderBook] = field(default_factory=dict)

    def balance_of(self, agent_id: str) -> int:
        """Return non-negative currency balance for `agent_id`."""
        return self.balances.get(agent_id, 0)

    def set_balance(self, agent_id: str, amount: int | float) -> None:
        """Set integer currency balance for `agent_id`."""
        int_amount = int(amount)
        if int_amount < 0:
            raise ValueError(f"Balance for {agent_id} cannot be negative: {amount}")
        self.balances[agent_id] = int_amount

    def sync_from_world(self, world: WorldState) -> None:
        """Sync market balances from world agent currency and institution reserves.

        Args:
            world: Authoritative WorldState containing agents and institutions.
        """
        for agent_id, agent in world.agents.items():
            self.balances[agent_id] = agent.currency
        for inst_id, inst in world.institutions.items():
            self.balances[inst_id] = inst.currency_reserve

    def transfer(self, from_agent: str, to_agent: str, amount: int | float) -> None:
        """Move integer `amount` from one entity's balance to another's.

        Supports int or int-equivalent float values for backward compatibility.

        Args:
            from_agent: Source agent or institution identifier.
            to_agent: Destination agent or institution identifier.
            amount: Non-negative integer or int-equivalent float currency to transfer.

        Raises:
            ValueError: If amount is negative, not integer-equivalent, or balance is insufficient.
        """
        if isinstance(amount, float):
            if not amount.is_integer() and amount != int(amount):
                raise ValueError(f"Transfer amount float must be integer-equivalent: {amount}")
            int_amount = int(amount)
        elif isinstance(amount, int):
            int_amount = amount
        else:
            raise TypeError(f"Transfer amount must be int or float: {type(amount)}")

        if int_amount < 0:
            raise ValueError(f"Transfer amount must be non-negative: {int_amount}")
        if self.balance_of(from_agent) < int_amount:
            raise ValueError(
                f"{from_agent} cannot transfer {int_amount}: insufficient balance "
                f"({self.balance_of(from_agent)})"
            )
        self.balances[from_agent] = self.balance_of(from_agent) - int_amount
        self.balances[to_agent] = self.balance_of(to_agent) + int_amount

    def record_transaction(self, resource: str, price: float, alpha: float = 0.2) -> None:
        """Update exponential moving average (EMA) transaction price for `resource`.

        Args:
            resource: Resource identifier (e.g. 'food', 'wood', 'stone').
            price: Transaction unit price.
            alpha: Smoothing factor in (0.0, 1.0]. Defaults to 0.2.
        """
        if not 0.0 < alpha <= 1.0:
            raise ValueError(f"alpha must be in (0, 1], got {alpha}")
        p = float(price)
        if resource not in self.prices:
            self.prices[resource] = p
        else:
            self.prices[resource] = (1.0 - alpha) * self.prices[resource] + alpha * p

    def quote_price(
        self,
        resource: str,
        local_supply: int,
        local_demand: int,
    ) -> int:
        """Compute Hayekian market clearing price based on local supply and demand ratio.

        Citation:
            Qi et al. (arXiv:2606.02859, 2026) — decentralized multi-agent price dynamics.
            Zheng et al. (Science Advances, 2022, DOI: 10.1126/sciadv.abk2607).

        Formula:
            P(r) = max(1, round(P_base * (demand + 1) / (supply + 1)))

        Args:
            resource: Resource identifier (e.g. 'food', 'wood', 'stone').
            local_supply: Units of resource available locally (stock + offers).
            local_demand: Units of resource requested locally (consumption + bids).

        Returns:
            Integer unit price >= 1.
        """
        base = self.base_prices.get(resource, 2)
        safe_supply = max(0, local_supply)
        safe_demand = max(0, local_demand)
        raw_price = base * (safe_demand + 1.0) / (safe_supply + 1.0)
        return max(1, int(round(raw_price)))

    def get_order_book(self, resource: str, location_id: str) -> OrderBook:
        """Get or initialize the local order book for (resource, location_id)."""
        key = f"{location_id}:{resource}"
        if key not in self.order_books:
            self.order_books[key] = OrderBook(resource=resource, location_id=location_id)
        return self.order_books[key]

    def place_order(
        self,
        order: Order,
        location_id: str,
        fee_rate: float = 0.0,
        current_tick: int = 0,
    ) -> list[TradeSettlement]:
        """Submit a limit order to the local order book and attempt immediate execution.

        Args:
            order: The :class:`Order` to submit.
            location_id: Location where trade occurs.
            fee_rate: Local institution transaction fee rate.
            current_tick: World clock tick.

        Returns:
            List of generated :class:`TradeSettlement` records (empty if order rested).
        """
        ob = self.get_order_book(order.resource, location_id)
        if order.side == OrderSide.BID:
            ob.add_bid(order)
        else:
            ob.add_ask(order)
        return ob.clear_orders(fee_rate=fee_rate, current_tick=current_tick)

    @overload
    def create_trade_action(
        self,
        seller_id: TradeSettlement,
        buyer_id: None = None,
        offer_resource: None = None,
        offer_qty: None = None,
        price: None = None,
        settlement: None = None,
    ) -> Action: ...

    @overload
    def create_trade_action(
        self,
        seller_id: str,
        buyer_id: str,
        offer_resource: str,
        offer_qty: int,
        price: int,
        settlement: None = None,
    ) -> Action: ...

    @overload
    def create_trade_action(
        self,
        seller_id: None = None,
        buyer_id: None = None,
        offer_resource: None = None,
        offer_qty: None = None,
        price: None = None,
        *,
        settlement: TradeSettlement,
    ) -> Action: ...

    def create_trade_action(
        self,
        seller_id: str | TradeSettlement | None = None,
        buyer_id: str | None = None,
        offer_resource: str | None = None,
        offer_qty: int | None = None,
        price: int | None = None,
        settlement: TradeSettlement | None = None,
    ) -> Action:
        """Construct a typed :class:`Action` conforming to Phase 1.1 `ActionType.TRADE`.

        Accepts either a :class:`TradeSettlement` (positionally or by keyword) or
        explicit trade parameters (`seller_id`, `buyer_id`, `offer_resource`, `offer_qty`, `price`).
        Enables seamless dispatch through `SocialSandboxEngine.step()`.
        """
        target_settlement = (
            settlement
            if settlement is not None
            else (seller_id if isinstance(seller_id, TradeSettlement) else None)
        )
        if target_settlement is not None:
            return Action(
                agent_id=target_settlement.seller_id,
                action_type=ActionType.TRADE,
                params={
                    "counterparty_id": target_settlement.buyer_id,
                    "offer_resource": target_settlement.resource,
                    "offer_qty": target_settlement.quantity,
                    "price": target_settlement.total_price,
                },
            )

        if seller_id is None or buyer_id is None or offer_resource is None or offer_qty is None or price is None:
            raise ValueError(
                "When not passing a TradeSettlement, seller_id, buyer_id, offer_resource, "
                "offer_qty, and price must all be provided."
            )
        return Action(
            agent_id=str(seller_id),
            action_type=ActionType.TRADE,
            params={
                "counterparty_id": buyer_id,
                "offer_resource": offer_resource,
                "offer_qty": int(offer_qty),
                "price": int(price),
            },
        )

    def settle_in_world(
        self,
        settlement: TradeSettlement,
        world: WorldState,
    ) -> WorldState:
        """Apply an executed trade settlement directly to `WorldState`.

        Debits buyer currency, credits seller (minus fee), transfers resource,
        and allocates withheld fee to the local institution reserve, maintaining
        strict conservation.

        Args:
            settlement: Trade execution details.
            world: Current world state.

        Returns:
            Updated :class:`WorldState`.
        """
        buyer = world.agents.get(settlement.buyer_id)
        seller = world.agents.get(settlement.seller_id)
        if buyer is None or seller is None:
            raise KeyError(f"Settlement references invalid agents: {settlement.buyer_id}, {settlement.seller_id}")

        if buyer.currency < settlement.total_price:
            raise ValueError(f"Buyer {buyer.agent_id} has insufficient currency for settlement")

        seller_inv = dict(seller.inventory)
        if seller_inv.get(settlement.resource, 0) < settlement.quantity:
            raise ValueError(f"Seller {seller.agent_id} has insufficient {settlement.resource}")

        # Update seller
        seller_inv[settlement.resource] = seller_inv[settlement.resource] - settlement.quantity
        seller_received = settlement.total_price - settlement.fee_withheld
        updated_seller = seller.model_copy(
            update={
                "inventory": seller_inv,
                "currency": seller.currency + seller_received,
            }
        )

        # Update buyer
        buyer_inv = dict(buyer.inventory)
        buyer_inv[settlement.resource] = buyer_inv.get(settlement.resource, 0) + settlement.quantity
        updated_buyer = buyer.model_copy(
            update={
                "inventory": buyer_inv,
                "currency": buyer.currency - settlement.total_price,
            }
        )

        agents = dict(world.agents)
        agents[seller.agent_id] = updated_seller
        agents[buyer.agent_id] = updated_buyer

        institutions = dict(world.institutions)
        if settlement.fee_withheld > 0:
            local_inst = next(
                (i for i in institutions.values() if i.location_id == settlement.location_id),
                None,
            )
            if local_inst is not None:
                institutions[local_inst.institution_id] = local_inst.model_copy(
                    update={"currency_reserve": local_inst.currency_reserve + settlement.fee_withheld}
                )

        return world.model_copy(update={"agents": agents, "institutions": institutions})
