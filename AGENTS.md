# Repository Guidance

## Shared Conventions

- Inherit README and Markdown style, link verification, GitHub Actions, reusable workflow, release policy, dispatch,
  pull-request review and merge authorization, workflow failure, commit, release-management, and code style rules from
  the shared topics in `../shared-automation/agents/`, which `CLAUDE.md` imports:
  - `code-style.md`
  - `documentation.md`
  - `git-and-pull-requests.md`
  - `workflows.md`

## Data Generation

- Regenerate and commit `frontend/src/lib/static/data.json` after changing the source CSV or forecast settings.

## Rollup Delivery

- Project-specific Rollup inputs include the S3 prefix, bundle file list, and metadata refresh files.
