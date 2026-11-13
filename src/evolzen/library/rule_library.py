"""The append-only, non-overwriting verified-rule library (Phase 1.5).

Verified rules (that passed ``evolzen.exploration.verifier.Verifier``) become
frozen :class:`~evolzen.schemas.library.RuleEntry` instances stored here.  A new
entry is spawned only when no existing active rule is sufficiently similar to the
candidate — the same "does this fit anything I already have?" logic as a Dirichlet
process mixture model (Ferguson, 1973).  Existing entries are **never** overwritten;
the Phase 1.5 success metric is exactly zero forgetting on a held-out regression
bank across repeated additions (untested until CI runs).

Default routing uses ``difflib.SequenceMatcher`` on ``code`` text — a stdlib-only,
dependency-free baseline.  Callers may supply a custom ``routing_confidence_fn`` for
embedding-based or AST-based similarity.

Phase 1.5 — evolzen.library.
Reference: docs/phases/1.5-library.md, docs/ARCHITECTURE.md §3.5, PRD FR-6,
Ferguson (1973) "A Bayesian Analysis of Some Nonparametric Problems".
"""

from __future__ import annotations

import difflib
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from evolzen.exploration.synthesizer import CandidateRule
from evolzen.library.audit import AuditLog, make_event
from evolzen.library.persistence import LibraryStore
from evolzen.library.validity import is_applicable, validate_supersession_reason
from evolzen.schemas.library import (
    AuditEvent,
    AuditEventType,
    ProvenanceClass,
    RuleEntry,
    RuleStatus,
    SupersessionLink,
    ValidityContext,
    VerificationEvidence,
)
from evolzen.schemas.world import CapabilityPackage, WorldState

#: Callable type for similarity scoring between two rule entries.
#: Must return a float in ``[0.0, 1.0]``; higher means more similar.
RoutingConfidenceFn = Callable[[RuleEntry, RuleEntry], float]


def _package_id_to_uuid(package_id: str) -> UUID:
    """Deterministic conversion of a string package_id to a UUID for audit events."""
    try:
        return UUID(package_id)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"evolzen:capability:{package_id}")


def _default_confidence(a: RuleEntry, b: RuleEntry) -> float:
    """Context-aware stdlib SequenceMatcher similarity on ``code`` text.

    Returns ``0.0`` immediately if *b* is not applicable in *a*'s validity
    context so routing never collapses distinct world versions or mechanics.

    Args:
        a: Candidate rule entry.
        b: Existing active rule entry.

    Returns:
        Similarity ratio in ``[0.0, 1.0]``.
    """
    if not is_applicable(b, a.validity):
        return 0.0
    return difflib.SequenceMatcher(None, a.code, b.code).ratio()


def _candidate_to_entry(
    candidate: CandidateRule,
    provenance: ProvenanceClass,
    validity: ValidityContext,
    evidence: VerificationEvidence,
    rule_family_id: UUID | None = None,
    version: int = 1,
) -> RuleEntry:
    """Convert a :class:`~evolzen.exploration.synthesizer.CandidateRule` to a :class:`RuleEntry`.

    Args:
        candidate: The raw synthesiser hypothesis.
        provenance: Origin classification.
        validity: World version and mechanic context.
        evidence: Verification evidence bundle.
        rule_family_id: Family UUID (new UUID if ``None``).
        version: Version number (1 for a new entry).

    Returns:
        A new, immutable :class:`RuleEntry`.
    """
    return RuleEntry(
        rule_id=uuid4(),
        version=version,
        rule_family_id=rule_family_id or uuid4(),
        code=candidate.code,
        explains=tuple(candidate.explains),
        status=RuleStatus.ACTIVE,
        provenance=provenance,
        validity=validity,
        evidence=evidence,
        created_at=datetime.now(tz=UTC),
    )


class RuleLibrary:
    """Append-only collection of verified rules backed by :class:`~evolzen.library.persistence.LibraryStore`.

    All mutation methods write through the store and emit an :class:`~evolzen.schemas.library.AuditEvent`.
    No entry is ever overwritten or deleted.

    Args:
        store: The :class:`~evolzen.library.persistence.LibraryStore` instance.
        audit_log: The :class:`~evolzen.library.audit.AuditLog` instance.
        routing_threshold: Similarity threshold in ``[0.0, 1.0]`` above which a
            candidate is routed to an existing entry rather than spawning a new one.
        routing_confidence_fn: Similarity scorer.  Defaults to
            :func:`_default_confidence` (SequenceMatcher on code text).

    Example::

        store = LibraryStore(Path("data/library.duckdb"))
        audit = AuditLog(Path("data/library_audit.jsonl"))
        library = RuleLibrary(store, audit, routing_threshold=0.85)
        entry = library.spawn_if_novel(candidate, validity=ctx, evidence=ev)
    """

    def __init__(
        self,
        store: LibraryStore,
        audit_log: AuditLog,
        routing_threshold: float = 0.85,
        routing_confidence_fn: RoutingConfidenceFn | None = None,
    ) -> None:
        self._store = store
        self._audit = audit_log
        self._threshold = routing_threshold
        self._confidence_fn: RoutingConfidenceFn = (
            routing_confidence_fn or _default_confidence
        )

    # ------------------------------------------------------------------
    # Spawn / routing
    # ------------------------------------------------------------------

    def spawn_if_novel(
        self,
        candidate: CandidateRule,
        validity: ValidityContext,
        evidence: VerificationEvidence,
        provenance: ProvenanceClass = ProvenanceClass.EXPLORATION_VERIFIED,
    ) -> RuleEntry | None:
        """Spawn a new library entry if *candidate* is sufficiently novel.

        Computes similarity between *candidate* (wrapped as a temporary
        :class:`RuleEntry`) and each active entry.  If the maximum similarity
        is at or above ``routing_threshold``, the candidate is *routed* to the
        existing entry and ``None`` is returned.  Otherwise a new entry is
        appended and returned.

        No existing entry is ever modified.

        Args:
            candidate: The synthesiser hypothesis to evaluate.
            validity: Validity context under which the candidate was verified.
            evidence: Verification evidence for the candidate.
            provenance: Origin classification (default:
                :attr:`~evolzen.schemas.library.ProvenanceClass.EXPLORATION_VERIFIED`).

        Returns:
            The new :class:`RuleEntry` if spawned, or ``None`` if routed.
        """
        # Build a temporary entry just for similarity scoring (not persisted).
        temp_entry = _candidate_to_entry(candidate, provenance, validity, evidence)

        active = self._store.get_active()
        best_score = 0.0
        best_match: RuleEntry | None = None
        for existing in active:
            score = self._confidence_fn(temp_entry, existing)
            if score > best_score:
                best_score = score
                best_match = existing

        if best_score >= self._threshold and best_match is not None:
            # Route — record audit event, do NOT persist temp_entry.
            self._audit.record(
                make_event(
                    AuditEventType.ROUTE,
                    rule_id=best_match.rule_id,
                    detail={
                        "candidate_rule_id": candidate.rule_id,
                        "similarity_score": best_score,
                        "threshold": self._threshold,
                    },
                )
            )
            return None

        # Spawn — persist the new entry and record audit event.
        self._store.append_rule(temp_entry)
        self._audit.record(
            make_event(
                AuditEventType.SPAWN,
                rule_id=temp_entry.rule_id,
                detail={
                    "candidate_rule_id": candidate.rule_id,
                    "best_similarity": best_score,
                    "provenance": str(provenance),
                },
            )
        )
        return temp_entry

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def promote(self, rule_id: UUID, evidence: VerificationEvidence) -> RuleEntry:
        """Promote a rule by updating its verification evidence (stays ACTIVE).

        Records a PROMOTE audit event.  The rule must already be ACTIVE.

        Args:
            rule_id: UUID of the rule to promote.
            evidence: Updated :class:`~evolzen.schemas.library.VerificationEvidence`.

        Returns:
            The updated :class:`RuleEntry` (freshly read from the store).

        Raises:
            KeyError: If *rule_id* does not exist in the store.
            ValueError: If the rule is not currently ACTIVE.
        """
        entry = self._store.get_by_id(rule_id)
        if entry is None:
            raise KeyError(f"No rule entry found for rule_id={rule_id}")
        if entry.status is not RuleStatus.ACTIVE:
            raise ValueError(
                f"Only ACTIVE rules can be promoted; {rule_id} is {entry.status}"
            )
        updated = self._store.update_evidence(rule_id, evidence)
        self._audit.record(
            make_event(
                AuditEventType.PROMOTE,
                rule_id=rule_id,
                detail={"evidence_id": str(evidence.evidence_id)},
            )
        )
        return updated

    def supersede(
        self,
        old_id: UUID,
        new_entry: RuleEntry,
        link: SupersessionLink,
    ) -> None:
        """Supersede *old_id* with *new_entry*, linked by *link*.

        Persists *new_entry*, updates *old_id*'s status to SUPERSEDED, and
        appends the :class:`~evolzen.schemas.library.SupersessionLink`.
        Records a SUPERSEDE audit event.

        Args:
            old_id: UUID of the rule being superseded.
            new_entry: Replacement :class:`RuleEntry` (already constructed by caller).
            link: :class:`~evolzen.schemas.library.SupersessionLink` documenting the
                reason.

        Raises:
            KeyError: If *old_id* does not exist.
            ValueError: If ``link.old_rule_id != old_id`` or
                ``link.new_rule_id != new_entry.rule_id``.
        """
        if link.old_rule_id != old_id:
            raise ValueError("link.old_rule_id must equal old_id")
        if link.new_rule_id != new_entry.rule_id:
            raise ValueError("link.new_rule_id must equal new_entry.rule_id")
        old = self._store.get_by_id(old_id)
        if old is None:
            raise KeyError(f"No rule entry found for rule_id={old_id}")

        self._store.append_rule(new_entry)
        self._store.update_status(
            old_id,
            RuleStatus.SUPERSEDED,
            superseded_by=new_entry.rule_id,
            reason=None,
        )
        self._store.append_supersession(link)
        self._audit.record(
            make_event(
                AuditEventType.SUPERSEDE,
                rule_id=old_id,
                detail={
                    "new_rule_id": str(new_entry.rule_id),
                    "reason": link.reason,
                },
            )
        )

    def deprecate(self, rule_id: UUID, reason: str) -> RuleEntry:
        """Mark a rule as DEPRECATED with a documented reason.

        Records a DEPRECATE audit event.

        Args:
            rule_id: UUID of the rule to deprecate.
            reason: Human-readable deprecation reason.

        Returns:
            The updated :class:`RuleEntry`.

        Raises:
            KeyError: If *rule_id* does not exist.
        """
        entry = self._store.get_by_id(rule_id)
        if entry is None:
            raise KeyError(f"No rule entry found for rule_id={rule_id}")
        self._store.update_status(
            rule_id, RuleStatus.DEPRECATED, superseded_by=None, reason=reason
        )
        self._audit.record(
            make_event(
                AuditEventType.DEPRECATE,
                rule_id=rule_id,
                detail={"reason": reason},
            )
        )
        result = self._store.get_by_id(rule_id)
        assert result is not None
        return result

    def reject(
        self,
        candidate: CandidateRule,
        reason: str,
        evidence: VerificationEvidence | None = None,
    ) -> AuditEvent:
        """Record an explicit rejection decision for a candidate rule.

        Does not persist *candidate* into ``rule_entries``; appends an
        ``AuditEventType.REJECT`` event to the audit log.

        Args:
            candidate: Rejected synthesiser candidate.
            reason: Non-empty justification for rejection.
            evidence: Optional verification evidence associated with the check.

        Returns:
            The recorded :class:`~evolzen.schemas.library.AuditEvent`.

        Raises:
            ValueError: If *reason* is empty/whitespace.
        """
        if not reason.strip():
            raise ValueError("Rejection reason must be non-empty")
        try:
            parsed_id = UUID(candidate.rule_id)
        except ValueError:
            parsed_id = uuid4()
        detail: dict[str, object] = {
            "candidate_rule_id": candidate.rule_id,
            "reason": reason,
            "explains": list(candidate.explains),
        }
        if evidence is not None:
            detail["evidence_id"] = str(evidence.evidence_id)
            detail["false_promotion_rate"] = evidence.false_promotion_rate
        event = make_event(AuditEventType.REJECT, rule_id=parsed_id, detail=detail)
        self._audit.record(event)
        return event

    def revert_supersession(self, old_id: UUID, reason: str) -> RuleEntry:
        """Explicitly reverse a supersession without erasing historical rows.

        Validates *reason* (at least 10 non-whitespace characters), marks the
        replacing entry ``DEPRECATED`` if it is still ``ACTIVE``, restores
        *old_id* to ``ACTIVE`` via an appended row, and writes an
        ``AuditEventType.REVERT`` audit record.

        Args:
            old_id: UUID of the previously superseded rule to restore.
            reason: Human-readable justification (minimum 10 characters).

        Returns:
            The restored :class:`RuleEntry` (status ``ACTIVE``).

        Raises:
            KeyError: If *old_id* does not exist.
            ValueError: If *old_id* is not currently ``SUPERSEDED`` or *reason*
                is invalid.
        """
        validate_supersession_reason(reason)
        old_entry = self._store.get_by_id(old_id)
        if old_entry is None:
            raise KeyError(f"No rule entry found for rule_id={old_id}")
        if old_entry.status is not RuleStatus.SUPERSEDED:
            raise ValueError(
                f"Only SUPERSEDED rules can be reverted; {old_id} is {old_entry.status}"
            )
        superseding_id = old_entry.superseded_by
        if superseding_id is not None:
            new_entry = self._store.get_by_id(superseding_id)
            if new_entry is not None and new_entry.status is RuleStatus.ACTIVE:
                self._store.update_status(
                    superseding_id,
                    RuleStatus.DEPRECATED,
                    superseded_by=None,
                    reason=f"Superseded rule restored: {reason}",
                )
        self._store.update_status(
            old_id,
            RuleStatus.ACTIVE,
            superseded_by=None,
            reason=None,
        )
        self._audit.record(
            make_event(
                AuditEventType.REVERT,
                rule_id=old_id,
                detail={
                    "reverted_from_rule_id": str(superseding_id) if superseding_id else None,
                    "reason": reason,
                },
            )
        )
        restored = self._store.get_by_id(old_id)
        assert restored is not None
        return restored

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, rule_id: UUID | str) -> RuleEntry | None:
        """Return the latest state of *rule_id*, or ``None`` if not found.

        Args:
            rule_id: UUID (or string representation of a UUID) to look up.

        Returns:
            :class:`RuleEntry` or ``None``.
        """
        if isinstance(rule_id, str):
            try:
                parsed_id = UUID(rule_id)
            except ValueError:
                return None
            return self._store.get_by_id(parsed_id)
        return self._store.get_by_id(rule_id)

    def get_active(self) -> list[RuleEntry]:
        """Return all entries whose current status is ACTIVE.

        Returns:
            List of :class:`RuleEntry` objects.
        """
        return self._store.get_active()

    def get_all(self) -> list[RuleEntry]:
        """Return the latest state of every entry in the store (all statuses).

        Returns:
            List of :class:`RuleEntry` objects.
        """
        return self._store.get_all()

    def get_family(self, rule_family_id: UUID) -> list[RuleEntry]:
        """Return all versions sharing *rule_family_id*, ordered by version.

        Args:
            rule_family_id: Family UUID to filter by.

        Returns:
            Ordered list of :class:`RuleEntry` objects.
        """
        return self._store.get_family(rule_family_id)

    def get_supersession_links(
        self, rule_id: UUID | None = None
    ) -> list[SupersessionLink]:
        """Return explicit supersession links from the store.

        Args:
            rule_id: Optional rule UUID to filter links by.

        Returns:
            List of :class:`~evolzen.schemas.library.SupersessionLink` objects.
        """
        return self._store.get_supersession_links(rule_id)

    def __len__(self) -> int:
        """Total number of distinct rule IDs (all statuses)."""
        return self._store.count()

    def active_count(self) -> int:
        """Number of rules whose current status is ACTIVE.

        Returns:
            Integer count.
        """
        return self._store.count_active()

    # ------------------------------------------------------------------
    # Capability package management
    # ------------------------------------------------------------------

    def register_capability(
        self,
        package: CapabilityPackage,
        evidence: VerificationEvidence | None = None,
    ) -> CapabilityPackage:
        """Register a verified capability package into the library.

        Validates verification gates (or updates verification flags using *evidence*),
        appends the package to the store with ``ACTIVE`` status, records an audit event,
        and returns the registered package.

        Args:
            package: The :class:`~evolzen.schemas.world.CapabilityPackage` to register.
            evidence: Optional :class:`~evolzen.schemas.library.VerificationEvidence`
                bundle backing the capability.

        Returns:
            The registered :class:`~evolzen.schemas.world.CapabilityPackage`.

        Raises:
            ValueError: If the package fails verification gates or if evidence validation fails.
        """
        event_type = AuditEventType.SPAWN
        if evidence is not None:
            if evidence.resource_ceiling_hit:
                raise ValueError(
                    "Verification evidence hit resource ceiling; cannot register capability"
                )
            if evidence.false_promotion_rate > 0.0:
                raise ValueError(
                    f"Verification evidence false promotion rate {evidence.false_promotion_rate} > 0.0"
                )
            ev_id = evidence.evidence_id_str
            if package.evidence_id and package.evidence_id != ev_id:
                raise ValueError(
                    f"Mismatched evidence_id between package ({package.evidence_id}) and evidence ({ev_id})"
                )
            package = package.model_copy(
                update={
                    "evidence_id": ev_id,
                    "verified_replay": True,
                    "verified_intervention": True,
                    "verified_containment": True,
                }
            )
            event_type = AuditEventType.PROMOTE
        else:
            if not (
                package.verified_replay
                and package.verified_intervention
                and package.verified_containment
            ):
                raise ValueError(
                    f"Capability package {package.package_id} failed verification gates: "
                    "verified_replay, verified_intervention, and verified_containment must all be True"
                )

        self._store.append_capability(package, status=RuleStatus.ACTIVE)
        if self._audit is not None:
            self._audit.record(
                make_event(
                    event_type,
                    rule_id=_package_id_to_uuid(package.package_id),
                    detail={
                        "package_id": package.package_id,
                        "version": package.version,
                        "action_type": str(package.action_type),
                        "evidence_id": package.evidence_id,
                    },
                )
            )
        return package

    def get_capability(self, package_id: str) -> CapabilityPackage | None:
        """Return the latest state of a capability package, or ``None`` if not found.

        Args:
            package_id: Unique string identifier of the package.

        Returns:
            The :class:`~evolzen.schemas.world.CapabilityPackage` or ``None``.
        """
        return self._store.get_capability_by_id(package_id)

    def get_active_capabilities(self) -> list[CapabilityPackage]:
        """Return all active capability packages in the library.

        Returns:
            List of active :class:`~evolzen.schemas.world.CapabilityPackage` objects.
        """
        return self._store.get_active_capabilities()

    def supersede_capability(
        self,
        old_package_id: str,
        new_package: CapabilityPackage,
        reason: str,
    ) -> CapabilityPackage:
        """Supersede an existing capability package with *new_package*.

        Validates *reason* (at least 10 non-whitespace characters), marks the
        old capability package as ``SUPERSEDED`` in the store, appends the
        new package with ``ACTIVE`` status, records an ``AuditEventType.SUPERSEDE``
        event in the audit log, and returns *new_package*.

        Args:
            old_package_id: Identifier of the package being superseded.
            new_package: Replacement :class:`~evolzen.schemas.world.CapabilityPackage`.
            reason: Human-readable justification (minimum 10 characters).

        Returns:
            The newly registered :class:`~evolzen.schemas.world.CapabilityPackage`.

        Raises:
            KeyError: If *old_package_id* does not exist in the store.
            ValueError: If *reason* is invalid or *new_package* fails verification.
        """
        validate_supersession_reason(reason)
        old = self._store.get_capability_by_id(old_package_id)
        if old is None:
            raise KeyError(f"No capability package found for package_id={old_package_id}")

        if not (
            new_package.verified_replay
            and new_package.verified_intervention
            and new_package.verified_containment
        ):
            raise ValueError(
                f"Replacement capability package {new_package.package_id} failed verification gates"
            )

        self._store.update_capability_status(old_package_id, RuleStatus.SUPERSEDED)
        self._store.append_capability(new_package, status=RuleStatus.ACTIVE)
        if self._audit is not None:
            self._audit.record(
                make_event(
                    AuditEventType.SUPERSEDE,
                    rule_id=_package_id_to_uuid(old_package_id),
                    detail={
                        "old_package_id": old_package_id,
                        "new_package_id": new_package.package_id,
                        "reason": reason,
                    },
                )
            )
        return new_package

    def export_capabilities_to_world(self, world: WorldState) -> WorldState:
        """Return a copy of *world* with active library capabilities merged into `world.capabilities`.

        Args:
            world: Current :class:`~evolzen.schemas.world.WorldState`.

        Returns:
            Updated copy of *world* containing all active library capabilities.
        """
        active_caps = self.get_active_capabilities()
        merged = dict(world.capabilities)
        for pkg in active_caps:
            merged[pkg.package_id] = pkg
        return world.model_copy(update={"capabilities": merged})

    def import_capabilities_from_world(
        self, world: WorldState
    ) -> list[CapabilityPackage]:
        """Import verified capabilities from *world.capabilities* into the library store.

        Only capability packages that satisfy all verification gates
        (``verified_replay``, ``verified_intervention``, ``verified_containment``)
        and are not already present in the store are imported.

        Args:
            world: :class:`~evolzen.schemas.world.WorldState` to import from.

        Returns:
            List of newly imported :class:`~evolzen.schemas.world.CapabilityPackage` instances.
        """
        imported: list[CapabilityPackage] = []
        for pkg in world.capabilities.values():
            if not (
                pkg.verified_replay
                and pkg.verified_intervention
                and pkg.verified_containment
            ):
                continue
            if self._store.get_capability_by_id(pkg.package_id) is not None:
                continue
            self._store.append_capability(pkg, status=RuleStatus.ACTIVE)
            if self._audit is not None:
                self._audit.record(
                    make_event(
                        AuditEventType.SPAWN,
                        rule_id=_package_id_to_uuid(pkg.package_id),
                        detail={
                            "package_id": pkg.package_id,
                            "source": "import_capabilities_from_world",
                        },
                    )
                )
            imported.append(pkg)
        return imported

    def capability_count(self) -> int:
        """Total number of distinct capability package IDs (all statuses)."""
        return self._store.count_capabilities()

    def active_capability_count(self) -> int:
        """Number of capability packages whose current status is ACTIVE."""
        return self._store.count_active_capabilities()

    # ------------------------------------------------------------------
    # Filtered rule querying
    # ------------------------------------------------------------------

    def find_by_mechanic(self, mechanic_key: str) -> list[RuleEntry]:
        """Return all active rules explaining *mechanic_key*.

        Args:
            mechanic_key: Mechanic identifier to filter by.

        Returns:
            List of active :class:`~evolzen.schemas.library.RuleEntry` objects
            whose ``explains`` tuple contains *mechanic_key*.
        """
        return [e for e in self.get_active() if mechanic_key in e.explains]

    def find_by_world_version(self, world_version: str) -> list[RuleEntry]:
        """Return all active rules whose ``validity.world_version == world_version``.

        Args:
            world_version: World version identifier to filter by.

        Returns:
            List of active :class:`~evolzen.schemas.library.RuleEntry` objects
            whose validity context matches *world_version*.
        """
        return [
            e for e in self.get_active() if e.validity.world_version == world_version
        ]
