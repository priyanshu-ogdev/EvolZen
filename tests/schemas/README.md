# Schema tests

`test_development.py` checks the new closed, frozen developmental records and restoration
boundaries. Legacy schema tests remain in `tests/core/test_schemas.py`; this change does not move
or weaken them. New schema tests mirror `src/evolzen/schemas/` as the repository convention asks.

Schema tests cover closed/frozen developmental records, finite bounded vectors, lifecycle
validation and restoration boundaries. Semantic host receipt consistency belongs to the future
environment/storage integration, not to Pydantic shape validation alone.
