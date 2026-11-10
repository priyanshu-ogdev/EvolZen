import pytest

from evolzen.economy.market import Market


def test_transfer_moves_balance() -> None:
    m = Market(balances={"a": 10.0, "b": 0.0})
    m.transfer("a", "b", 4.0)
    assert m.balance_of("a") == 6.0
    assert m.balance_of("b") == 4.0


def test_transfer_raises_on_insufficient_balance() -> None:
    m = Market(balances={"a": 1.0})
    with pytest.raises(ValueError):
        m.transfer("a", "b", 5.0)
