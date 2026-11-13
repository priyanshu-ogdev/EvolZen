"""Tests for Phase 1.3 ManualStore, provenance floors, and knowledge transfer."""
from __future__ import annotations

import pytest

from evolzen.economy.manuals import ManualStore, RealDataFloorViolation
from evolzen.schemas.manual import (
    ManualEntry,
    ManualEntryStatus,
    ProvenanceCategory,
    ProvenanceRecord,
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
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="https://arxiv.org/abs/2606.02859",
    )
    prov_sim = ProvenanceRecord(
        provenance_id="prov-2",
        category=ProvenanceCategory.SIMULATOR_TRACE,
        uri_or_source="engine:seed-42",
    )
    prov_model = ProvenanceRecord(
        provenance_id="prov-3",
        category=ProvenanceCategory.MODEL_GENERATED,
        uri_or_source="vllm:meta-llama-3",
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


def test_manual_store_add_falsify_revise_entry() -> None:
    """Verify add_entry, falsify_entry, and revise_entry methods directly on ManualStore."""
    store = ManualStore(real_data_floor=0.3)

    # 1. add_entry via keyword arguments
    prov = ProvenanceRecord(
        provenance_id="prov-human-1",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="docs/protocol.md",
    )
    e1 = store.add_entry(
        "hazard:desert",
        text="Drink water at noon",
        written_by="expert",
        provenance=prov,
    )
    assert e1.text == "Drink water at noon"
    assert e1.status == ManualEntryStatus.HYPOTHESIS
    assert e1.is_ground_truth is True

    # 2. add_entry via pre-instantiated ManualEntry
    e2 = ManualEntry(
        text="Never rest during daytime",
        written_by="agent-1",
        category=ProvenanceCategory.MODEL_GENERATED,
    )
    added_e2 = store.add_entry("hazard:desert", e2)
    assert added_e2 is e2
    assert len(store.get_or_create("hazard:desert").entries) == 2

    # 3. falsify_entry by index
    falsified = store.falsify_entry("hazard:desert", 1, evidence_id="heatstroke-event-1")
    assert falsified.status == ManualEntryStatus.FALSIFIED
    assert "heatstroke-event-1" in falsified.evidence_ids

    # 4. revise_entry
    revised = store.revise_entry(
        "hazard:desert",
        1,
        new_text="Rest in shelter between 11:00 and 15:00",
        written_by="medic",
        evidence_id="recovery-event-2",
        provenance=prov,
    )
    assert revised.status == ManualEntryStatus.HYPOTHESIS
    assert revised.revised_from == "Never rest during daytime"
    assert revised.is_ground_truth is True
    assert len(store.get_or_create("hazard:desert").active_beliefs()) == 2


def test_manual_store_check_real_data_floor_none_evaluates_stored() -> None:
    """Verify check_real_data_floor(None) computes real fraction across all stored manuals."""
    store = ManualStore(real_data_floor=0.5)

    # Initially empty store -> real fraction is 1.0 (passes floor)
    store.check_real_data_floor()

    # Add 1 real entry and 1 synthetic entry (real fraction = 0.5 -> passes floor)
    prov = ProvenanceRecord(
        provenance_id="p-1",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="field_notes.txt",
    )
    store.add_entry("s1", text="Safe path", written_by="guide", provenance=prov)
    store.add_entry("s1", text="Quick path", written_by="scout", category=ProvenanceCategory.MODEL_GENERATED)

    store.check_real_data_floor(None)  # 1/2 = 0.5 >= 0.5 passes

    # Add second manual with synthetic entry: now 1 real out of 3 entries (0.333 < 0.5)
    store.add_entry("s2", text="Hallucinated shortcut", written_by="bot", category=ProvenanceCategory.MODEL_GENERATED)

    with pytest.raises(RealDataFloorViolation, match="below the configured floor"):
        store.check_real_data_floor()


def test_manual_store_to_dict_and_from_dict_roundtrip() -> None:
    """Verify serialization and deserialization of ManualStore."""
    store = ManualStore(real_data_floor=0.35)

    prov = ProvenanceRecord(
        provenance_id="prov-exp-1",
        category=ProvenanceCategory.SIMULATOR_TRACE,
        uri_or_source="sim:run-99",
    )
    store.add_entry("crafting", text="Smelt ore into ingots", written_by="metallurgist", provenance=prov)
    store.add_entry("farming", text="Harvest wheat when golden", written_by="farmer")

    data = store.to_dict()
    assert data["real_data_floor"] == 0.35
    assert "crafting" in data["manuals"]
    assert "farming" in data["manuals"]

    # Reconstruct from dict
    restored = ManualStore.from_dict(data)
    assert restored.real_data_floor == 0.35
    crafting_m = restored.get("crafting")
    assert crafting_m is not None
    assert len(crafting_m.entries) == 1
    assert crafting_m.entries[0].text == "Smelt ore into ingots"
    assert crafting_m.entries[0].provenance is not None
    assert crafting_m.entries[0].provenance.provenance_id == "prov-exp-1"


def test_manual_store_floor_bounds_and_list() -> None:
    """Verify ManualStore validates floor range and lists manuals."""
    with pytest.raises(ValueError, match="real_data_floor must be in"):
        ManualStore(real_data_floor=-0.1)
    with pytest.raises(ValueError, match="real_data_floor must be in"):
        ManualStore(real_data_floor=1.1)

    store = ManualStore(real_data_floor=0.2)
    assert store.real_data_floor == 0.2
    assert store.get("missing") is None

    store.get_or_create("beta")
    store.get_or_create("alpha")
    ordered = store.list_manuals()
    assert [m.situation_key for m in ordered] == ["alpha", "beta"]


def test_knowledge_transfer_and_backward_compat_edge_cases() -> None:
    """Verify edge cases in measure_knowledge_transfer and verify_backward_compatibility."""
    store = ManualStore(real_data_floor=0.2)

    # Empty trials
    with pytest.raises(ValueError, match="must each contain at least one score"):
        store.measure_knowledge_transfer("key", novice_eval=[], baseline_eval=[1.0])

    # Zero baseline score
    zero_base = store.measure_knowledge_transfer("key", novice_eval=[10.0], baseline_eval=[0.0])
    assert zero_base.relative_gain == 10.0

    # Negative baseline score
    neg_base = store.measure_knowledge_transfer("key", novice_eval=[0.0], baseline_eval=[0.0])
    assert neg_base.relative_gain == 0.0

    # Backward compatibility: empty lists
    assert store.verify_backward_compatibility([], []) is True

    # Backward compatibility: prior <= 0
    assert store.verify_backward_compatibility([0.0], [5.0]) is True
    assert store.verify_backward_compatibility([0.0], [-1.0]) is False


def test_manual_store_empty_manuals_real_fraction() -> None:
    """Verify check_real_data_floor and calculate_real_fraction handle empty manuals in store."""
    store = ManualStore(real_data_floor=0.4)
    # Manuals exist but have 0 entries
    store.get_or_create("empty-manual-1")
    store.get_or_create("empty-manual-2")

    # Should compute actual_fraction = 1.0 (empty) and pass
    store.check_real_data_floor()
    # calculate_real_fraction(None) over empty manuals returns 1.0
    assert store.calculate_real_fraction(None) == 1.0


def test_manual_store_calculate_real_fraction_none_evaluates_all_entries() -> None:
    """Verify calculate_real_fraction(None) aggregates across multiple non-empty manuals."""
    store = ManualStore(real_data_floor=0.3)

    prov = ProvenanceRecord(
        provenance_id="p-sim-1",
        category=ProvenanceCategory.SIMULATOR_TRACE,
        uri_or_source="sim:env",
    )
    store.add_entry("man1", text="Entry 1", written_by="agent", provenance=prov)
    store.add_entry("man2", text="Entry 2", written_by="agent", category=ProvenanceCategory.MODEL_GENERATED)

    # 1 real out of 2 total = 0.5
    assert store.calculate_real_fraction(None) == 0.5


def test_manual_store_invalid_index_raises() -> None:
    """Verify falsify_entry and revise_entry raise IndexError on invalid index."""
    store = ManualStore(real_data_floor=0.2)
    store.add_entry("topic", text="Fact", written_by="user")

    with pytest.raises(IndexError):
        store.falsify_entry("topic", index=99)

    with pytest.raises(IndexError):
        store.revise_entry("topic", index=-5, new_text="New", written_by="user")


