import pytest

from evolzen.economy.manuals import ManualStore, RealDataFloorViolation


def test_manual_store_get_or_create_is_idempotent() -> None:
    store = ManualStore(real_data_floor=0.2)
    m1 = store.get_or_create("negotiation:round-1")
    m2 = store.get_or_create("negotiation:round-1")
    assert m1 is m2


def test_real_data_floor_violation_raises() -> None:
    store = ManualStore(real_data_floor=0.3)
    with pytest.raises(RealDataFloorViolation):
        store.check_real_data_floor(real_fraction=0.1)


def test_real_data_floor_passes_when_met() -> None:
    store = ManualStore(real_data_floor=0.3)
    store.check_real_data_floor(real_fraction=0.5)  # should not raise
