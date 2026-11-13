"""Tests for Phase 1.3 ManualStore, provenance floors, and knowledge transfer."""
from __future__ import annotations

import pytest

from evolzen.economy.manuals import ManualStore, RealDataFloorViolation
from evolzen.schemas.manual import (
    ManualEntry,
    ManualEntryStatus,
    ProvenanceRecord,
    ProvenanceSource,
)


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
    store.check_real_data_floor(real_fraction=0.5)


def test_calculate_real_fraction_with_provenance_records() -> None:
    """Verify real data fraction accurately measures non-model-generated provenance."""
    store = ManualStore(real_data_floor=0.4)

    prov_human = ProvenanceRecord(
        provenance_id="prov-1",
        source_type=ProvenanceSource.HUMAN_EXTERNAL,
        origin="https://arxiv.org/abs/2606.02859",
        hash_sha256="abc123hash",
        verified=True,
    )
    prov_sim = ProvenanceRecord(
        provenance_id="prov-2",
        source_type=ProvenanceSource.SIMULATOR_TRACE,
        origin="engine:seed-42",
        hash_sha256="def456hash",
        verified=True,
    )
    prov_model = ProvenanceRecord(
        provenance_id="prov-3",
        source_type=ProvenanceSource.MODEL_GENERATED,
        origin="vllm:meta-llama-3",
        hash_sha256="ghi789hash",
        verified=False,
    )

    e1 = ManualEntry(text="Conserve food during drought", written_by="human", provenance=prov_human)
    e2 = ManualEntry(text="Crafting stone tool costs 1 stone 2 wood", written_by="sim", provenance=prov_sim)
    e3 = ManualEntry(text="Trade offers over 5 are accepted", written_by="bot", provenance=prov_model)
    e4 = ManualEntry(text="Unverified belief", written_by="bot", provenance=None)

    # 2 real out of 4 entries = 0.50
    corpus = [e1, e2, e3, e4]
    real_frac = store.calculate_real_fraction(corpus)
    assert real_frac == 0.50

    # Passes 0.40 floor
    verified = store.verify_generation_corpus(corpus)
    assert verified == 0.50

    # Raises when floor is higher (0.60)
    strict_store = ManualStore(real_data_floor=0.60)
    with pytest.raises(RealDataFloorViolation, match="below the configured floor"):
        strict_store.verify_generation_corpus(corpus)


def test_falsify_revise_confirm_lifecycle() -> None:
    """Verify beliefs transition through hypothesis, falsification, and revision chains."""
    store = ManualStore(real_data_floor=0.2)
    manual = store.get_or_create("trading:plaza")

    e0 = ManualEntry(text="All trades at plaza are tax-free", written_by="agent-0")
    manual.add_entry(e0)
    assert len(manual.active_beliefs()) == 1
    assert manual.get_entry(0).status == ManualEntryStatus.HYPOTHESIS

    # Falsify upon observing 10% guild fee
    falsified = store.falsify("trading:plaza", 0, evidence_id="trans-guild-fee-1")
    assert falsified.status == ManualEntryStatus.FALSIFIED
    assert "trans-guild-fee-1" in falsified.evidence_ids
    assert len(manual.active_beliefs()) == 0

    # Revise belief with correct tax rate
    revised = store.revise(
        "trading:plaza",
        0,
        new_text="Guild withholds 10% fee on plaza trades",
        written_by="agent-0",
        evidence_id="trans-guild-fee-2",
    )
    assert revised.status == ManualEntryStatus.HYPOTHESIS
    assert revised.revised_from == "All trades at plaza are tax-free"
    assert len(manual.active_beliefs()) == 1

    # Confirm revised belief after multiple verified observations
    confirmed = store.confirm("trading:plaza", 1, evidence_id="trans-guild-fee-3")
    assert confirmed.status == ManualEntryStatus.CONFIRMED
    assert len(manual.active_beliefs()) == 1


def test_measure_knowledge_transfer_forward_gain() -> None:
    """Verify forward knowledge transfer calculation computes relative gain and effectiveness."""
    store = ManualStore(real_data_floor=0.25)

    # Novices reading confirmed manuals achieve mean score 85.0
    novice_scores = [80.0, 85.0, 90.0, 85.0]
    # Unguided baselines achieve mean score 50.0
    baseline_scores = [45.0, 50.0, 55.0, 50.0]

    report = store.measure_knowledge_transfer(
        situation_key="crafting:tools",
        novice_eval=novice_scores,
        baseline_eval=baseline_scores,
        min_relative_gain=0.20,
    )

    assert report.situation_key == "crafting:tools"
    assert report.mean_novice_score == 85.0
    assert report.mean_baseline_score == 50.0
    assert report.absolute_gain == 35.0
    assert report.relative_gain == 0.70  # (85 - 50) / 50 = 0.70
    assert report.transfer_effective is True


def test_verify_backward_compatibility() -> None:
    """Verify backward compatibility detects catastrophic interference on historical benchmarks."""
    store = ManualStore(real_data_floor=0.25)

    prior_benchmarks = [100.0, 95.0, 98.0]
    # Minor acceptable variance (drop <= 5%)
    updated_acceptable = [98.0, 95.0, 96.0]
    assert store.verify_backward_compatibility(prior_benchmarks, updated_acceptable, max_degradation=0.05) is True

    # Severe degradation (drop > 5%)
    updated_degraded = [70.0, 75.0, 80.0]
    assert store.verify_backward_compatibility(prior_benchmarks, updated_degraded, max_degradation=0.05) is False
