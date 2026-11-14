from pathlib import Path
from uuid import uuid4

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.audit import AuditLog
from evolzen.library.persistence import LibraryStore
from evolzen.library.rule_library import RuleLibrary
from evolzen.recognition.moe_library import SparseMoELibrary
from evolzen.schemas.library import ValidityContext, VerificationEvidence


class MockRouter:
    """Mock router returning configured rule_ids."""

    def __init__(self, target_ids: list[str]) -> None:
        self.target_ids = target_ids

    def route(self, query_embedding: list[float], top_k: int) -> list[str]:
        return self.target_ids[:top_k]


def test_sparse_moe_library_retrieval(tmp_path: Path) -> None:
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    library = RuleLibrary(store, audit)

    val = ValidityContext(world_version="env-v1", mechanic_keys=("gravity",), seed_range=(0, 99), verified_at_tick=10)
    ev = VerificationEvidence(evidence_id=uuid4(), transition_ids=(uuid4(),), intervention_ids=(), held_out_combination_ids=())

    rule1 = CandidateRule(rule_id="r1", code="def predict(s, a, e, sd): return {}", explains=["g1"])
    rule2 = CandidateRule(rule_id="r2", code="def predict(s, a, e, sd): return {'status': 'ok'}", explains=["g2"])

    e1 = library.spawn_if_novel(rule1, val, ev)
    e2 = library.spawn_if_novel(rule2, val, ev)
    assert e1 is not None
    assert e2 is not None

    router = MockRouter(target_ids=[str(e1.rule_id)])
    moe = SparseMoELibrary(rule_library=library, router=router, top_k=2)

    active = moe.active_entries([0.1, 0.2, 0.3])
    assert len(active) == 1
    assert active[0].rule_id == e1.rule_id


def test_sparse_moe_library_missing_entries(tmp_path: Path) -> None:
    store = LibraryStore(tmp_path / "lib.duckdb")
    audit = AuditLog(tmp_path / "audit.jsonl")
    library = RuleLibrary(store, audit)

    router = MockRouter(target_ids=["nonexistent-rule-uuid", str(uuid4())])
    moe = SparseMoELibrary(rule_library=library, router=router, top_k=2)

    active = moe.active_entries([0.0] * 4)
    assert active == []
