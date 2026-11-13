"""Phase 1.3 Data Provenance schemas (PRD FR-4, docs/phases/1.3-economy.md).

Defines provenance categories and immutable provenance records required to enforce
the real-data floor, preventing model collapse from recursive self-training on
purely model-generated artifacts.

Citations:
    - Model collapse & provenance floor: Shumailov et al. (Nature 2024,
      DOI: 10.1038/s41586-024-07566-y).
    - Cryptographic provenance and reproducible audit trails: Li et al.
      (ACM Computing Surveys 2022, DOI: 10.1145/3555803).

Note:
    These provenance contracts are an EvolZen Phase 1.3 specification choice and
    remain empirically untested until Phase 1.3 economy runs are executed.
"""
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceCategory(StrEnum):
    """Origin categories for knowledge artifacts enforcing the real-data floor."""

    HUMAN_AUTHORED = "human_authored"
    HUMAN_DEMONSTRATION = "human_demonstration"
    SIMULATOR_TRACE = "simulator_trace"
    MODEL_GENERATED = "model_generated"


GROUND_TRUTH_CATEGORIES: frozenset[ProvenanceCategory] = frozenset(
    {
        ProvenanceCategory.HUMAN_AUTHORED,
        ProvenanceCategory.HUMAN_DEMONSTRATION,
        ProvenanceCategory.SIMULATOR_TRACE,
    }
)


class ProvenanceRecord(BaseModel):
    """Immutable provenance record tracking origin, verification, and deterministic digest.

    Attributes:
        provenance_id: Unique identifier for this provenance record.
        category: Origin category classifying whether data is human, simulation, or model.
        uri_or_source: URI, path, or origin identifier (dataset URL, simulator seed, etc.).
        description: Human-readable description of the origin material.
        created_tick: Simulation clock tick at which the provenance record was registered.
        sampling_weight: Normalized sampling weight in [0.0, 1.0].
        hash_digest: Cryptographic SHA-256 digest of the canonical metadata or content.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", validate_default=True)

    provenance_id: str
    category: ProvenanceCategory
    uri_or_source: str
    description: str = ""
    created_tick: int = Field(default=0, ge=0)
    sampling_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    hash_digest: str = ""

    @property
    def is_ground_truth(self) -> bool:
        """Return True if category is human-authored, demonstration, or simulator trace."""
        return self.category in GROUND_TRUTH_CATEGORIES

    def compute_digest(self, content: str | bytes | None = None) -> str:
        """Compute deterministic SHA-256 hex digest of source content or canonical metadata."""
        if content is not None:
            payload = content.encode("utf-8") if isinstance(content, str) else content
            return hashlib.sha256(payload).hexdigest()
        canonical = {
            "category": str(self.category),
            "created_tick": self.created_tick,
            "description": self.description,
            "provenance_id": self.provenance_id,
            "sampling_weight": self.sampling_weight,
            "uri_or_source": self.uri_or_source,
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def with_computed_digest(self) -> ProvenanceRecord:
        """Return an immutable copy of this record with hash_digest populated."""
        return self.model_copy(update={"hash_digest": self.compute_digest()})

    @classmethod
    def create(
        cls,
        *,
        provenance_id: str,
        category: ProvenanceCategory,
        uri_or_source: str,
        description: str = "",
        created_tick: int = 0,
        sampling_weight: float = 1.0,
        hash_digest: str | None = None,
    ) -> ProvenanceRecord:
        """Factory creating a ProvenanceRecord, computing deterministic digest if hash_digest is None."""
        rec = cls(
            provenance_id=provenance_id,
            category=category,
            uri_or_source=uri_or_source,
            description=description,
            created_tick=created_tick,
            sampling_weight=sampling_weight,
            hash_digest=hash_digest if hash_digest is not None else "",
        )
        if hash_digest is None:
            rec = rec.with_computed_digest()
        return rec

    @classmethod
    def compute_content_digest(cls, content: str | bytes | dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hex digest for arbitrary content."""
        if isinstance(content, dict):
            payload = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        elif isinstance(content, str):
            payload = content.encode("utf-8")
        else:
            payload = content
        return hashlib.sha256(payload).hexdigest()


__all__ = [
    "GROUND_TRUTH_CATEGORIES",
    "ProvenanceCategory",
    "ProvenanceRecord",
]
