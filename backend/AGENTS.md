# Backend Guidance

## Backend Python

- Format Python from `backend` with the repository's Black and isort settings. Remove a trailing comma when it only
  forces an otherwise fitting expression to remain multiline; keep it when syntax requires it or the formatter restores
  it.
- When backend code directly imports a runtime package, declare that package explicitly in `backend/pyproject.toml` rather than relying on transitive dependencies.
