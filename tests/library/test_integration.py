"""End-to-end Phase 1.5 integration test — zero forgetting across >= 3 rounds.

Verifies the full lifecycle of ``evolzen.library`` across three successive
addition, promotion, routing, deprecation, and supersession rounds while
preserving immutable historical records and achieving zero regression on the
held-out regression bank.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from evolzen.config import LibrarySettings, load_settings
from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library import (
    AuditLog,
    LibraryStore,
    RegressionBank,
    RuleLibrary,
    applicable_entries,
    is_applicable,
    needs_supersession,
    validate_supersession_reason,
)
from evolzen.schemas.library import (
    AuditEventType,
    ProvenanceClass,
    RegressionResult,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
    ValidityContext,
    VerificationEvidence,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _ctx(world_version: str = "env-v1", mechanic: str = "gravity") -> ValidityContext:
    return ValidityContext(
        world_version=world_version,
        mechanic_keys=(mechanic,),
        seed_range=(0, 99),
        verified_at_tick=100,
    )


def _evidence(fp_rate: float = 0.02) -> VerificationEvidence:
    return VerificationEvidence(
        evidence_id=uuid4(),
        transition_ids=(uuid4(), uuid4()),
        intervention_ids=(uuid4(),),
        held_out_combination_ids=(uuid4(),),
        false_promotion_rate=fp_rate,
        resource_ceiling_hit=False,
    )


def _register_fixtures(bank: RegressionBank, rule_id: UUID, count: int = 5) -> None:
    tids = [uuid4() for _ in range(count)]
    fixtures = [
        {
            "transition_id": str(tid),
            "expected_emission": f"em_{idx}",
            "actual_emission": f"em_{idx}",
        }
        for idx, tid in enumerate(tids)
    ]
    bank.register(rule_id, tids, fixtures)


@pytest.mark.integration
def test_three_round_zero_forgetting_and_full_audit_trail(tmp_path: Path) -> None:
    """Phase 1.5 end-to-end scenario across three rounds of additions."""
    # Load LibrarySettings pattern with tmp_path overrides
    base_settings = load_settings(LibrarySettings, Path("configs/library.yaml"))
    db_path = tmp_path / base_settings.db_path.name
    audit_path = tmp_path / base_settings.audit_log_path.name

    store = LibraryStore(db_path)
    audit = AuditLog(audit_path)
    library = RuleLibrary(
        store=store,
        audit_log=audit,
        routing_threshold=base_settings.routing_confidence_threshold,
    )
    bank = RegressionBank(db_path)

    all_results: list[RegressionResult] = []

    # ------------------------------------------------------------------
    # Round 1: Spawn 3 distinct rules, register 5 fixtures each, check
    # ------------------------------------------------------------------
    r1_specs = [
        ("def apply_gravity(s, a): return {'vy': s['vy'] - 9.81}", "gravity"),
        ("def elastic_bounce(s, a): return {'vx': -s['vx'] * 0.9}", "collision"),
        ("def thermal_decay(s, a): return {'temp': s['temp'] * 0.95}", "thermodynamics"),
    ]
    r1_entries: list[RuleEntry] = []
    for code, mech in r1_specs:
        entry = library.spawn_if_novel(
            CandidateRule(rule_id=str(uuid4()), code=code, explains=[mech]),
            validity=_ctx("env-v1", mech),
            evidence=_evidence(),
        )
        assert entry is not None
        _register_fixtures(bank, entry.rule_id, count=5)
        r1_entries.append(entry)

    r1_results = bank.check_all_active(library, store)
    assert len(r1_results) == 3
    assert RegressionBank.any_regression(r1_results) is False
    all_results.extend(r1_results)

    # ------------------------------------------------------------------
    # Round 2: 1 novel spawn + 1 duplicate routed + 2 promotions
    # ------------------------------------------------------------------
    r2_novel = library.spawn_if_novel(
        CandidateRule(
            rule_id=str(uuid4()),
            code="def fluid_drag(s, a): return {'drag': 0.5 * s['rho'] * s['v'] ** 2}",
            explains=["drag"],
        ),
        validity=_ctx("env-v1", "drag"),
        evidence=_evidence(),
    )
    assert r2_novel is not None
    _register_fixtures(bank, r2_novel.rule_id, count=5)

    # Identical code to r1_entries[0] -> must route, not spawn
    r2_duplicate = library.spawn_if_novel(
        CandidateRule(rule_id=str(uuid4()), code=r1_specs[0][0], explains=["gravity"]),
        validity=_ctx("env-v1", "gravity"),
        evidence=_evidence(),
    )
    assert r2_duplicate is None

    # Promote two existing rules with tighter false_promotion_rate evidence
    library.promote(r1_entries[0].rule_id, _evidence(fp_rate=0.005))
    library.promote(r1_entries[1].rule_id, _evidence(fp_rate=0.005))

    r2_results = bank.check_all_active(library, store)
    assert len(r2_results) == 4
    assert RegressionBank.any_regression(r2_results) is False
    all_results.extend(r2_results)

    # ------------------------------------------------------------------
    # Round 3: Deprecate 1, supersede 1 (with validity context shift), spawn 1
    # ------------------------------------------------------------------
    library.deprecate(r1_entries[2].rule_id, reason="Thermodynamics disabled in env-v2.")

    # Rule 0 needs supersession when moving to env-v2
    v2_ctx = _ctx("env-v2", "gravity")
    assert needs_supersession(r1_entries[0], v2_ctx) is True
    reason = validate_supersession_reason(
        "World shifted to env-v2 with updated gravitational constant."
    )
    r1_v2 = RuleEntry(
        rule_id=uuid4(),
        version=2,
        rule_family_id=r1_entries[0].rule_family_id,
        code="def apply_gravity_v2(s, a): return {'vy': s['vy'] - 3.72}",
        explains=("gravity",),
        status=RuleStatus.ACTIVE,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=v2_ctx,
        evidence=_evidence(fp_rate=0.0),
        created_at=_now(),
    )
    link = SupersessionLink(
        old_rule_id=r1_entries[0].rule_id,
        new_rule_id=r1_v2.rule_id,
        reason=reason,
        linked_at=_now(),
    )
    library.supersede(r1_entries[0].rule_id, r1_v2, link)
    _register_fixtures(bank, r1_v2.rule_id, count=5)

    r3_novel = library.spawn_if_novel(
        CandidateRule(
            rule_id=str(uuid4()),
            code="def magnetic_flux(s, a): return {'emf': -s['dphi_dt']}",
            explains=["electromagnetism"],
        ),
        validity=_ctx("env-v2", "electromagnetism"),
        evidence=_evidence(),
    )
    assert r3_novel is not None
    _register_fixtures(bank, r3_novel.rule_id, count=5)

    r3_results = bank.check_all_active(library, store)
    # Active: r1_entries[1], r2_novel, r1_v2, r3_novel => 4 active rules
    assert len(r3_results) == 4
    assert RegressionBank.any_regression(r3_results) is False
    all_results.extend(r3_results)

    # ------------------------------------------------------------------
    # Final assertions: Zero forgetting, immutability, family, audit trail
    # ------------------------------------------------------------------
    assert RegressionBank.any_regression(all_results) is False

    # Total distinct rules: 3 (R1) + 1 (R2) + 1 (v2) + 1 (R3) = 6
    assert len(library) == 6
    assert library.active_count() == 4

    # Historical superseded & deprecated rules remain readable
    deprecated_read = library.get(r1_entries[2].rule_id)
    assert deprecated_read is not None
    assert deprecated_read.status is RuleStatus.DEPRECATED
    assert deprecated_read.deprecation_reason == "Thermodynamics disabled in env-v2."

    superseded_read = library.get(r1_entries[0].rule_id)
    assert superseded_read is not None
    assert superseded_read.status is RuleStatus.SUPERSEDED
    assert superseded_read.superseded_by == r1_v2.rule_id

    # Family linkage preserved and ordered
    family = library.get_family(r1_entries[0].rule_family_id)
    assert [e.version for e in family] == [1, 2]
    assert is_applicable(family[0], v2_ctx) is False
    assert is_applicable(family[1], v2_ctx) is True
    assert len(applicable_entries(library.get_all(), v2_ctx)) == 1  # r1_v2 (gravity in env-v2)

    # Exact sequence of audit events
    events = audit.load_all()
    assert [e.event_type for e in events] == [
        AuditEventType.SPAWN,
        AuditEventType.SPAWN,
        AuditEventType.SPAWN,
        AuditEventType.SPAWN,
        AuditEventType.ROUTE,
        AuditEventType.PROMOTE,
        AuditEventType.PROMOTE,
        AuditEventType.DEPRECATE,
        AuditEventType.SUPERSEDE,
        AuditEventType.SPAWN,
    ]
