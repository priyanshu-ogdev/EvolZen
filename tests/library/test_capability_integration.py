"""Integration and lifecycle tests for capability package persistence, world synchronization,

filtered queries, and transition log ingestion.

References:
- docs/phases/1.5-library.md
- docs/subsystems/library/README.md
- docs/ARCHITECTURE.md §3.5
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pytest

from evolzen.environment.world_state import build_default_world
from evolzen.library.audit import AuditLog
from evolzen.library.persistence import SCHEMA_VERSION, LibraryStore
from evolzen.library.regression_bank import RegressionBank
from evolzen.library.rule_library import RuleLibrary
from evolzen.schemas.library import (
    AuditEventType,
    ProvenanceClass,
    RuleEntry,
    RuleStatus,
    ValidityContext,
    VerificationEvidence,
)
from evolzen.schemas.transition import Action, Emission, State, Transition
from evolzen.schemas.world import ActionType, CapabilityPackage, WorldState
from evolzen.storage.transition_log import TransitionLogStore

# ---------------------------------------------------------------------------
# Test fixtures and factory helpers
# ---------------------------------------------------------------------------

def _make_rule_entry(
    *,
    rule_id: UUID | None = None,
    rule_family_id: UUID | None = None,
    version: int = 1,
    code: str = "def predict(s, a): return s",
    explains: tuple[str, ...] = ("gravity",),
    status: RuleStatus = RuleStatus.ACTIVE,
    world_version: str = "env-v1",
) -> RuleEntry:
    rid = rule_id or uuid4()
    fid = rule_family_id or rid
    return RuleEntry(
        rule_id=rid,
        version=version,
        rule_family_id=fid,
        code=code,
        explains=explains,
        status=status,
        provenance=ProvenanceClass.EXPLORATION_VERIFIED,
        validity=ValidityContext(
            world_version=world_version,
            mechanic_keys=explains,
            seed_range=(0, 100),
            verified_at_tick=50,
        ),
        evidence=VerificationEvidence(
            evidence_id=uuid4(),
            transition_ids=(uuid4(),),
            intervention_ids=(),
            held_out_combination_ids=(),
            false_promotion_rate=0.0,
            resource_ceiling_hit=False,
        ),
        created_at=datetime.now(tz=UTC),
    )


def _make_capability_package(
    *,
    package_id: str = "craft:iron_axe:v1",
    version: str = "1.0.0",
    action_type: str = ActionType.CRAFT,
    required_resources: dict[str, int] | None = None,
    output_kind: str = "iron_axe",
    evidence_id: str = "ev-bootstrap-100",
    verified: bool = True,
) -> CapabilityPackage:
    return CapabilityPackage(
        package_id=package_id,
        version=version,
        action_type=action_type,
        required_resources=required_resources or {"wood": 2, "iron": 3},
        output_kind=output_kind,
        min_age=0,
        evidence_id=evidence_id,
        verified_replay=verified,
        verified_intervention=verified,
        verified_containment=verified,
    )


def _make_library(tmp_path: Path, name: str = "lib") -> tuple[RuleLibrary, LibraryStore, AuditLog]:
    store = LibraryStore(tmp_path / f"{name}.duckdb")
    audit = AuditLog(tmp_path / f"{name}_audit.jsonl")
    lib = RuleLibrary(store, audit)
    return lib, store, audit


# ===========================================================================
# 1. Database Schema Versioning & Guards
# ===========================================================================

def test_schema_meta_initialization_and_version(tmp_path: Path) -> None:
    """LibraryStore ensures schema_meta is created and stamped with SCHEMA_VERSION."""
    db_path = tmp_path / "lib_version.duckdb"
    store = LibraryStore(db_path)
    assert store.count() == 0

    with duckdb.connect(str(db_path)) as con:
        rows = con.execute(
            "SELECT schema_version FROM schema_meta ORDER BY initialized_at DESC LIMIT 1"
        ).fetchall()
        assert len(rows) == 1
        assert int(rows[0][0]) == SCHEMA_VERSION


def test_schema_version_mismatch_raises(tmp_path: Path) -> None:
    """LibraryStore raises RuntimeError if database schema version > SCHEMA_VERSION."""
    db_path = tmp_path / "lib_incompatible.duckdb"
    LibraryStore(db_path)

    # Manually inject a future schema version
    future_version = SCHEMA_VERSION + 1
    with duckdb.connect(str(db_path)) as con:
        con.execute(
            "INSERT INTO schema_meta (schema_version, initialized_at) VALUES (?, current_timestamp)",
            [future_version],
        )

    with pytest.raises(RuntimeError, match=f"Incompatible database schema version {future_version}"):
        LibraryStore(db_path)


# ===========================================================================
# 2. Capability Package Persistence in LibraryStore
# ===========================================================================

def test_store_capability_append_and_get_by_id(tmp_path: Path) -> None:
    """LibraryStore appends and retrieves capability packages by package_id."""
    store = LibraryStore(tmp_path / "cap_store.duckdb")
    pkg = _make_capability_package(package_id="craft:shield:v1")

    assert store.get_capability_by_id("craft:shield:v1") is None
    store.append_capability(pkg, status=RuleStatus.ACTIVE)

    fetched = store.get_capability_by_id("craft:shield:v1")
    assert fetched is not None
    assert fetched.package_id == "craft:shield:v1"
    assert fetched.output_kind == "iron_axe"
    assert fetched.evidence_id == "ev-bootstrap-100"
    assert fetched.verified_replay is True


def test_store_capability_get_all_and_active(tmp_path: Path) -> None:
    """LibraryStore retrieves all or active-only capability packages correctly."""
    store = LibraryStore(tmp_path / "cap_active.duckdb")
    pkg1 = _make_capability_package(package_id="cap:active:1")
    pkg2 = _make_capability_package(package_id="cap:deprecated:2")
    pkg3 = _make_capability_package(package_id="cap:active:3")

    store.append_capability(pkg1, status=RuleStatus.ACTIVE)
    store.append_capability(pkg2, status=RuleStatus.DEPRECATED)
    store.append_capability(pkg3, status=RuleStatus.ACTIVE)

    all_caps = store.get_all_capabilities()
    assert len(all_caps) == 3
    assert {c.package_id for c in all_caps} == {"cap:active:1", "cap:deprecated:2", "cap:active:3"}

    active_caps = store.get_active_capabilities()
    assert len(active_caps) == 2
    assert {c.package_id for c in active_caps} == {"cap:active:1", "cap:active:3"}

    assert store.count_capabilities() == 3
    assert store.count_active_capabilities() == 2


def test_store_capability_status_update_is_append_only(tmp_path: Path) -> None:
    """LibraryStore.update_capability_status appends a new row without deleting prior rows."""
    db_path = tmp_path / "cap_update.duckdb"
    store = LibraryStore(db_path)
    pkg = _make_capability_package(package_id="cap:mutating:1")
    store.append_capability(pkg, status=RuleStatus.ACTIVE)

    assert store.count_active_capabilities() == 1
    store.update_capability_status("cap:mutating:1", RuleStatus.SUPERSEDED)

    assert store.count_active_capabilities() == 0
    assert store.count_capabilities() == 1

    # Verify append-only guarantee in DuckDB table
    with duckdb.connect(str(db_path)) as con:
        rows = con.execute(
            "SELECT row_seq, status FROM capability_packages WHERE package_id = ? ORDER BY row_seq",
            ["cap:mutating:1"],
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][1] == "active"
        assert rows[1][1] == "superseded"
        assert rows[1][0] > rows[0][0]

    with pytest.raises(KeyError, match="No capability package found"):
        store.update_capability_status("nonexistent", RuleStatus.DEPRECATED)


def test_store_list_capabilities_by_evidence(tmp_path: Path) -> None:
    """LibraryStore filters capability packages by evidence_id."""
    store = LibraryStore(tmp_path / "cap_evidence.duckdb")
    pkg1 = _make_capability_package(package_id="cap:ev:1", evidence_id="ev-alpha")
    pkg2 = _make_capability_package(package_id="cap:ev:2", evidence_id="ev-beta")
    pkg3 = _make_capability_package(package_id="cap:ev:3", evidence_id="ev-alpha")

    store.append_capability(pkg1)
    store.append_capability(pkg2)
    store.append_capability(pkg3)

    alpha_caps = store.list_capabilities_by_evidence("ev-alpha")
    assert len(alpha_caps) == 2
    assert {c.package_id for c in alpha_caps} == {"cap:ev:1", "cap:ev:3"}

    beta_caps = store.list_capabilities_by_evidence("ev-beta")
    assert len(beta_caps) == 1
    assert beta_caps[0].package_id == "cap:ev:2"

    assert store.list_capabilities_by_evidence("ev-gamma") == []


# ===========================================================================
# 3. Capability Lifecycle in RuleLibrary
# ===========================================================================

def test_rule_library_register_capability_verified(tmp_path: Path) -> None:
    """RuleLibrary registers verified capability package and emits audit event."""
    lib, _store, audit = _make_library(tmp_path, "reg_cap")

    pkg = _make_capability_package(package_id="craft:pickaxe:v1", verified=True)
    registered = lib.register_capability(pkg)

    assert registered.package_id == "craft:pickaxe:v1"
    assert lib.get_capability("craft:pickaxe:v1") is not None
    assert lib.capability_count() == 1
    assert lib.active_capability_count() == 1

    events = audit.load_all()
    assert len(events) == 1
    assert events[0].event_type == AuditEventType.SPAWN
    assert events[0].detail["package_id"] == "craft:pickaxe:v1"


def test_rule_library_register_capability_unverified_raises(tmp_path: Path) -> None:
    """RuleLibrary rejects registration of unverified capability packages."""
    lib, _store, _audit = _make_library(tmp_path, "unverified")

    unverified = _make_capability_package(package_id="craft:flawed:v1", verified=False)
    with pytest.raises(ValueError, match="failed verification gates"):
        lib.register_capability(unverified)


def test_rule_library_register_capability_with_evidence(tmp_path: Path) -> None:
    """RuleLibrary promotes capability using valid verification evidence bundle."""
    lib, _store, audit = _make_library(tmp_path, "promote_cap")

    evidence_uuid = uuid4()
    evidence = VerificationEvidence(
        evidence_id=evidence_uuid,
        transition_ids=(uuid4(),),
        intervention_ids=(),
        held_out_combination_ids=(),
        false_promotion_rate=0.0,
        resource_ceiling_hit=False,
    )

    pkg = _make_capability_package(
        package_id="craft:bow:v1",
        evidence_id=str(evidence_uuid),
        verified=False,  # Upgraded by evidence
    )

    registered = lib.register_capability(pkg, evidence=evidence)
    assert registered.verified_replay is True
    assert registered.verified_intervention is True
    assert registered.verified_containment is True
    assert registered.evidence_id == str(evidence_uuid)

    events = audit.load_all()
    assert len(events) == 1
    assert events[0].event_type == AuditEventType.PROMOTE

    # Check evidence failure conditions
    ceiling_evidence = evidence.model_copy(update={"resource_ceiling_hit": True})
    with pytest.raises(ValueError, match="hit resource ceiling"):
        lib.register_capability(pkg, evidence=ceiling_evidence)

    leaky_evidence = evidence.model_copy(update={"false_promotion_rate": 0.05})
    with pytest.raises(ValueError, match="false promotion rate 0.05 > 0.0"):
        lib.register_capability(pkg, evidence=leaky_evidence)

    mismatched_pkg = _make_capability_package(
        package_id="craft:bow:v2",
        evidence_id="different-evidence-id",
        verified=False,
    )
    with pytest.raises(ValueError, match="Mismatched evidence_id"):
        lib.register_capability(mismatched_pkg, evidence=evidence)


def test_rule_library_supersede_capability(tmp_path: Path) -> None:
    """RuleLibrary supersedes capability package with explicit audit logging."""
    lib, _store, audit = _make_library(tmp_path, "supersede_cap")

    old_pkg = _make_capability_package(package_id="craft:armor:v1", version="1.0.0")
    lib.register_capability(old_pkg)

    new_pkg = _make_capability_package(
        package_id="craft:armor:v2",
        version="2.0.0",
        required_resources={"iron": 5, "leather": 2},
    )

    valid_reason = "Upgraded to reinforced plate with reduced raw material overhead"
    lib.supersede_capability("craft:armor:v1", new_pkg, reason=valid_reason)

    assert lib.get_capability("craft:armor:v1") is not None
    assert lib.get_capability("craft:armor:v2") is not None

    active_caps = lib.get_active_capabilities()
    assert len(active_caps) == 1
    assert active_caps[0].package_id == "craft:armor:v2"

    events = audit.load_all()
    assert len(events) == 2
    supersede_event = events[1]
    assert supersede_event.event_type == AuditEventType.SUPERSEDE
    assert supersede_event.detail["old_package_id"] == "craft:armor:v1"
    assert supersede_event.detail["new_package_id"] == "craft:armor:v2"
    assert supersede_event.detail["reason"] == valid_reason

    # Test rejection on unverified replacement
    unverified_replacement = _make_capability_package(
        package_id="craft:armor:v3",
        verified=False,
    )
    with pytest.raises(ValueError, match="failed verification gates"):
        lib.supersede_capability("craft:armor:v2", unverified_replacement, reason=valid_reason)

    # Test rejection on short reason (< 10 chars)
    with pytest.raises(ValueError, match="at least 10 non-whitespace characters"):
        lib.supersede_capability("craft:armor:v2", new_pkg, reason="short")

    # Test rejection on nonexistent old package
    with pytest.raises(KeyError, match="No capability package found"):
        lib.supersede_capability("craft:armor:v999", new_pkg, reason="valid reason 12345")


def test_rule_library_export_capabilities_to_world(tmp_path: Path) -> None:
    """RuleLibrary exports active capabilities into WorldState.capabilities."""
    lib, _store, _audit = _make_library(tmp_path, "export_cap")

    pkg1 = _make_capability_package(package_id="craft:scythe:v1")
    lib.register_capability(pkg1)

    world: WorldState = build_default_world(seed=7)
    assert "craft:tool:v1" in world.capabilities
    assert "craft:scythe:v1" not in world.capabilities

    updated_world = lib.export_capabilities_to_world(world)
    assert "craft:scythe:v1" in updated_world.capabilities
    assert "craft:tool:v1" in updated_world.capabilities
    assert updated_world.capabilities["craft:scythe:v1"].package_id == "craft:scythe:v1"


def test_rule_library_import_capabilities_from_world(tmp_path: Path) -> None:
    """RuleLibrary imports verified capabilities from WorldState into library store."""
    lib, _store, _audit = _make_library(tmp_path, "import_cap")

    world: WorldState = build_default_world(seed=8)
    # Add an unverified capability to world that should be skipped
    unverified_pkg = _make_capability_package(package_id="craft:draft:v1", verified=False)
    world = world.model_copy(
        update={"capabilities": {**world.capabilities, "craft:draft:v1": unverified_pkg}}
    )

    imported = lib.import_capabilities_from_world(world)
    assert len(imported) == 1
    assert imported[0].package_id == "craft:tool:v1"

    # Re-importing should skip already imported package
    second_import = lib.import_capabilities_from_world(world)
    assert len(second_import) == 0

    assert lib.get_capability("craft:tool:v1") is not None
    assert lib.get_capability("craft:draft:v1") is None


# ===========================================================================
# 4. Filtered Querying in RuleLibrary
# ===========================================================================

def test_find_by_mechanic(tmp_path: Path) -> None:
    """RuleLibrary.find_by_mechanic filters active rules explaining given mechanic."""
    lib, store, _audit = _make_library(tmp_path, "filter_mech")

    entry1 = _make_rule_entry(explains=("gravity", "collision"))
    entry2 = _make_rule_entry(explains=("thermodynamics",))
    entry3 = _make_rule_entry(explains=("gravity",), status=RuleStatus.DEPRECATED)

    store.append_rule(entry1)
    store.append_rule(entry2)
    store.append_rule(entry3)

    grav_rules = lib.find_by_mechanic("gravity")
    assert len(grav_rules) == 1
    assert grav_rules[0].rule_id == entry1.rule_id

    col_rules = lib.find_by_mechanic("collision")
    assert len(col_rules) == 1
    assert col_rules[0].rule_id == entry1.rule_id

    thermo_rules = lib.find_by_mechanic("thermodynamics")
    assert len(thermo_rules) == 1
    assert thermo_rules[0].rule_id == entry2.rule_id

    unknown_rules = lib.find_by_mechanic("electromagnetism")
    assert unknown_rules == []


def test_find_by_world_version(tmp_path: Path) -> None:
    """RuleLibrary.find_by_world_version filters active rules by validity.world_version."""
    lib, store, _audit = _make_library(tmp_path, "filter_version")

    entry_v1 = _make_rule_entry(world_version="env-v1")
    entry_v2 = _make_rule_entry(world_version="env-v2")
    entry_v1_dep = _make_rule_entry(world_version="env-v1", status=RuleStatus.DEPRECATED)

    store.append_rule(entry_v1)
    store.append_rule(entry_v2)
    store.append_rule(entry_v1_dep)

    v1_rules = lib.find_by_world_version("env-v1")
    assert len(v1_rules) == 1
    assert v1_rules[0].rule_id == entry_v1.rule_id

    v2_rules = lib.find_by_world_version("env-v2")
    assert len(v2_rules) == 1
    assert v2_rules[0].rule_id == entry_v2.rule_id

    v3_rules = lib.find_by_world_version("env-v3")
    assert v3_rules == []


# ===========================================================================
# 5. Regression Bank Transition Ingestion
# ===========================================================================

def test_regression_bank_register_from_transitions(tmp_path: Path) -> None:
    """RegressionBank ingests sequences of Transition objects into serialisable fixtures."""
    bank = RegressionBank(tmp_path / "bank.duckdb")
    rule_id = uuid4()

    t1 = Transition(
        state=State(data={"tick": 0, "energy": 100}),
        action=Action(agent_id="agent-0", action_type="gather"),
        emission=Emission(data={"harvested": 5, "mechanic": "resource_gather"}),
        next_state=State(data={"tick": 1, "energy": 95}),
        seed=42,
    )
    t2 = Transition(
        state=State(data={"tick": 1, "energy": 95}),
        action=Action(agent_id="agent-0", action_type="craft"),
        emission=Emission(data={"crafted_item": "tool", "mechanic": "craft"}),
        next_state=State(data={"tick": 2, "energy": 80}),
        seed=42,
    )

    registered_tids = bank.register_from_transitions(rule_id, [t1, t2])
    assert len(registered_tids) == 2
    assert registered_tids == [t1.transition_id, t2.transition_id]

    fixtures = bank.cases_for_rule(rule_id)
    assert len(fixtures) == 2
    assert fixtures[0]["expected_emission"] == {"harvested": 5, "mechanic": "resource_gather"}
    assert fixtures[0]["action_type"] == "gather"
    assert fixtures[1]["expected_emission"] == {"crafted_item": "tool", "mechanic": "craft"}
    assert fixtures[1]["action_type"] == "craft"

    entry = _make_rule_entry(rule_id=rule_id)
    result = bank.check_rule(rule_id, entry=entry)
    assert result.all_passed is True
    assert len(result.failed_transition_ids) == 0


def test_regression_bank_register_from_transition_store(tmp_path: Path) -> None:
    """RegressionBank ingests recorded transitions from a DuckDB TransitionLogStore."""
    store_path = tmp_path / "transitions.duckdb"
    bank_path = tmp_path / "bank.duckdb"

    t1 = Transition(
        state=State(data={"tick": 0, "energy": 100}),
        action=Action(agent_id="agent-0", action_type="gather"),
        emission=Emission(data={"harvested": 3}),
        next_state=State(data={"tick": 1, "energy": 90}),
        seed=10,
    )
    t2 = Transition(
        state=State(data={"tick": 2, "energy": 90}),
        action=Action(agent_id="agent-1", action_type="wait"),
        emission=Emission(data={"harvested": 0}),
        next_state=State(data={"tick": 3, "energy": 90}),
        seed=10,
    )

    with TransitionLogStore(store_path) as trans_store:
        trans_store.append(t1, run_id="run-ingest")
        trans_store.append(t2, run_id="run-ingest")

        bank = RegressionBank(bank_path)
        rule_id = uuid4()

        # Ingest only up to tick 1 (should match t1 only)
        ingested_ids = bank.register_from_transition_store(
            rule_id=rule_id,
            store=trans_store,
            run_id="run-ingest",
            up_to_tick=1,
        )

        assert len(ingested_ids) == 1
        assert ingested_ids[0] == t1.transition_id

        fixtures = bank.cases_for_rule(rule_id)
        assert len(fixtures) == 1
        assert "expected_emission" in fixtures[0]
        assert fixtures[0]["transition_id"] == str(t1.transition_id)
        assert fixtures[0]["expected_emission"] == {"harvested": 3}
