# Repository Guidance

## Shared Conventions

- Inherit README and Markdown style, GitHub Actions, reusable workflow wrapper, release policy, dispatch, pull-request
  review, workflow failure, commit, and release-management rules from `../shared-automation/AGENTS.md`.
- Inherit shared Python and SQL conventions from `../shared-automation/AGENTS.md`.

## Data Generation

- Regenerate and commit `frontend/src/lib/static/data.json` after changing the source CSV or forecast settings.

## Rollup Delivery

- Project-specific Rollup inputs include the S3 prefix, bundle file list, and metadata refresh files.
