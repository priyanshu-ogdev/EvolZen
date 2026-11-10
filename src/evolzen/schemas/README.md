# Shared schemas

Current legacy records: `transition.py`, `drive_vector.py`, `manual.py`.
New developmental records: `development.py` (version `eight-drive-v1`). Existing record shapes
and public exports are unchanged. Import new types directly from `evolzen.schemas.development`.

The new records use frozen tuples, reject unknown fields and nonfinite values, validate vector
dimensions and enforce lifecycle/memory constraints during snapshot restoration. They are data,
not executable formulas. Frozen state is not authenticated state; callers must protect outcome,
assessment and snapshot provenance.

See [contracts and migration](../../../docs/subsystems/agents/engineering.md). Proposed world
snapshot and richer social-profile interfaces elsewhere in the docs remain future work. Any
change to an existing schema requires checking all importers across all nine subsystems.
