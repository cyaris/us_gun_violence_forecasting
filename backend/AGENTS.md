# Backend Guidance

- Keep Python virtual environments outside this repository. Use an external environment such as `~/.virtualenvs/us-gun-violence-forecasting-backend`; do not create or rely on `backend/.venv`.
- When backend code directly imports a runtime package, declare that package explicitly in `backend/pyproject.toml` rather than relying on transitive dependencies.

## Code Formatting

- Do not use non-functional trailing commas in multiline Python syntax. Prefer single-line calls, literals, and expressions when they fit under the repository's effective formatter width.
- Format Python files with Black using a wide line length and `--skip-magic-trailing-comma` so calls and literals are not kept multiline solely because of trailing commas.
