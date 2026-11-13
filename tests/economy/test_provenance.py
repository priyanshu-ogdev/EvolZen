"""Tests for Phase 1.3 ProvenanceRecord and ProvenanceCategory schemas."""
from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from evolzen.schemas import (
    Manual,
    ManualEntry,
    ManualEntryStatus,
    ProvenanceCategory,
    ProvenanceRecord,
)
from evolzen.schemas.provenance import GROUND_TRUTH_CATEGORIES


class TestProvenanceCategory:
    """Test enumeration values and string behavior of ProvenanceCategory."""

    def test_category_values(self) -> None:
        assert ProvenanceCategory.HUMAN_AUTHORED.value == "human_authored"
        assert ProvenanceCategory.HUMAN_DEMONSTRATION.value == "human_demonstration"
        assert ProvenanceCategory.SIMULATOR_TRACE.value == "simulator_trace"
        assert ProvenanceCategory.MODEL_GENERATED.value == "model_generated"

    def test_category_is_str_enum(self) -> None:
        assert isinstance(ProvenanceCategory.HUMAN_AUTHORED, str)
        assert ProvenanceCategory("human_authored") == ProvenanceCategory.HUMAN_AUTHORED
        assert ProvenanceCategory("model_generated") == ProvenanceCategory.MODEL_GENERATED


class TestProvenanceRecord:
    """Test ProvenanceRecord instantiation, validation, immutability, and hashing."""

    def test_provenance_record_defaults(self) -> None:
        rec = ProvenanceRecord(
            provenance_id="prov-1",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="https://arxiv.org/abs/2606.02859",
        )
        assert rec.provenance_id == "prov-1"
        assert rec.category == ProvenanceCategory.HUMAN_AUTHORED
        assert rec.uri_or_source == "https://arxiv.org/abs/2606.02859"
        assert rec.description == ""
        assert rec.created_tick == 0
        assert rec.sampling_weight == 1.0
        assert rec.hash_digest == ""

    def test_is_ground_truth(self) -> None:
        human_rec = ProvenanceRecord(
            provenance_id="p-1",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="expert:annotation",
        )
        demo_rec = ProvenanceRecord(
            provenance_id="p-2",
            category=ProvenanceCategory.HUMAN_DEMONSTRATION,
            uri_or_source="demo:run-42",
        )
        sim_rec = ProvenanceRecord(
            provenance_id="p-3",
            category=ProvenanceCategory.SIMULATOR_TRACE,
            uri_or_source="sim:seed-1234",
        )
        model_rec = ProvenanceRecord(
            provenance_id="p-4",
            category=ProvenanceCategory.MODEL_GENERATED,
            uri_or_source="vllm:meta-llama-3",
        )

        assert human_rec.is_ground_truth is True
        assert demo_rec.is_ground_truth is True
        assert sim_rec.is_ground_truth is True
        assert model_rec.is_ground_truth is False

        assert ProvenanceCategory.HUMAN_AUTHORED in GROUND_TRUTH_CATEGORIES
        assert ProvenanceCategory.HUMAN_DEMONSTRATION in GROUND_TRUTH_CATEGORIES
        assert ProvenanceCategory.SIMULATOR_TRACE in GROUND_TRUTH_CATEGORIES
        assert ProvenanceCategory.MODEL_GENERATED not in GROUND_TRUTH_CATEGORIES

    def test_compute_digest_deterministic(self) -> None:
        rec = ProvenanceRecord(
            provenance_id="p-det",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="dataset://v1",
            description="Verified initial rulebook",
            created_tick=100,
            sampling_weight=0.8,
        )
        digest1 = rec.compute_digest()
        digest2 = rec.compute_digest()
        assert digest1 == digest2
        assert len(digest1) == 64
        # Verify deterministic canonical JSON SHA-256 calculation
        canonical = {
            "category": "human_authored",
            "created_tick": 100,
            "description": "Verified initial rulebook",
            "provenance_id": "p-det",
            "sampling_weight": 0.8,
            "uri_or_source": "dataset://v1",
        }
        expected = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert digest1 == expected

    def test_compute_digest_with_custom_content(self) -> None:
        rec = ProvenanceRecord(
            provenance_id="p-content",
            category=ProvenanceCategory.SIMULATOR_TRACE,
            uri_or_source="sim:run-99",
        )
        content = "transition:state1:actionA:state2"
        digest = rec.compute_digest(content=content)
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert digest == expected

    def test_compute_content_digest_classmethod(self) -> None:
        data_str = "raw demonstration trace"
        assert ProvenanceRecord.compute_content_digest(data_str) == hashlib.sha256(data_str.encode("utf-8")).hexdigest()
        dict_payload = {"b": 2, "a": 1}
        expected_json = json.dumps({"a": 1, "b": 2}, separators=(",", ":")).encode("utf-8")
        assert ProvenanceRecord.compute_content_digest(dict_payload) == hashlib.sha256(expected_json).hexdigest()

    def test_with_computed_digest_and_create_factory(self) -> None:
        rec = ProvenanceRecord(
            provenance_id="p-factory",
            category=ProvenanceCategory.HUMAN_DEMONSTRATION,
            uri_or_source="expert:trace-1",
        )
        assert rec.hash_digest == ""
        populated = rec.with_computed_digest()
        assert populated.hash_digest == rec.compute_digest()
        assert populated.provenance_id == rec.provenance_id

        # Test ProvenanceRecord.create factory with auto-hash
        auto_rec = ProvenanceRecord.create(
            provenance_id="p-auto",
            category=ProvenanceCategory.SIMULATOR_TRACE,
            uri_or_source="sim:seed-555",
            created_tick=42,
        )
        assert auto_rec.hash_digest == auto_rec.compute_digest()
        assert auto_rec.created_tick == 42

        # Test ProvenanceRecord.create with explicit hash_digest
        explicit_rec = ProvenanceRecord.create(
            provenance_id="p-expl",
            category=ProvenanceCategory.MODEL_GENERATED,
            uri_or_source="vllm:model",
            hash_digest="custom_hash_123",
        )
        assert explicit_rec.hash_digest == "custom_hash_123"

    def test_provenance_record_is_frozen(self) -> None:
        rec = ProvenanceRecord(
            provenance_id="p-frozen",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="source://immutable",
        )
        with pytest.raises(ValidationError):
            rec.description = "mutation"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ProvenanceRecord(
                provenance_id="p-extra",
                category=ProvenanceCategory.HUMAN_AUTHORED,
                uri_or_source="source://test",
                extra_field="disallowed",  # type: ignore[call-arg]
            )

    def test_sampling_weight_validation_bounds(self) -> None:
        # Valid edge cases
        ProvenanceRecord(
            provenance_id="p-w0",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="s1",
            sampling_weight=0.0,
        )
        ProvenanceRecord(
            provenance_id="p-w1",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="s2",
            sampling_weight=1.0,
        )

        with pytest.raises(ValidationError):
            ProvenanceRecord(
                provenance_id="p-w-neg",
                category=ProvenanceCategory.HUMAN_AUTHORED,
                uri_or_source="s3",
                sampling_weight=-0.01,
            )

        with pytest.raises(ValidationError):
            ProvenanceRecord(
                provenance_id="p-w-gt1",
                category=ProvenanceCategory.HUMAN_AUTHORED,
                uri_or_source="s4",
                sampling_weight=1.01,
            )

    def test_created_tick_validation(self) -> None:
        with pytest.raises(ValidationError):
            ProvenanceRecord(
                provenance_id="p-tick-neg",
                category=ProvenanceCategory.HUMAN_AUTHORED,
                uri_or_source="s",
                created_tick=-1,
            )

    def test_serialization_roundtrip(self) -> None:
        original = ProvenanceRecord.create(
            provenance_id="p-json",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="https://arxiv.org/abs/2607.28287",
            description="Tycho foundation references",
            created_tick=250,
            sampling_weight=0.75,
        )
        dumped_json = original.model_dump_json()
        loaded = ProvenanceRecord.model_validate_json(dumped_json)
        assert loaded == original
        assert loaded.hash_digest == original.hash_digest


class TestManualEntryProvenanceIntegration:
    """Test ManualEntry category default, provenance wiring, and Manual real_data_fraction."""

    def test_manual_entry_defaults(self) -> None:
        entry = ManualEntry(
            text="Initial belief about resource regeneration",
            written_by="agent-seed",
        )
        assert entry.category == ProvenanceCategory.MODEL_GENERATED
        assert entry.provenance is None
        assert entry.is_ground_truth is False

    def test_manual_entry_with_provenance_syncs_category(self) -> None:
        prov = ProvenanceRecord(
            provenance_id="prov-human-1",
            category=ProvenanceCategory.HUMAN_AUTHORED,
            uri_or_source="curator:manual-seed",
        )
        entry = ManualEntry(
            text="Water sources replenish every 50 ticks",
            written_by="curator",
            provenance=prov,
        )
        # Category should automatically sync to provenance category
        assert entry.category == ProvenanceCategory.HUMAN_AUTHORED
        assert entry.provenance is prov
        assert entry.is_ground_truth is True

    def test_manual_entry_explicit_category_retained(self) -> None:
        entry = ManualEntry(
            text="Observation from simulator engine",
            written_by="system",
            category=ProvenanceCategory.SIMULATOR_TRACE,
        )
        assert entry.category == ProvenanceCategory.SIMULATOR_TRACE
        assert entry.provenance is None
        assert entry.is_ground_truth is True

    def test_manual_real_data_fraction_empty(self) -> None:
        manual = Manual(situation_key="empty:manual")
        assert manual.real_data_fraction() == 1.0

    def test_manual_real_data_fraction_calculation(self) -> None:
        manual = Manual(situation_key="foraging:forest")

        # 2 real/ground-truth entries
        e_human = ManualEntry(
            text="Berries are toxic in winter",
            written_by="human-expert",
            provenance=ProvenanceRecord(
                provenance_id="p-1",
                category=ProvenanceCategory.HUMAN_AUTHORED,
                uri_or_source="expert:manual",
            ),
        )
        e_sim = ManualEntry(
            text="Oak trees drop acorns at tick % 100 == 0",
            written_by="sim",
            category=ProvenanceCategory.SIMULATOR_TRACE,
        )

        # 2 synthetic/model-generated entries
        e_bot1 = ManualEntry(
            text="Squirrels accept stone trades",
            written_by="agent-1",
            category=ProvenanceCategory.MODEL_GENERATED,
        )
        e_bot2 = ManualEntry(
            text="Walking backwards reduces stamina cost",
            written_by="agent-2",
        )

        manual.add_entry(e_human)
        manual.add_entry(e_sim)
        manual.add_entry(e_bot1)
        manual.add_entry(e_bot2)

        # 2 out of 4 entries are real data -> 0.50
        assert manual.real_data_fraction() == 0.50

    def test_manual_revise_entry_with_provenance(self) -> None:
        manual = Manual(situation_key="crafting:tools")
        manual.add_entry(
            ManualEntry(
                text="Crafting stone tool costs 2 wood",
                written_by="agent-1",
            )
        )
        assert manual.get_entry(0).status == ManualEntryStatus.HYPOTHESIS

        prov_verified = ProvenanceRecord.create(
            provenance_id="p-craft-sim",
            category=ProvenanceCategory.SIMULATOR_TRACE,
            uri_or_source="engine:recipe-audit",
        )
        revised = manual.revise_entry(
            index=0,
            new_text="Crafting stone tool costs 1 wood and 1 stone",
            written_by="agent-1",
            evidence_id="trans-craft-1",
            provenance=prov_verified,
        )

        assert revised.status == ManualEntryStatus.HYPOTHESIS
        assert revised.revised_from == "Crafting stone tool costs 2 wood"
        assert revised.provenance == prov_verified
        assert revised.category == ProvenanceCategory.SIMULATOR_TRACE
        assert revised.is_ground_truth is True
        assert manual.get_entry(0).status == ManualEntryStatus.FALSIFIED
        # 1 falsified entry (model-gen) + 1 active entry (sim-trace) = 1/2 real = 0.5
        assert manual.real_data_fraction() == 0.5
