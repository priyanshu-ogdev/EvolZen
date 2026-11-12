# Shared schemas

Current schema modules:
- `transition.py` (`State`, `Action`, `ExogenousInput`, `Emission`, `Transition`)
- `drive_vector.py` (`DriveVector`)
- `manual.py` (`ManualEntryStatus`, `ManualEntry`, `Manual`)
- `development.py` (`BirthGenome`, `Motive`, `LifeStage`, `BrainSnapshot`, `Candidate`, `Decision`, `Outcome`, etc., version `eight-drive-v1`)
- `world.py` (`WorldState`, `WorldSnapshot`, `CapabilityPackage`, `ActionType`, `GrowthEvent`, `WorldInvariant`, `InvariantReport`, `BranchRecord`, `InterventionSpec`, and typed world entity records)
- `library.py` (`RuleEntry`, `RuleStatus`, `ProvenanceClass`, `ValidityContext`, `VerificationEvidence`, `SupersessionLink`, `AuditEvent`, `AuditEventType`, `RegressionResult`)

`schemas/__init__.py` currently re-exports `transition`, `drive_vector`, `manual`, and `library`; top-level re-exports for `world` and `development` remain an open gap (callers import those modules directly). `AgentProfile` and `ProvenanceRecord` remain planned. Existing record shapes and public exports remain backward-compatible.
