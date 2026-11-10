# .github/

CI and repository automation.

| File | Purpose |
|---|---|
| [`workflows/ci.yml`](workflows/ci.yml) | Lint (`ruff`), type-check (`mypy --strict`), test (`pytest`), path-filtered per subsystem. |
| [`CODEOWNERS`](CODEOWNERS) | Review routing by subsystem path. |
| [`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md) | Checklist enforcing this project's honesty and testing requirements. |
| [`ISSUE_TEMPLATE/`](ISSUE_TEMPLATE/) | Bug reports vs. open research questions — different information, different reviewers. |
| [`dependabot.yml`](dependabot.yml) | Weekly automated dependency-update PRs. |
