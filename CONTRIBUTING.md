# Contributing

## Branching

- Use short feature branches from `main`.
- Prefer names like `feature/persistent-jobs`, `fix/upload-validation`, or `docs/sprint-plan`.
- Open a pull request before merging to `main`.

## Commits

Use concise, imperative commit messages:

```text
Add request correlation middleware
Fix compare result status handling
Document benchmark fixture layout
```

## Local Checks

Run these before opening a pull request:

```bash
ruff check .
black --check .
mypy app
pytest
```

## Pull Requests

- Keep changes scoped to one story or task.
- Include tests for behavior changes.
- Update docs when API, architecture, operations, or setup changes.
- Do not include document contents, PII, or confidential benchmark files in logs or fixtures.
