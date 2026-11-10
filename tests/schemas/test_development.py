import math

import pytest
from pydantic import ValidationError

from evolzen.agents.development import born
from evolzen.schemas.development import (
    ZERO,
    BrainSnapshot,
    Candidate,
    DevelopmentConfig,
    DriveEquation,
)


def test_records_are_frozen_and_reject_unknown_fields() -> None:
    candidate = Candidate(action_id="rest", context_key="x", skill_key="rest")
    with pytest.raises(ValidationError):
        candidate.cost = 0.5
    data = candidate.model_dump()
    data["arbitrary_code"] = "not executable"
    with pytest.raises(ValidationError):
        Candidate.model_validate(data)


def test_reject_nonfinite_coefficients_and_bad_vector_length() -> None:
    with pytest.raises(ValidationError):
        DriveEquation(bias=math.nan, context=ZERO, age_weight=0, momentum=0)
    with pytest.raises(ValidationError):
        DriveEquation(bias=0, context=(0.0,), age_weight=0, momentum=0)


def test_snapshot_restoration_cannot_exceed_limits_or_reverse_clock() -> None:
    state = born("c", 1, 10)
    data = state.model_dump()
    data["tick"] = 9
    with pytest.raises(ValidationError):
        BrainSnapshot.model_validate(data)
    with pytest.raises(ValidationError):
        DevelopmentConfig(memory_limit=0)
