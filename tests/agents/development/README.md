# Developmental-agent tests

Tests mirror `src/evolzen/agents/development`: seeded equations, lifecycle boundaries, decision
feedback, parental teaching, serialization and bounded phenotype archives. They use numerical
fixtures and never execute agent-generated code or load LLMs.

Targeted project command after normal uv setup:
`uv run pytest tests/agents/development tests/schemas/test_development.py -q`.
Record actual results; these tests do not establish learning efficiency, human realism, safety
of a deployed executor or successful multi-generation world integration.
