"""Falsifiable manual store with a mandatory real-data floor (Phase 1.3).

Manuals (`evolzen.schemas.manual.Manual`) are the primary Phase 1.3 knowledge-transfer
mechanism — natural-language, actively revised, requiring no gradient step. This module also
enforces the real-data floor: purely recursive training on prior generations' own output is the
literature's reference setup for demonstrating model collapse (Shumailov et al., Nature 2024).
"""
from __future__ import annotations

from evolzen.schemas.manual import Manual


class RealDataFloorViolation(Exception):
    """Raised when a generation's training corpus falls below the configured real-data floor."""


class ManualStore:
    """Keyed store of Manuals, one per `situation_key`, with a real-data floor check."""

    def __init__(self, real_data_floor: float) -> None:
        if not 0.0 <= real_data_floor <= 1.0:
            raise ValueError("real_data_floor must be in [0, 1]")
        self._real_data_floor = real_data_floor
        self._manuals: dict[str, Manual] = {}

    def get_or_create(self, situation_key: str) -> Manual:
        if situation_key not in self._manuals:
            self._manuals[situation_key] = Manual(situation_key=situation_key)
        return self._manuals[situation_key]

    def check_real_data_floor(self, real_fraction: float) -> None:
        """Raise if a generation's corpus doesn't meet the real-data floor.

        Call this before starting a new generation's training pass — the Phase 1.3 success
        metric requires this check to gate every generation, not just be logged after the
        fact.
        """
        if real_fraction < self._real_data_floor:
            raise RealDataFloorViolation(
                f"real_fraction={real_fraction:.3f} is below the configured floor "
                f"={self._real_data_floor:.3f}; halt this generation (see docs/phases/1.3-economy.md)."
            )
