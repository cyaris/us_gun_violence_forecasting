# Backend Guidance

## Backend Python

- Format Python from `backend` with the repository's Black and isort settings. Avoid non-functional trailing commas that make Black preserve unnecessary multiline layouts; when an existing tuple, list, call, or assertion would fit under the configured line length, remove the non-functional trailing comma so Black can collapse it. Keep commas that are semantically required or improve readability.
- When backend code directly imports a runtime package, declare that package explicitly in `backend/pyproject.toml` rather than relying on transitive dependencies.
